"""文章/内容 API"""
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Path, Request
from fastapi.responses import Response

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_article_service, get_config_service, get_knowledge_service, get_db, require_api_key
from app.api.sse import create_sse_response, llm_stream_to_sse
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.article import (
    ArticleResponse, ArticleCreate, ArticleUpdate,
    ArticleGenerateRequest, BatchGenerateRequest, MultimodalRequest,
    ArticleVersionResponse, ArticleSearchItem, OriginalContentResponse,
)
from app.services.article_service import ArticleService
from app.services.config_service import ConfigService
from app.services.knowledge_service import KnowledgeService
from app.services.audit_service import log_audit, get_operator_from_request
from app.services.llm_service import LLMConfig
from app.services.llm_factory import get_default_model
from app.models.article_version import ArticleVersion
from app.utils.diff_utils import compute_diff
from app.utils.prompt_guard import detect_injection

router = APIRouter(prefix="/articles", tags=["自动创作"])


async def _resolve_cfg(req: Any, config_svc: ConfigService) -> LLMConfig:
    cfg = await config_svc.get_config()
    provider = getattr(req, "provider", None) or cfg.get("gen_provider", "DeepSeek")
    api_key = getattr(req, "api_key", None) or cfg.get("gen_api_key", "")
    model = getattr(req, "model", None) or get_default_model(provider)
    temp = getattr(req, "temperature", 0.7) or cfg.get("temperature", 0.7)
    return LLMConfig(provider=provider, api_key=api_key, model=model, temperature=temp)


def _run_injection_check(brand: str, advantages: str) -> list[str]:
    """对品牌名称和品牌优势描述执行 prompt 注入检测，返回警告列表（非阻塞）"""
    warnings: list[str] = []
    if brand:
        warnings.extend(f"[品牌] {w}" for w in detect_injection(brand))
    if advantages:
        warnings.extend(f"[品牌优势] {w}" for w in detect_injection(advantages))
    return warnings


# ---- 文章搜索 ----

@router.get("/search", response_model=ApiResponse[list[ArticleSearchItem]])
async def search_articles(
    q: str = Query(..., min_length=1, description="搜索关键词，匹配 keyword 或 filename"),
    brand: str = Query("", description="按品牌筛选（可选）"),
    limit: int = Query(20, ge=1, le=100, description="返回数量上限"),
    svc: ArticleService = Depends(get_article_service),
    _auth: None = Depends(require_api_key),
):
    """文章搜索接口（用于 selector/autocomplete 下拉联想）"""
    articles = await svc.search_articles(query=q, brand=brand, limit=limit)
    return ApiResponse(data=[ArticleSearchItem.model_validate(a) for a in articles])


# ---- 文章 CRUD ----

@router.get("", response_model=ApiResponse[PageResponse[ArticleResponse]])
async def list_articles(
    brand: str = "", platform: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    svc: ArticleService = Depends(get_article_service),
    _auth: None = Depends(require_api_key),
):
    result = await svc.get_articles(brand=brand, platform=platform, page=page, page_size=page_size)
    return ApiResponse(data=PageResponse(**result))


@router.post("", response_model=ApiResponse[ArticleResponse])
async def create_article(
    req: ArticleCreate,
    svc: ArticleService = Depends(get_article_service),
    _auth: None = Depends(require_api_key),
):
    art = await svc.save_article(
        keyword=req.keyword, platform=req.platform, content=req.content,
        filename=req.filename, brand=req.brand, source="manual",
    )
    return ApiResponse(data=ArticleResponse.model_validate(art))


# ---- 平台元信息（必须在 /{article_id} 之前注册，否则被路径参数匹配） ----

@router.get("/meta/platforms", response_model=ApiResponse[list])
async def supported_platforms(
    svc: ArticleService = Depends(get_article_service),
    _auth: None = Depends(require_api_key),
):
    return ApiResponse(data=svc.get_supported_platforms())


