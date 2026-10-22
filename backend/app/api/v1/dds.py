"""DDS 三维评分 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_dds_service, require_api_key, get_config_service, get_db
from app.api.sse import create_sse_response
from app.schemas.common import ApiResponse
from app.schemas.dds import DDSScoreRequest
from app.models.dds_score import DDSScore
from app.services.dds_service import DDSService
from app.services.config_service import ConfigService
from app.services.llm_service import LLMConfig
from app.services.llm_factory import get_default_model

router = APIRouter(prefix="/dds", tags=["DDS三维评分"])


@router.post("/score")
async def score_dds(
    req: DDSScoreRequest,
    svc: DDSService = Depends(get_dds_service),
    config_svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    """DDS 三维评分（SSE 流式）"""
    cfg = await config_svc.get_config()
    provider = req.provider or cfg.get("gen_provider", "DeepSeek")
    api_key = req.api_key or cfg.get("gen_api_key", "")
    model = req.model or get_default_model(provider)
    temperature = req.temperature
    llm_cfg = LLMConfig(provider=provider, api_key=api_key, model=model, temperature=temperature)

    async def _stream():
        yield {"event": "start", "data": {"message": "开始 DDS 三维评分..."}}
        full_chunks = []
        async for event in svc.score_content(
            content=req.content,
            brand=req.brand or cfg.get("brand", ""),
            cfg=llm_cfg,
            article_id=req.article_id,
        ):
            yield event
            if event.get("event") == "chunk":
                full_chunks.append(event["data"].get("content", ""))
        yield {"event": "done", "data": {}}

    return create_sse_response(_stream())


@router.get("/history", response_model=ApiResponse)
async def dds_history(
    article_id: int = Query(0, ge=0),
    brand: str = "",
    limit: int = Query(20, ge=1, le=1000),
    svc: DDSService = Depends(get_dds_service),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_api_key),
):
    """获取 DDS 评分历史"""
    # NOTE: Direct DB access used here; should be moved to DDSService in future refactor
    stmt = select(DDSScore).order_by(desc(DDSScore.created_at)).limit(limit)
    if article_id:
        stmt = stmt.where(DDSScore.article_id == article_id)
    if brand:
        stmt = stmt.where(DDSScore.brand == brand)
    result = (await db.execute(stmt)).scalars().all()
    items = []
    for r in result:
        items.append({
            "id": r.id,
            "semantic_depth": r.semantic_depth,
            "data_support": r.data_support,
            "authoritative_source": r.authoritative_source,
            "total_score": r.total_score,
            "article_id": r.article_id,
            "brand": r.brand,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return ApiResponse(data=items)
