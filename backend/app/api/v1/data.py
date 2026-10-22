"""数据管理 API - 导出/导入/清理/存储监控/审计日志"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_data_service, require_api_key
from app.api.sse import create_sse_response
from app.core.exceptions import ValidationError, NotFoundError
from app.core.logging import get_logger
from app.models.audit_log import AuditLog
from app.schemas.common import ApiResponse, PageResponse
from app.services.data_service import DataService

logger = get_logger(__name__)
router = APIRouter(prefix="/data", tags=["数据管理"], dependencies=[Depends(require_api_key)])


# ── 存储监控 ──────────────────────────────────────────────

@router.get("/storage", response_model=ApiResponse[dict])
async def storage_stats(svc: DataService = Depends(get_data_service)):
    """获取当前存储统计（数据库大小、各表记录数、知识库大小）"""
    stats = await svc.get_storage_stats()
    return ApiResponse(data=stats)


# ── 全量导出 / 导入 ────────────────────────────────────────

@router.get("/export/all")
async def export_all(svc: DataService = Depends(get_data_service)):
    """全量导出为 JSON 文件"""
    data = await svc.export_all()
    content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    filename = f"geo_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    return Response(
        content=content.encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/csv/{module}")
async def export_csv(module: str, svc: DataService = Depends(get_data_service)):
    """按模块导出 CSV（keywords/articles/verify_results/api_calls）"""
    supported = {"keywords", "articles", "verify_results", "api_calls"}
    if module not in supported:
        raise ValidationError(f"不支持导出的模块：{module}，支持：{', '.join(supported)}")
    content = await svc.export_csv(module)
    raw_filename = f"{module}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    filename = quote(raw_filename)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


class ImportBody(BaseModel):
    data: dict
    strategy: str = "skip"  # skip / overwrite / append


@router.post("/import", response_model=ApiResponse[dict])
async def import_data(body: ImportBody, svc: DataService = Depends(get_data_service)):
    """从导出文件导入数据"""
    if body.strategy not in {"skip", "overwrite", "append"}:
        raise ValidationError("strategy 必须是 skip/overwrite/append 之一")
    result = await svc.import_data(body.data, strategy=body.strategy)
    return ApiResponse(data=result, message="导入完成")


# ── 数据清理 ──────────────────────────────────────────────

class CleanupBody(BaseModel):
    days: int = Field(90, ge=1, le=3650)
    tables: list[str] = ["api_calls", "workflow_executions", "monitor_results"]


@router.post("/cleanup", response_model=ApiResponse[dict])
async def cleanup_old_data(body: CleanupBody, svc: DataService = Depends(get_data_service)):
    """清理 N 天前的指定数据"""
    supported = {"api_calls", "verify_results", "workflow_executions", "monitor_results"}
    invalid = [t for t in body.tables if t not in supported]
    if invalid:
        raise ValidationError(f"不支持清理的表：{', '.join(invalid)}")
    result = await svc.cleanup_old_data(body.days, body.tables)
    return ApiResponse(data=result, message=f"已清理 {body.days} 天前的数据")


# ── 用户数据管理（GDPR 被遗忘权 / 数据可携带权）──────────

@router.get("/user-data", response_model=ApiResponse[dict])
async def export_user_data(
    brand: str = Query(..., min_length=1, description="品牌名称"),
    svc: DataService = Depends(get_data_service),
):
    """导出指定品牌的全部用户数据（GDPR「数据可携带权」）

    返回该品牌下所有业务数据的 JSON，包括 keywords、articles、
    article_versions、optimizations、verify_results、monitor_tasks、
    monitor_results、alerts、platform_accounts、workflows、
    workflow_executions、knowledge_docs（元数据）、api_calls、
    dds_scores、optimization_actions、marketing_reports、publish_records。
    """
    try:
        data = await svc.export_user_data(brand)
        return ApiResponse(data=data, message=f"品牌 '{brand}' 数据导出完成")
    except ValueError as e:
        raise ValidationError(str(e))


@router.delete("/user-data", response_model=ApiResponse[dict])
async def delete_user_data(
    brand: str = Query(..., min_length=1, description="品牌名称"),
    svc: DataService = Depends(get_data_service),
):
    """删除指定品牌的所有用户数据（GDPR「被遗忘权」）

    不可逆操作，删除该品牌下的所有业务数据，包括：
    keywords、articles（含 article_versions、publish_records）、
    optimizations、verify_results、monitor_tasks（含 monitor_results、alerts）、
    platform_accounts、workflows（含 workflow_executions）、
    knowledge_docs（含磁盘文件和向量索引）、api_calls、dds_scores、
    optimization_actions、marketing_reports。

    审计日志会被保留以记录此次删除操作。
    返回各类型数据的删除计数。
    """
    try:
        result = await svc.delete_all_user_data(brand)
        return ApiResponse(
            data=result,
            message=f"品牌 '{brand}' 数据已删除，共 {result.get('total_deleted', 0)} 条记录",
        )
    except ValueError as e:
        raise ValidationError(str(e))


# ── 审计日志 ──────────────────────────────────────────────

@router.get("/audit-logs", response_model=ApiResponse[PageResponse])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """查看操作审计日志（分页）"""
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))
    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
        count_query = count_query.where(AuditLog.resource_type == resource_type)
    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    items = []
    for log in result.scalars().all():
        detail = None
        if log.detail:
            try:
                detail = json.loads(log.detail)
            except json.JSONDecodeError:
                detail = log.detail
        items.append({
            "id": log.id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "detail": detail,
            "result": log.result,
            "error_message": log.error_message,
            "operator": log.operator,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ApiResponse(data=PageResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages,
    ))