@router.get("/meta/platform-groups", response_model=ApiResponse[list])
async def platform_groups(
    svc: ArticleService = Depends(get_article_service),
    _auth: None = Depends(require_api_key),
):
    return ApiResponse(data=svc.get_platform_groups())


# ---- 下载（批量下载必须在 /{article_id} 之前） ----

@router.get("/batch-download")
async def batch_download(
    ids: str = Query(..., description="逗号分隔的文章ID"),
    svc: ArticleService = Depends(get_article_service),
    _auth: None = Depends(require_api_key),
):
    article_ids = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    if not article_ids:
        raise ValidationError("请提供有效的文章ID列表")
    if len(article_ids) > 100:
        raise ValidationError("批量下载最多支持100篇文章")
    zip_bytes = await svc.download_batch_zip(article_ids)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=articles_{len(article_ids)}.zip"},
    )


# ---- 内容生成 ----

@router.post("/generate")
async def generate_article(
    req: ArticleGenerateRequest,
    svc: ArticleService = Depends(get_article_service),
    config_svc: ConfigService = Depends(get_config_service),
    knowledge_svc: KnowledgeService = Depends(get_knowledge_service),
    _auth: None = Depends(require_api_key),
):
    """单平台内容生成（SSE 流式）"""
    cfg = await _resolve_cfg(req, config_svc)
    gcfg = await config_svc.get_config()
    brand = req.brand or gcfg.get("brand", "")
    advantages = req.advantages or gcfg.get("advantages", "")

    # Prompt 注入检测（非阻塞，仅警告）
    injection_warnings = _run_injection_check(brand, advantages)

    use_kb = req.use_knowledge or gcfg.get("use_knowledge_base", False)
    knowledge_context = req.knowledge_context
    if use_kb and not knowledge_context:
        knowledge_context = await knowledge_svc.get_context_for_query(req.keyword, brand)

    meta: dict = {
        "keyword": req.keyword,
        "platform": req.platform,
    }
    if injection_warnings:
        meta["warnings"] = injection_warnings

    return create_sse_response(llm_stream_to_sse(
        svc.generate_content_stream(
            keyword=req.keyword, platform=req.platform,
            brand=brand, advantages=advantages, cfg=cfg,
            knowledge_context=knowledge_context,
            word_count=req.word_count, style=req.style,
        ),
        meta=meta,
    ))


