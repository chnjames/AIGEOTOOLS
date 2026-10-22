"""关键词 API"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_keyword_service, get_config_service, require_api_key
from app.api.sse import create_sse_response, llm_stream_to_sse
from app.core.database import get_db
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.keyword import (
    KeywordResponse, KeywordCreate, KeywordGenerateRequest,
    KeywordMineRequest, KeywordExpandRequest, KeywordClusterRequest,
    TopicClusterResponse, TagUpdateRequest, ImportRequest,
)
from app.services.keyword_service import KeywordService, generate_combinations
from app.services.config_service import ConfigService
from app.services.llm_service import LLMConfig
from app.services.llm_factory import get_default_model
from app.services.keyword_analytics import analyze_keywords_quality, get_industry_presets
from app.services.audit_service import log_audit, get_operator_from_request
from app.utils.prompt_guard import detect_injection

router = APIRouter(prefix="/keywords", tags=["关键词蒸馏"])


def _collect_injection_warnings(brand: str, advantages: str) -> list[str]:
    """对 brand 和 advantages 字段运行注入检测，收集所有警告（非阻塞）。"""
    warnings: list[str] = []
    if brand:
        warnings.extend(f"[品牌] {w}" for w in detect_injection(brand))
    if advantages:
        warnings.extend(f"[品牌优势] {w}" for w in detect_injection(advantages))
    return warnings


@router.get("", response_model=ApiResponse[PageResponse[KeywordResponse]])
async def list_keywords(
    brand: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    is_favorite: Optional[bool] = Query(None, description="按收藏状态筛选"),
    tag: Optional[str] = Query(None, description="按标签筛选"),
    search: Optional[str] = Query(None, description="搜索关键词文本"),
    svc: KeywordService = Depends(get_keyword_service),
    _auth: None = Depends(require_api_key),
):
    result = await svc.get_keywords(
        brand=brand, page=page, page_size=page_size,
        is_favorite=is_favorite, tag=tag or "", search=search or "",
    )
    return ApiResponse(data=PageResponse(**result))


@router.post("", response_model=ApiResponse[dict])
async def create_keywords(
    req: KeywordCreate,
    svc: KeywordService = Depends(get_keyword_service),
    _auth: None = Depends(require_api_key),
):
    result = await svc.create_keywords(req.keywords, req.brand)
    saved_objs = result["saved"]
    return ApiResponse(data={
        "saved": [KeywordResponse.model_validate(o) for o in saved_objs],
        "duplicates_skipped": result["duplicates_skipped"],
        "errors": result["errors"],
    })


@router.get("/search", response_model=ApiResponse[list])
async def search_keywords(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    brand: str = Query("", description="按品牌筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量上限"),
    svc: KeywordService = Depends(get_keyword_service),
    _auth: None = Depends(require_api_key),
):
    """关键词搜索（自动补全/选择器用），返回 id/keyword/brand/is_favorite/tags 精简列表。"""
    items = await svc.search_keywords(query=q, brand=brand, limit=limit)
    result = [
        {
            "id": kw.id,
            "keyword": kw.keyword,
            "brand": kw.brand,
            "is_favorite": kw.is_favorite,
            "tags": kw.tags.split(",") if kw.tags else [],
        }
        for kw in items
    ]
    return ApiResponse(data=result)


@router.post("/import", response_model=ApiResponse[dict])
async def import_keywords(
    req: ImportRequest,
    svc: KeywordService = Depends(get_keyword_service),
    _auth: None = Depends(require_api_key),
):
    """将指定 ID 的关键词导入到目标品牌，自动跳过已存在的关键词。"""
    result = await svc.import_keywords(req.keyword_ids, req.target_brand)
    return ApiResponse(data={
        "imported": result["imported"],
        "skipped": result["skipped"],
        "errors": result["errors"],
    })


@router.post("/combinations", response_model=ApiResponse[list[str]])
async def generate_keyword_combinations(
    core_keyword: str = Query(...),
    max_results: int = Query(50, ge=1, le=500),
    _auth: None = Depends(require_api_key),
):
    """词库组合生成关键词（纯计算，不调用LLM）"""
    kws = generate_combinations(core_keyword=core_keyword, max_results=max_results)
    return ApiResponse(data=kws)


async def _resolve_cfg(req, config_svc: ConfigService) -> tuple[LLMConfig, str, str]:
    """从请求或全局配置解析 LLM 配置"""
    cfg = await config_svc.get_config()
    provider = req.provider or cfg.get("gen_provider", "DeepSeek")
    api_key = req.api_key or cfg.get("gen_api_key", "")
    model = req.model or get_default_model(provider)
    temperature = getattr(req, "temperature", 0.7) or cfg.get("temperature", 0.7)
    brand = getattr(req, "brand", "") or cfg.get("brand", "")
    advantages = getattr(req, "advantages", "") or cfg.get("advantages", "")
    return LLMConfig(provider=provider, api_key=api_key, model=model, temperature=temperature), brand, advantages


@router.post("/generate")
async def generate_keywords_llm(
    req: KeywordGenerateRequest,
    svc: KeywordService = Depends(get_keyword_service),
    config_svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    """LLM 生成关键词（SSE 流式）"""
    cfg, brand, advantages = await _resolve_cfg(req, config_svc)
    if not brand:
        brand = req.brand
    if not advantages:
        advantages = req.advantages

    # Prompt 注入检测（非阻塞，仅警告）
    warnings = _collect_injection_warnings(brand, advantages)

    async def _gen():
        yield {"event": "start", "data": {"message": "开始生成关键词...", "warnings": warnings}}
        async for event in llm_stream_to_sse(
            svc.generate_llm_keywords(
                core_keyword=req.core_keyword, brand=brand, advantages=advantages,
                cfg=cfg, max_count=req.max_results, polish=req.polish,
            ),
            meta={"brand": brand}
        ):
            yield event

    return create_sse_response(_gen())


@router.post("/mine")
async def mine_keywords(
    req: KeywordMineRequest,
    svc: KeywordService = Depends(get_keyword_service),
    config_svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    """竞品关键词挖掘（SSE 流式）"""
    cfg, brand, advantages = await _resolve_cfg(req, config_svc)
    brand = brand or req.brand

    # Prompt 注入检测（非阻塞，仅警告）
    warnings = _collect_injection_warnings(brand, advantages)

    async def _stream():
        yield {"event": "start", "data": {"warnings": warnings}}
        async for event in llm_stream_to_sse(
            svc.mine_keywords(req.keyword, brand, cfg)
        ):
            yield event

    return create_sse_response(_stream())


@router.post("/expand")
async def expand_keywords(
    req: KeywordExpandRequest,
    svc: KeywordService = Depends(get_keyword_service),
    config_svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    """语义扩展（SSE 流式）"""
    cfg, brand, advantages = await _resolve_cfg(req, config_svc)
    brand = brand or req.brand

    # Prompt 注入检测（非阻塞，仅警告）
    warnings = _collect_injection_warnings(brand, advantages)

    async def _stream():
        yield {"event": "start", "data": {"warnings": warnings}}
        async for event in llm_stream_to_sse(
            svc.expand_keywords(req.keywords, brand, cfg)
        ):
            yield event

    return create_sse_response(_stream())


@router.post("/cluster", response_model=ApiResponse[TopicClusterResponse])
async def cluster_keywords(
    req: KeywordClusterRequest,
    svc: KeywordService = Depends(get_keyword_service),
    config_svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    """话题聚类"""
    cfg, brand, _ = await _resolve_cfg(req, config_svc)
    result = await svc.cluster_keywords(req.keywords, brand or req.brand, cfg)
    return ApiResponse(data=TopicClusterResponse(**result))


@router.get("/meta/industry-presets", response_model=ApiResponse[list])
async def industry_presets(_auth: None = Depends(require_api_key)):
    """获取行业预设词库模板"""
    return ApiResponse(data=get_industry_presets())


@router.post("/analyze-quality", response_model=ApiResponse[dict])
async def keyword_quality(
    keywords: list[str],
    _auth: None = Depends(require_api_key),
):
    """分析关键词质量（意图分布、品牌词比例、长尾词比例等，纯规则，不调LLM）"""
    return ApiResponse(data=analyze_keywords_quality(keywords))


# ---- 单条操作（/{kid} 路由统一放在最后，避免遮挡具体路径） ----

@router.post("/{kid}/favorite", response_model=ApiResponse[dict])
async def toggle_keyword_favorite(
    kid: int,
    svc: KeywordService = Depends(get_keyword_service),
    _auth: None = Depends(require_api_key),
):
    """切换关键词收藏状态，返回最新的 is_favorite 值。"""
    obj = await svc.toggle_favorite(kid)
    if obj is None:
        raise NotFoundError("关键词不存在")
    return ApiResponse(data={"id": obj.id, "is_favorite": obj.is_favorite})


@router.put("/{kid}/tags", response_model=ApiResponse[KeywordResponse])
async def set_keyword_tags(
    kid: int,
    req: TagUpdateRequest,
    svc: KeywordService = Depends(get_keyword_service),
    _auth: None = Depends(require_api_key),
):
    """设置关键词的标签列表（覆盖原有标签）。"""
    obj = await svc.set_tags(kid, req.tags)
    if obj is None:
        raise NotFoundError("关键词不存在")
    return ApiResponse(data=KeywordResponse.model_validate(obj))


@router.delete("/{kw_id}", response_model=ApiResponse[dict])
async def delete_keyword(
    kw_id: int,
    svc: KeywordService = Depends(get_keyword_service),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _auth: None = Depends(require_api_key),
):
    ok = await svc.delete_keyword(kw_id)
    if ok:
        await log_audit(
            db=db, action="keyword_delete", resource_type="keyword", resource_id=str(kw_id),
            operator=get_operator_from_request(request),
        )
    return ApiResponse(data={"ok": ok})


@router.delete("", response_model=ApiResponse[dict])
async def delete_all_keywords(
    brand: str = Query(..., description="品牌名称（必填，防止误删所有关键词）"),
    svc: KeywordService = Depends(get_keyword_service),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _auth: None = Depends(require_api_key),
):
    if not brand:
        raise ValidationError("必须指定 brand 参数，不允许删除所有关键词")
    count = await svc.delete_all(brand)
    await log_audit(
        db=db, action="keyword_delete_all", resource_type="keyword",
        operator=get_operator_from_request(request),
        details={"brand": brand, "deleted_count": count},
    )
    return ApiResponse(data={"deleted": count})
