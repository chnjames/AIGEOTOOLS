"""ROI 归因与效果分析 API"""
from datetime import datetime as dt

from fastapi import APIRouter, Depends, Query, Body
from app.api.deps import get_attribution_service, get_report_service, require_api_key
from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.common import ApiResponse
from app.services.attribution_service import AttributionService
from app.services.report_service import ReportService

router = APIRouter(prefix="/analytics", tags=["ROI归因分析"])


@router.get("/roi-overview", response_model=ApiResponse)
async def roi_overview(
    brand: str = "",
    days: int = Query(30, ge=1, le=365),
    svc: AttributionService = Depends(get_attribution_service),
    _auth: None = Depends(require_api_key),
):
    """ROI 概览"""
    data = await svc.get_roi_overview(brand, days)
    return ApiResponse(data=data)


@router.get("/action-ranking", response_model=ApiResponse)
async def action_ranking(
    brand: str = "",
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    svc: AttributionService = Depends(get_attribution_service),
    _auth: None = Depends(require_api_key),
):
    """优化动作效果排名"""
    data = await svc.get_action_effect_ranking(brand, days, limit)
    return ApiResponse(data=data)


@router.get("/timeline", response_model=ApiResponse)
async def optimization_timeline(
    brand: str = "",
    days: int = Query(30, ge=1, le=365),
    svc: AttributionService = Depends(get_attribution_service),
    _auth: None = Depends(require_api_key),
):
    """优化时间线（含提及率趋势和操作标注）"""
    data = await svc.get_optimization_timeline(brand, days)
    return ApiResponse(data=data)


@router.get("/ab-comparison", response_model=ApiResponse)
async def ab_comparison(
    brand: str = "",
    svc: AttributionService = Depends(get_attribution_service),
    _auth: None = Depends(require_api_key),
):
    """A/B 对比（优化前后）"""
    data = await svc.get_ab_comparison(brand)
    return ApiResponse(data=data)


@router.post("/record-action", response_model=ApiResponse)
async def record_action(
    body: dict = Body(...),
    svc: AttributionService = Depends(get_attribution_service),
    _auth: None = Depends(require_api_key),
):
    """记录优化动作（供前端手动标记或服务调用）"""
    action = await svc.record_action(
        action_type=body.get("action_type", "other"),
        description=body.get("description", ""),
        brand=body.get("brand", ""),
        article_id=body.get("article_id"),
        keyword=body.get("keyword", ""),
        platform=body.get("platform", ""),
        score_before=body.get("score_before"),
        score_after=body.get("score_after"),
    )
    return ApiResponse(data={"id": action.id, "action_type": action.action_type})


# --- 营销报告 ---
report_router = APIRouter(prefix="/reports2", tags=["营销报告"])


@report_router.post("/generate", response_model=ApiResponse)
async def generate_report(
    body: dict = Body(...),
    svc: ReportService = Depends(get_report_service),
    _auth: None = Depends(require_api_key),
):
    """生成营销报告"""
    try:
        d_from = dt.fromisoformat(body["date_from"]) if body.get("date_from") else None
    except (ValueError, TypeError):
        raise ValidationError("date_from 格式无效，请使用 ISO 格式（YYYY-MM-DD）")
    try:
        d_to = dt.fromisoformat(body["date_to"]) if body.get("date_to") else None
    except (ValueError, TypeError):
        raise ValidationError("date_to 格式无效，请使用 ISO 格式（YYYY-MM-DD）")
    report = await svc.generate_report(
        report_type=body.get("report_type", "weekly"),
        brand=body.get("brand", ""),
        date_from=d_from, date_to=d_to,
        title=body.get("title", ""),
    )
    return ApiResponse(data={"id": report.id, "title": report.title, "share_token": report.share_token})


@report_router.get("/list", response_model=ApiResponse)
async def list_reports(
    brand: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: ReportService = Depends(get_report_service),
    _auth: None = Depends(require_api_key),
):
    """报告列表"""
    data = await svc.list_reports(brand, page, page_size)
    return ApiResponse(data=data)


@report_router.get("/{report_id}", response_model=ApiResponse)
async def get_report(
    report_id: int,
    svc: ReportService = Depends(get_report_service),
    _auth: None = Depends(require_api_key),
):
    """获取报告详情"""
    data = await svc.get_report(report_id)
    return ApiResponse(data=data)


@report_router.get("/share/{token}", response_model=ApiResponse)
async def get_shared_report(
    token: str,
    svc: ReportService = Depends(get_report_service),
):
    """通过分享链接查看报告（无需认证）"""
    data = await svc.get_by_share_token(token)
    if not data:
        raise NotFoundError("报告不存在或已失效")
    return ApiResponse(data=data)


@report_router.delete("/{report_id}", response_model=ApiResponse)
async def delete_report(
    report_id: int,
    svc: ReportService = Depends(get_report_service),
    _auth: None = Depends(require_api_key),
):
    """删除报告"""
    ok = await svc.delete_report(report_id)
    if not ok:
        raise NotFoundError("报告不存在")
    return ApiResponse(data={"deleted": ok})
