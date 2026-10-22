"""内容优化 API"""
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_optimization_service, get_config_service, get_knowledge_service, require_api_key
from app.api.sse import create_sse_response, llm_stream_to_sse
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.optimization import (
    OptimizationResponse, OptimizeRequest, SchemaGenerateRequest, SchemaResponse,
    TechConfigRequest, TechConfigResponse, UniquenessRequest, UniquenessResponse,
    OriginalContentResponse,
)
from app.services.optimization_service import OptimizationService, generate_tech_config, check_uniqueness
from app.services.config_service import ConfigService
from app.services.knowledge_service import KnowledgeService
from app.services.llm_service import LLMConfig
from app.services.llm_factory import get_default_model
from app.utils.prompt_guard import detect_injection

logger = get_logger(__name__)
router = APIRouter(prefix="/optimizations", tags=["文章优化"])

# 优化类 LLM 调用超时（秒），优化涉及全文改写，需要更长时间
OPTIMIZATION_TIMEOUT = 90


def _collect_injection_warnings(
    content: str = "", brand: str = "", advantages: str = "", keyword: str = "",
) -> list[str]:
    """对进入 LLM 提示词的用户文本字段运行 Prompt 注入检测，收集所有警告（非阻塞）。"""
    warnings: list[str] = []
    if content:
        warnings.extend(f"[内容] {w}" for w in detect_injection(content))
    if brand:
        warnings.extend(f"[品牌] {w}" for w in detect_injection(brand))
    if advantages:
        warnings.extend(f"[品牌优势] {w}" for w in detect_injection(advantages))
    if keyword:
        warnings.extend(f"[关键词] {w}" for w in detect_injection(keyword))
    if warnings:
        logger.warning("Optimization prompt-injection warnings: %s", warnings)
    return warnings


async def _resolve_cfg(req: Any, config_svc: ConfigService, timeout: int = OPTIMIZATION_TIMEOUT) -> tuple[LLMConfig, str, str]:
    cfg = await config_svc.get_config()
    provider = getattr(req, "provider", None) or cfg.get("gen_provider", "DeepSeek")
    api_key = getattr(req, "api_key", None) or cfg.get("gen_api_key", "")
    model = getattr(req, "model", None) or get_default_model(provider)
    temp = getattr(req, "temperature", 0.7) or cfg.get("temperature", 0.7)
    brand = getattr(req, "brand", "") or cfg.get("brand", "")
    advantages = getattr(req, "advantages", "") or cfg.get("advantages", "")
    return LLMConfig(provider=provider, api_key=api_key, model=model, temperature=temp, timeout=timeout), brand, advantages


@router.get("", response_model=ApiResponse[PageResponse[OptimizationResponse]])
async def list_optimizations(
    brand: str = "", page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    svc: OptimizationService = Depends(get_optimization_service),
    _auth: None = Depends(require_api_key),
):
    result = await svc.get_optimizations(brand=brand, page=page, page_size=page_size)
    return ApiResponse(data=PageResponse(**result))


@router.post("/eeat")
async def enhance_eeat(
    req: OptimizeRequest,
    svc: OptimizationService = Depends(get_optimization_service),
    config_svc: ConfigService = Depends(get_config_service),
    knowledge_svc: KnowledgeService = Depends(get_knowledge_service),
    _auth: None = Depends(require_api_key),
):
    """E-E-A-T 增强（SSE 流式）"""
    cfg, brand, advantages = await _resolve_cfg(req, config_svc)
    gcfg = await config_svc.get_config()
    use_kb = req.use_knowledge or gcfg.get("use_knowledge_base", False)
    knowledge_context = req.knowledge_context
    if use_kb and not knowledge_context:
        knowledge_context = await knowledge_svc.get_context_for_query("", brand or req.brand)
    # Prompt 注入检测（非阻塞，仅警告）
    warnings = _collect_injection_warnings(
        content=req.content, brand=brand or req.brand, advantages=advantages or req.advantages,
    )

    async def _stream():
        if warnings:
            yield {"event": "injection_warnings", "data": {"warnings": warnings}}
        async for event in llm_stream_to_sse(
            svc.enhance_eeat(
                content=req.content, brand=brand or req.brand,
                advantages=advantages or req.advantages,
                platform=req.platform, cfg=cfg,
                knowledge_context=knowledge_context,
                article_id=req.article_id,
            ),
            meta={"type": "eeat"}
        ):
            yield event

    return create_sse_response(_stream())