@router.post("/batch-generate")
async def batch_generate(
    req: BatchGenerateRequest,
    svc: ArticleService = Depends(get_article_service),
    config_svc: ConfigService = Depends(get_config_service),
    knowledge_svc: KnowledgeService = Depends(get_knowledge_service),
    _auth: None = Depends(require_api_key),
):
    """批量多平台生成（支持混合批量：通过 keyword_platforms 指定每个关键词的目标平台）"""
    cfg = await _resolve_cfg(req, config_svc)
    gcfg = await config_svc.get_config()
    brand = req.brand or gcfg.get("brand", "")
    advantages = req.advantages or gcfg.get("advantages", "")

    # 参数校验：必须提供 (keywords + platforms) 或 keyword_platforms
    has_keyword_platforms = req.keyword_platforms is not None and len(req.keyword_platforms) > 0
    has_keywords = bool(req.keywords)
    has_platforms = bool(req.platforms)
    if not has_keyword_platforms:
        if not has_keywords:
            raise ValidationError("请提供关键词列表（keywords）或关键词-平台映射（keyword_platforms）")
        if not has_platforms:
            raise ValidationError("请提供目标平台列表（platforms）或关键词-平台映射（keyword_platforms）")

    # 构建最终的关键词-平台映射（支持混合模式：
    #   - keyword_platforms 中指定的关键词使用其专属平台列表；
    #   - 其余 keywords 使用统一的 platforms 列表）
    effective_kw_platforms: dict[str, list[str]] = {}
    if has_keyword_platforms:
        effective_kw_platforms.update(req.keyword_platforms)
    # 将 keywords 中未在 keyword_platforms 里出现的关键词，用统一 platforms 补齐
    for kw in req.keywords:
        if kw not in effective_kw_platforms:
            if not has_platforms:
                raise ValidationError(f"关键词「{kw}」未指定平台，且未提供默认 platforms 列表")
            effective_kw_platforms[kw] = list(req.platforms)

    if not effective_kw_platforms:
        raise ValidationError("没有可生成的关键词-平台对，请检查参数")

    # 用于元信息展示：所有关键词、所有涉及的平台
    effective_keywords = list(effective_kw_platforms.keys())
    all_platforms_set: set[str] = set()
    for plats in effective_kw_platforms.values():
        all_platforms_set.update(plats)
    effective_platforms = list(all_platforms_set)

    # Prompt 注入检测（非阻塞，仅警告）
    injection_warnings = _run_injection_check(brand, advantages)

    use_kb = req.use_knowledge or gcfg.get("use_knowledge_base", False)
    knowledge_context = req.knowledge_context
    if use_kb and not knowledge_context:
        first_kw = effective_keywords[0] if effective_keywords else ""
        knowledge_context = await knowledge_svc.get_context_for_query(first_kw, brand) if first_kw else None

    async def _stream_with_warnings():
        """包装 service 流，在 start 事件中注入警告信息"""
        started = False
        async for event in svc.batch_generate_stream(
            keywords=effective_keywords,
            platforms=effective_platforms,
            brand=brand,
            advantages=advantages,
            cfg=cfg,
            knowledge_context=knowledge_context,
            word_count=req.word_count,
            keyword_platforms=effective_kw_platforms,
        ):
            # 在第一个 start 事件中追加注入警告
            if not started and event.get("event") == "start":
                data = dict(event.get("data", {}))
                if injection_warnings:
                    data["warnings"] = injection_warnings
                yield {"event": "start", "data": data}
                started = True
            else:
                yield event

    return create_sse_response(_stream_with_warnings())


# ---- 多模态 ----

# ---- 单篇操作（/{article_id} 路由统一放在此区域，避免遮挡具体路径） ----

@router.get("/{article_id}", response_model=ApiResponse[ArticleResponse])
async def get_article(
    article_id: int = Path(..., ge=1),
    svc: ArticleService = Depends(get_article_service),
    _auth: None = Depends(require_api_key),
):
    art = await svc.get_article(article_id)
    if not art:
        raise NotFoundError("文章不存在")
    return ApiResponse(data=ArticleResponse.model_validate(art))


@router.put("/{article_id}", response_model=ApiResponse[ArticleResponse])
async def update_article(
    article_id: int = Path(..., ge=1), req: ArticleUpdate = ...,
    svc: ArticleService = Depends(get_article_service),
    _auth: None = Depends(require_api_key),
):
    update_data = req.model_dump(exclude={"note"}, exclude_unset=True)
    art = await svc.update_article(
        article_id,
        source="edited",
        note=req.note or "手动编辑",
        **update_data,
    )
    if not art:
        raise NotFoundError("文章不存在")
    return ApiResponse(data=ArticleResponse.model_validate(art))


@router.delete("/{article_id}", response_model=ApiResponse[dict])
async def delete_article(
    article_id: int = Path(..., ge=1),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    svc: ArticleService = Depends(get_article_service),
    _auth: None = Depends(require_api_key),
):
    ok = await svc.delete_article(article_id)
    if not ok:
        raise NotFoundError("文章不存在")
    # 审计日志：记录文章删除
    await log_audit(
        db=db,
        action="article_delete",
        resource_type="article",
        resource_id=str(article_id),
        operator=get_operator_from_request(request),
        details={"article_id": article_id},
    )
    return ApiResponse(data={"ok": ok})


@router.get("/{article_id}/original", response_model=ApiResponse[OriginalContentResponse])
async def get_original_content(
    article_id: int = Path(..., ge=1),
    svc: ArticleService = Depends(get_article_service),
    _auth: None = Depends(require_api_key),
):
    """获取文章原始版本（版本1）的内容"""
    art = await svc.get_article(article_id)
    if not art:
        raise NotFoundError("文章不存在")
    original = await svc.get_original_content(article_id)
    return ApiResponse(data=OriginalContentResponse(
        article_id=article_id,
        original_content=original,
    ))


