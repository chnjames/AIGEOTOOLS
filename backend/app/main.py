"""FastAPI 应用入口"""
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response, HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.exceptions import GEOAppException, PromptInjectionWarning
from app.core.logging import setup_logging, get_logger
from app.core.database import engine, AsyncSessionFactory, check_db_connection
from app.core.scheduler import start_scheduler, shutdown_scheduler
from app.api.v1.router import api_router

# 确保所有模型被导入（Alembic/表创建需要）
import app.models  # noqa: F401

settings = get_settings()
logger = get_logger(__name__)

setup_logging()

# 启动时警告：API Key 未设置
if not settings.API_KEY:
    logger.warning("SECURITY: API_KEY is not set — API authentication is disabled. Non-localhost requests will be blocked.")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理"""
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    # 确保上传目录存在
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.KNOWLEDGE_DIR, exist_ok=True)
    # 初始化数据库表 + 种子数据
    try:
        async with AsyncSessionFactory() as db:
            from app.services.template_service import TemplateService
            tpl_svc = TemplateService(db)
            await tpl_svc.seed_defaults()
            from app.services.article_service import ArticleService
            platform_config = await tpl_svc.get_platform_config()
            ArticleService.set_platform_config(platform_config)
            await db.commit()
        logger.info("Platform templates seeded")
    except Exception as e:
        logger.warning("Failed to seed templates: %s", e)
    # 启动定时任务调度器
    try:
        start_scheduler()
    except Exception as e:
        logger.warning("Failed to start scheduler (apscheduler not installed?): %s", e)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)
    shutdown_scheduler()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="GEO 智能内容优化平台 API",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Request-ID", "Authorization"],
)


# 安全中间件：API_KEY 未设置时，仅允许本机访问
@app.middleware("http")
async def enforce_localhost_when_no_apikey(request: Request, call_next) -> Response:
    if not settings.API_KEY:
        client_host = request.client.host if request.client else ""
        # 允许本机回环地址和健康检查
        allowed_hosts = {"127.0.0.1", "::1", "localhost"}
        if client_host not in allowed_hosts and request.url.path not in ("/health", "/"):
            logger.warning("Blocked non-localhost request from %s to %s (API_KEY not set)", client_host, request.url.path)
            return JSONResponse(
                status_code=403,
                content={"code": "FORBIDDEN", "message": "API_KEY 未配置，仅允许本机访问。请设置 API_KEY 后重试。"},
            )
    return await call_next(request)


# 请求 ID + 慢请求日志中间件
SLOW_REQUEST_THRESHOLD = 5.0  # 秒，超过此时间的请求记录警告日志

@app.middleware("http")
async def add_request_id(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request.state.request_id = request_id
    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    if duration > SLOW_REQUEST_THRESHOLD and request.url.path not in ("/health", "/"):
        logger.warning(
            "[%s] SLOW request: %s %s took %.3fs (status=%d)",
            request_id, request.method, request.url.path, duration, response.status_code,
        )
    return response


# 请求参数验证错误处理器（统一错误格式）
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    req_id = getattr(request.state, "request_id", "-")
    errors = exc.errors()
    first_err = errors[0] if errors else {}
    loc = first_err.get("loc", ())
    field = " -> ".join(str(p) for p in loc if p != "body") if loc else "请求参数"
    msg = first_err.get("msg", "参数验证失败")
    detail = f"{field}: {msg}" if field != "请求参数" else msg
    logger.warning("[%s] Validation error on %s %s: %s", req_id, request.method, request.url.path, detail)
    return JSONResponse(
        status_code=422,
        content={"code": "VALIDATION_ERROR", "message": detail, "request_id": req_id},
    )


# 全局异常处理器
@app.exception_handler(GEOAppException)
async def geo_app_exception_handler(request: Request, exc: GEOAppException) -> JSONResponse:
    # PromptInjectionWarning 返回 200 但附带警告
    if isinstance(exc, PromptInjectionWarning):
        status = 200
        logger.warning("[%s] Prompt injection detected: %s - %s", getattr(request.state, "request_id", "-"), exc.code, exc.message)
    else:
        status = exc.status_code
        log_level = logger.error if status >= 500 else logger.warning
        log_level("[%s] App exception: %s - %s", getattr(request.state, "request_id", "-"), exc.code, exc.message)
    return JSONResponse(
        status_code=status,
        content={"code": exc.code, "message": exc.message},
    )


# HTTP 异常处理器（FastAPI/Starlette 原生的 HTTPException 保持其原有状态码）
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    req_id = getattr(request.state, "request_id", "-")
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": f"HTTP_{exc.status_code}", "message": exc.detail, "request_id": req_id},
    )


# 全局异常处理器（仅处理未被其他 handler 捕获的非 HTTP 异常）
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # 跳过 HTTP 异常（由上面的 handler 处理）
    if isinstance(exc, StarletteHTTPException):
        raise exc
    req_id = getattr(request.state, "request_id", "-")
    logger.error("[%s] Unhandled exception on %s %s: %s: %s", req_id, request.method, request.url.path, type(exc).__name__, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "服务器内部错误，请稍后重试。如问题持续存在，请联系管理员并提供 Request ID。", "request_id": req_id},
    )


# 路由注册
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health_check() -> dict[str, object]:
    """健康检查：返回应用版本、数据库、磁盘和知识库状态"""
    import shutil
    checks: dict[str, object] = {}
    db_ok = await check_db_connection()
    checks["database"] = "connected" if db_ok else "disconnected"

    # 磁盘空间检查
    try:
        disk = shutil.disk_usage("/")
        disk_pct = disk.used / disk.total * 100
        checks["disk"] = {
            "free_gb": round(disk.free / (1024**3), 1),
            "total_gb": round(disk.total / (1024**3), 1),
            "used_pct": round(disk_pct, 1),
        }
        disk_ok = disk_pct < 90
    except Exception:
        disk_ok = True  # 无法检测时不阻断健康检查
        checks["disk"] = "unknown"

    # ChromaDB 知识库检查
    chroma_ok = True
    try:
        import os
        kb_path = settings.KNOWLEDGE_DIR
        if os.path.isdir(kb_path) and os.listdir(kb_path):
            checks["knowledge_base"] = "populated"
        else:
            checks["knowledge_base"] = "empty"
    except Exception:
        checks["knowledge_base"] = "unknown"

    all_ok = db_ok and disk_ok and chroma_ok
    return {
        "status": "ok" if all_ok else "degraded",
        "version": settings.APP_VERSION,
        **checks,
    }


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
