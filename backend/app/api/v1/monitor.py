"""持续监测 API"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from app.api.deps import get_monitor_service, get_config_service, require_api_key
from app.api.sse import create_sse_response
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.scheduler import reschedule_task, remove_scheduled_task
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.monitor import (
    MonitorTaskCreate,
    MonitorTaskUpdate,
    MonitorTaskResponse,
    MonitorResultResponse,
    AlertResponse,
    TrendPoint,
)
from app.services.monitor_service import MonitorService, _parse_queries
from app.services.config_service import ConfigService
from app.utils.prompt_guard import detect_injection

logger = get_logger(__name__)
router = APIRouter(prefix="/monitor", tags=["持续监测"])


def _collect_injection_warnings(queries_raw: str, brand: str = "", competitors: str = "") -> list[str]:
    """对进入 LLM 提示词的监测任务查询词/品牌/竞品运行 Prompt 注入检测（非阻塞）。

    queries_raw 可能是 JSON 数组或换行/逗号分隔文本，先解析为列表再逐条检测。
    """
    warnings: list[str] = []
    for q in _parse_queries(queries_raw or ""):
        warnings.extend(f"[查询词] {w}" for w in detect_injection(q))
    if brand:
        warnings.extend(f"[品牌] {w}" for w in detect_injection(brand))
    if competitors:
        for c in [s.strip() for s in competitors.split(",") if s.strip()]:
            warnings.extend(f"[竞品] {w}" for w in detect_injection(c))
    if warnings:
        logger.warning("Monitor prompt-injection warnings: %s", warnings)
    return warnings


async def _resolve_provider_configs(config_svc: ConfigService) -> dict[str, str]:
    """从全局配置解析可用的平台 API Key（复用 verification 模块的模式）"""
    cfg = await config_svc.get_config()
    result: dict[str, str] = {}
    # Use verify_providers and verify_keys from config
    all_providers = cfg.get("verify_providers", [])
    saved_keys = cfg.get("verify_keys", {})
    gen_provider = cfg.get("gen_provider", "")
    gen_key = cfg.get("gen_api_key", "")

    for p in all_providers:
        key = ""
        if p in saved_keys:
            key = saved_keys[p]
        elif p == gen_provider and gen_key:
            key = gen_key
        if key:
            result[p] = key

    # If no verify_providers configured but gen_provider is set, fall back to it
    if not result and gen_provider and gen_key:
        result[gen_provider] = gen_key

    return result


# ---- Monitor Task CRUD --------------------------------------------------------

@router.get("/tasks", response_model=ApiResponse[PageResponse[MonitorTaskResponse]])
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: MonitorService = Depends(get_monitor_service),
    _auth: None = Depends(require_api_key),
):
    """分页列出监测任务"""
    result = await svc.list_tasks(page=page, page_size=page_size)
    return ApiResponse(data=PageResponse(**result))


@router.post("/tasks", response_model=ApiResponse[MonitorTaskResponse])
async def create_task(
    req: MonitorTaskCreate,
    background_tasks: BackgroundTasks,
    svc: MonitorService = Depends(get_monitor_service),
    _auth: None = Depends(require_api_key),
):
    """创建监测任务"""
    # Prompt 注入检测（非阻塞，仅警告）
    _collect_injection_warnings(queries_raw=req.queries, brand=req.brand, competitors=req.competitors)
    task = await svc.create_task(req.model_dump(exclude_unset=True))
    # 使用 FastAPI BackgroundTasks 替代裸 asyncio.create_task，避免请求结束后任务被取消
    background_tasks.add_task(reschedule_task, task.id)
    return ApiResponse(data=MonitorTaskResponse.model_validate(task))


@router.put("/tasks/{task_id}", response_model=ApiResponse[MonitorTaskResponse])
async def update_task(
    task_id: int,
    req: MonitorTaskUpdate,
    background_tasks: BackgroundTasks,
    svc: MonitorService = Depends(get_monitor_service),
    _auth: None = Depends(require_api_key),
):
    """更新监测任务"""
    # Prompt 注入检测（非阻塞，仅警告）—— 仅对实际传入的字段检测
    _collect_injection_warnings(
        queries_raw=req.queries or "",
        brand=req.brand or "",
        competitors=req.competitors or "",
    )
    task = await svc.update_task(task_id, req.model_dump(exclude_unset=True))
    if task is None:
        raise NotFoundError("监测任务不存在")
    background_tasks.add_task(reschedule_task, task_id)
    return ApiResponse(data=MonitorTaskResponse.model_validate(task))


@router.delete("/tasks/{task_id}", response_model=ApiResponse[dict])
async def delete_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    svc: MonitorService = Depends(get_monitor_service),
    _auth: None = Depends(require_api_key),
):
    """删除监测任务"""
    ok = await svc.delete_task(task_id)
    if ok:
        background_tasks.add_task(remove_scheduled_task, task_id)
    return ApiResponse(data={"ok": ok})


@router.post("/tasks/{task_id}/toggle", response_model=ApiResponse[MonitorTaskResponse])
async def toggle_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    svc: MonitorService = Depends(get_monitor_service),
    _auth: None = Depends(require_api_key),
):
    """切换任务启用/禁用状态"""
    task = await svc.toggle_task(task_id)
    if task is None:
        raise NotFoundError("监测任务不存在")
    background_tasks.add_task(reschedule_task, task_id)
    return ApiResponse(data=MonitorTaskResponse.model_validate(task))


# ---- Manual trigger (SSE streaming) -------------------------------------------

@router.post("/tasks/{task_id}/run")
async def run_task(
    task_id: int,
    svc: MonitorService = Depends(get_monitor_service),
    config_svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    """手动触发监测任务执行（SSE 流式返回进度）"""
    prov_cfgs = await _resolve_provider_configs(config_svc)

    gcfg = await config_svc.get_config()
    temperature = gcfg.get("temperature", 0.7)

    async def _stream():
        async for event in svc.run_task_stream(
            task_id=task_id,
            provider_configs=prov_cfgs,
            temperature=temperature,
        ):
            yield event

    return create_sse_response(_stream())


# ---- Results ------------------------------------------------------------------

@router.get("/tasks/{task_id}/results", response_model=ApiResponse[PageResponse[MonitorResultResponse]])
async def get_task_results(
    task_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_date: Optional[date] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期 YYYY-MM-DD"),
    svc: MonitorService = Depends(get_monitor_service),
    _auth: None = Depends(require_api_key),
):
    """分页获取监测任务结果，支持日期范围过滤"""
    result = await svc.get_results(
        task_id=task_id,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
    )
    return ApiResponse(data=PageResponse(**result))


# ---- Trends -------------------------------------------------------------------

@router.get("/trends", response_model=ApiResponse[list[TrendPoint]])
async def get_trends(
    task_id: Optional[int] = Query(None, description="任务ID（不传则查询全部）"),
    platform: Optional[str] = Query(None, description="平台名称过滤"),
    days: int = Query(30, ge=1, le=365, description="查询最近N天"),
    svc: MonitorService = Depends(get_monitor_service),
    _auth: None = Depends(require_api_key),
):
    """查询品牌提及率趋势数据（按日期+平台聚合）"""
    trends = await svc.get_trends(task_id=task_id, platform=platform, days=days)
    return ApiResponse(data=[TrendPoint(**t) for t in trends])


# ---- Alerts -------------------------------------------------------------------

@router.get("/alerts", response_model=ApiResponse[PageResponse[AlertResponse]])
async def list_alerts(
    unread_only: bool = Query(False, description="仅显示未读告警"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: MonitorService = Depends(get_monitor_service),
    _auth: None = Depends(require_api_key),
):
    """分页列出告警记录"""
    result = await svc.list_alerts(unread_only=unread_only, page=page, page_size=page_size)
    return ApiResponse(data=PageResponse(**result))


@router.put("/alerts/{alert_id}/read", response_model=ApiResponse[AlertResponse])
async def mark_alert_read(
    alert_id: int,
    svc: MonitorService = Depends(get_monitor_service),
    _auth: None = Depends(require_api_key),
):
    """标记告警为已读"""
    alert = await svc.mark_alert_read(alert_id)
    return ApiResponse(data=AlertResponse.model_validate(alert))
