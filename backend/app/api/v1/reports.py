"""数据报表 API"""
import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_roi_service, get_verify_service, get_config_service, require_api_key,
)
from app.core.database import get_db
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.roi import KPIResponse, CostReportResponse, MentionReportResponse, ROIReportResponse
from app.services.roi_service import ROIService
from app.services.verify_service import VerifyService
from app.services.config_service import ConfigService
from app.api.sse import create_sse_response
from app.prompts.scoring_prompts import CONFIG_OPTIMIZE_PROMPT
from app.services.llm_service import LLMService, LLMConfig
from app.services.llm_factory import get_default_model
from app.utils.text_utils import extract_json
from app.models.api_call import ApiCall as ApiCallModel

router = APIRouter(prefix="/reports", tags=["AI数据报表"])


@router.get("/kpi", response_model=ApiResponse[KPIResponse])
async def get_kpi(
    brand: str = "",
    svc: ROIService = Depends(get_roi_service),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_api_key),
):
    result = await svc.get_kpi(db, brand)
    return ApiResponse(data=KPIResponse(**result))


@router.get("/costs", response_model=ApiResponse[CostReportResponse])
async def get_costs(
    brand: str = "",
    svc: ROIService = Depends(get_roi_service),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_api_key),
):
    result = await svc.get_cost_report(db, brand)
    return ApiResponse(data=CostReportResponse(**result))


@router.get("/mentions", response_model=ApiResponse[MentionReportResponse])
async def get_mentions(
    brand: str = "",
    svc: ROIService = Depends(get_roi_service),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_api_key),
):
    result = await svc.get_mention_report(db, brand)
    return ApiResponse(data=MentionReportResponse(**result))


@router.get("/roi", response_model=ApiResponse[ROIReportResponse])
async def get_roi(
    brand: str = "",
    svc: ROIService = Depends(get_roi_service),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_api_key),
):
    result = await svc.get_roi_report(db, brand)
    return ApiResponse(data=ROIReportResponse(**result))


@router.get("/api-calls")
async def get_api_calls(
    brand: str = "",
    operation_type: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_api_key),
):
    """获取 API 调用历史记录（支持按操作类型筛选，返回全量汇总）"""
    # 构建基础查询（含筛选条件）
    base_filters = []
    if brand:
        base_filters.append(ApiCallModel.brand == brand)
    if operation_type:
        base_filters.append(ApiCallModel.operation_type == operation_type)

    stmt = select(ApiCallModel).order_by(desc(ApiCallModel.created_at))
    for f in base_filters:
        stmt = stmt.where(f)

    # 全量汇总（基于所有匹配记录，非仅当前页）
    summary_stmt = select(
        func.count(ApiCallModel.id).label("total_calls"),
        func.coalesce(func.sum(ApiCallModel.input_tokens + ApiCallModel.output_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(ApiCallModel.cost_cny), 0).label("total_cost_cny"),
        func.coalesce(func.sum(ApiCallModel.cost_usd), 0).label("total_cost_usd"),
    )
    for f in base_filters:
        summary_stmt = summary_stmt.where(f)
    summary_row = (await db.execute(summary_stmt)).one()
    summary = {
        "total_calls": summary_row.total_calls or 0,
        "total_tokens": summary_row.total_tokens or 0,
        "total_cost_cny": float(summary_row.total_cost_cny or 0),
        "total_cost_usd": float(summary_row.total_cost_usd or 0),
    }

    # 分页数据
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = (await db.execute(stmt)).scalars().all()
    items = []
    for r in result:
        items.append({
            "id": r.id,
            "operation_type": r.operation_type,
            "provider": r.provider,
            "model": r.model,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "cost_usd": r.cost_usd,
            "cost_cny": r.cost_cny,
            "keyword": r.keyword,
            "platform": r.platform,
            "brand": r.brand,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return ApiResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        "summary": summary,
    })


@router.get("/negative")
async def get_negative_mentions(
    brand: str = "",
    svc: VerifyService = Depends(get_verify_service),
    _auth: None = Depends(require_api_key),
):
    result = await svc.get_negative_mentions(brand)
    return ApiResponse(data=result)


@router.get("/optimization-suggestions", response_model=ApiResponse[list])
async def get_suggestions(
    brand: str = "",
    svc: ROIService = Depends(get_roi_service),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_api_key),
):
    report = await svc.get_cost_report(db, brand)
    suggestions = svc._get_suggestions(report)
    return ApiResponse(data=suggestions)


@router.post("/config-optimizer")
async def config_optimizer(
    request: dict,
    config_svc: ConfigService = Depends(get_config_service),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(require_api_key),
):
    """配置优化建议（SSE 流式）"""
    cfg = await config_svc.get_config()
    provider = request.get("provider") or cfg.get("gen_provider", "DeepSeek")
    api_key = request.get("api_key") or cfg.get("gen_api_key", "")
    model = request.get("model") or get_default_model(provider)
    temperature = request.get("temperature", 0.7) or cfg.get("temperature", 0.7)
    brand = request.get("brand", "") or cfg.get("brand", "")
    advantages = request.get("advantages", "") or cfg.get("advantages", "")
    competitors = request.get("competitors", [])

    competitors_str = "\n".join(competitors) if competitors else cfg.get("competitors", "")
    llm_cfg = LLMConfig(provider=provider, api_key=api_key, model=model, temperature=temperature)
    llm_svc = LLMService(db)

    prompt = CONFIG_OPTIMIZE_PROMPT.format(
        current_config=json.dumps(cfg, ensure_ascii=False, indent=2),
        brand=brand, advantages=advantages, competitors=competitors_str,
    )

    async def _stream():
        yield {"event": "start", "data": {"message": "正在分析配置..."}}
        full = []
        async for chunk in llm_svc.stream(prompt, llm_cfg):
            full.append(chunk)
            yield {"event": "chunk", "data": {"content": chunk}}
        result = "".join(full)
        parsed = extract_json(result)
        yield {"event": "complete", "data": {"result": parsed or {"raw": result}}}

    return create_sse_response(_stream())