@router.post("/{article_id}/multimodal")
async def generate_multimodal(
    article_id: int = Path(..., ge=1), req: MultimodalRequest = ...,
    svc: ArticleService = Depends(get_article_service),
    config_svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    """生成多模态描述（SSE 流式）"""
    cfg = await _resolve_cfg(req, config_svc)
    return create_sse_response(llm_stream_to_sse(
        svc.generate_multimodal(
            article_id, cfg, gen_image=req.generate_image_desc,
            gen_video=req.generate_video_script,
        )
    ))


@router.get("/{article_id}/download")
async def download_single(
    article_id: int = Path(..., ge=1),
    svc: ArticleService = Depends(get_article_service),
    _auth: None = Depends(require_api_key),
):
    article = await svc.get_article(article_id)
    if not article:
        raise NotFoundError("文章不存在")
    fname = article.filename or f"article_{article_id}.md"
    encoded_name = quote(fname)
    return Response(
        content=(article.content or "").encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )


# ---- 版本管理 ----

@router.get("/{article_id}/versions", response_model=ApiResponse[list[ArticleVersionResponse]])
async def list_versions(
    article_id: int = Path(..., ge=1),
    svc: ArticleService = Depends(get_article_service),
    _auth: None = Depends(require_api_key),
):
    art = await svc.get_article(article_id)
    if not art:
        raise NotFoundError("文章不存在")
    versions = await svc.get_versions(article_id)
    return ApiResponse(data=[ArticleVersionResponse.model_validate(v) for v in versions])


@router.get("/{article_id}/versions/{version_id}", response_model=ApiResponse[ArticleVersionResponse])
async def get_version(
    article_id: int = Path(..., ge=1), version_id: int = Path(..., ge=1),
    svc: ArticleService = Depends(get_article_service),
    _auth: None = Depends(require_api_key),
):
    art = await svc.get_article(article_id)
    if not art:
        raise NotFoundError("文章不存在")
    v = await svc.get_version(version_id)
    if not v or v.article_id != article_id:
        raise NotFoundError("版本不存在")
    return ApiResponse(data=ArticleVersionResponse.model_validate(v))


@router.post("/{article_id}/rollback/{version_number}", response_model=ApiResponse[ArticleResponse])
async def rollback_version(
    article_id: int = Path(..., ge=1), version_number: int = Path(..., ge=1),
    svc: ArticleService = Depends(get_article_service),
    _auth: None = Depends(require_api_key),
):
    art = await svc.rollback_to_version(article_id, version_number)
    if not art:
        raise NotFoundError("文章或版本不存在")
    return ApiResponse(data=ArticleResponse.model_validate(art))


@router.get("/{article_id}/diff")
async def diff_versions(
    article_id: int = Path(..., ge=1),
    version_a: int = Query(..., ge=1),
    version_b: int = Query(..., ge=1),
    svc: ArticleService = Depends(get_article_service),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_api_key),
):
    """对比两个版本的差异（HTML diff）"""
    art = await svc.get_article(article_id)
    if not art:
        raise NotFoundError("文章不存在")
    va_res = await db.execute(
        select(ArticleVersion).where(
            ArticleVersion.article_id == article_id, ArticleVersion.version_number == version_a
        )
    )
    vb_res = await db.execute(
        select(ArticleVersion).where(
            ArticleVersion.article_id == article_id, ArticleVersion.version_number == version_b
        )
    )
    va = va_res.scalar_one_or_none()
    vb = vb_res.scalar_one_or_none()
    if not va or not vb:
        raise NotFoundError("版本不存在")
    diff = compute_diff(va.content or "", vb.content or "")
    diff["version_a"] = version_a
    diff["version_b"] = version_b
    return ApiResponse(data=diff)