@router.post("/fact-density")
async def enhance_fact_density(
    req: OptimizeRequest,
    svc: OptimizationService = Depends(get_optimization_service),
    config_svc: ConfigService = Depends(get_config_service),
    knowledge_svc: KnowledgeService = Depends(get_knowledge_service),
    _auth: None = Depends(require_api_key),
):
    """事实密度增强（SSE 流式）"""
    cfg, brand, _ = await _resolve_cfg(req, config_svc)
    gcfg = await config_svc.get_config()
    use_kb = req.use_knowledge or gcfg.get("use_knowledge_base", False)
    knowledge_context = req.knowledge_context
    if use_kb and not knowledge_context:
        knowledge_context = await knowledge_svc.get_context_for_query("", brand or req.brand)
    # Prompt 注入检测（非阻塞，仅警告）
    warnings = _collect_injection_warnings(
        content=req.content, brand=brand or req.brand,
    )

    async def _stream():
        if warnings:
            yield {"event": "injection_warnings", "data": {"warnings": warnings}}
        async for event in llm_stream_to_sse(
            svc.enhance_fact_density(
                content=req.content, brand=brand or req.brand,
                platform=req.platform, cfg=cfg,
                knowledge_context=knowledge_context,
                article_id=req.article_id,
            ),
            meta={"type": "fact_density"}
        ):
            yield event

    return create_sse_response(_stream())


@router.post("/semantic-richness")
async def enhance_semantic_richness(
    req: OptimizeRequest,
    svc: OptimizationService = Depends(get_optimization_service),
    config_svc: ConfigService = Depends(get_config_service),
    knowledge_svc: KnowledgeService = Depends(get_knowledge_service),
    _auth: None = Depends(require_api_key),
):
    """语义丰富度增强（SSE 流式）- 同义词/上位词/实体关系优化"""
    cfg, brand, _ = await _resolve_cfg(req, config_svc)
    gcfg = await config_svc.get_config()
    use_kb = req.use_knowledge or gcfg.get("use_knowledge_base", False)
    knowledge_context = req.knowledge_context
    if use_kb and not knowledge_context:
        knowledge_context = await knowledge_svc.get_context_for_query(req.keyword, brand or req.brand)
    keyword = req.keyword or gcfg.get("current_keyword", "")
    # Prompt 注入检测（非阻塞，仅警告）
    warnings = _collect_injection_warnings(
        content=req.content, brand=brand or req.brand, keyword=keyword,
    )

    async def _stream():
        if warnings:
            yield {"event": "injection_warnings", "data": {"warnings": warnings}}
        async for event in llm_stream_to_sse(
            svc.enhance_semantic_richness(
                content=req.content, brand=brand or req.brand,
                keyword=keyword, platform=req.platform, cfg=cfg,
                knowledge_context=knowledge_context,
                article_id=req.article_id,
            ),
            meta={"type": "semantic_richness"}
        ):
            yield event

    return create_sse_response(_stream())


@router.post("/schema", response_model=ApiResponse[SchemaResponse])
async def generate_schema(
    req: SchemaGenerateRequest,
    svc: OptimizationService = Depends(get_optimization_service),
    config_svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    """生成 Schema.org JSON-LD"""
    cfg = (await _resolve_cfg(req, config_svc))[0]
    gcfg = await config_svc.get_config()
    brand = req.brand or gcfg.get("brand", "")
    # Prompt 注入检测（非阻塞，仅警告记录日志）
    _collect_injection_warnings(content=req.content, brand=brand)
    result = await svc.generate_schema(req.content, req.schema_type, brand, cfg)
    return ApiResponse(data=SchemaResponse(**result))


@router.post("/tech-config", response_model=ApiResponse[TechConfigResponse])
async def generate_tech_config_endpoint(
    req: TechConfigRequest,
    _auth: None = Depends(require_api_key),
):
    """生成技术配置（robots.txt等）"""
    result = generate_tech_config(req.brand, req.website_url, req.keywords, req.platforms)
    return ApiResponse(data=TechConfigResponse(**result))


@router.post("/uniqueness", response_model=ApiResponse[UniquenessResponse])
async def check_uniqueness_endpoint(
    req: UniquenessRequest,
    _auth: None = Depends(require_api_key),
):
    """内容独特性检测"""
    result = check_uniqueness(req.content, req.reference_contents)
    return ApiResponse(data=UniquenessResponse(**result))


@router.get("/techniques", response_model=ApiResponse[list])
async def get_techniques(
    svc: OptimizationService = Depends(get_optimization_service),
    _auth: None = Depends(require_api_key),
):
    return ApiResponse(data=svc.get_techniques())


@router.get("/articles/{article_id}/original-content", response_model=ApiResponse[OriginalContentResponse])
async def get_original_content(
    article_id: int,
    svc: OptimizationService = Depends(get_optimization_service),
    _auth: None = Depends(require_api_key),
):
    """获取文章原文（版本1的内容），用于"恢复原文"按钮。

    - 若存在 version_number=1 的版本快照，返回其内容
    - 若 v1 快照不存在（旧数据），回退到当前文章内容
    - 若文章不存在，返回 404
    """
    content = await svc.get_original_content(article_id)
    if content is None:
        raise NotFoundError("文章不存在")
    return ApiResponse(data=OriginalContentResponse(
        article_id=article_id,
        original_content=content,
    ))


@router.post("/{opt_id}/apply", response_model=ApiResponse[dict])
async def apply_optimization(
    opt_id: int,
    svc: OptimizationService = Depends(get_optimization_service),
    _auth: None = Depends(require_api_key),
):
    """将优化结果应用到文章（更新文章内容为优化后的版本）"""
    result = await svc.apply_optimization(opt_id)
    return ApiResponse(data=result)
