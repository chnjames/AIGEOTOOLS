"""平台模板管理 API"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import get_template_service, require_api_key
from app.core.exceptions import ValidationError, NotFoundError
from app.core.logging import get_logger
from app.schemas.common import ApiResponse
from app.services.template_service import TemplateService

logger = get_logger(__name__)
router = APIRouter(prefix="/templates", tags=["平台模板"], dependencies=[Depends(require_api_key)])


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    style_instruction: str
    filename_suffix: str = Field(".md", max_length=20)
    group_name: str = "其他"
    word_count_default: int = Field(1500, ge=100, le=100000)


class TemplateUpdate(BaseModel):
    style_instruction: Optional[str] = None
    filename_suffix: Optional[str] = Field(None, max_length=20)
    group_name: Optional[str] = None
    word_count_default: Optional[int] = Field(None, ge=100, le=100000)
    is_active: Optional[bool] = None


class TemplateImportBody(BaseModel):
    templates: list[dict]
    strategy: str = "skip"  # skip / overwrite / append


@router.get("", response_model=ApiResponse[list])
async def list_templates(
    active_only: bool = Query(True),
    svc: TemplateService = Depends(get_template_service),
):
    """获取平台模板列表"""
    templates = await svc.list_templates(active_only=active_only)
    items = [{
        "id": t.id, "name": t.name, "style": t.style_instruction,
        "filename_suffix": t.filename_suffix, "group": t.group_name,
        "is_default": t.is_default, "is_active": t.is_active,
        "word_count_default": t.word_count_default,
    } for t in templates]
    return ApiResponse(data=items)


@router.get("/groups", response_model=ApiResponse[list])
async def get_platform_groups(svc: TemplateService = Depends(get_template_service)):
    """获取分组平台列表"""
    return ApiResponse(data=svc.get_platform_groups())


@router.get("/config", response_model=ApiResponse[dict])
async def get_platform_config(svc: TemplateService = Depends(get_template_service)):
    """获取平台配置 dict（兼容 PLATFORM_CONFIG 格式）"""
    return ApiResponse(data=svc.get_platform_config())


@router.post("", response_model=ApiResponse[dict])
async def create_template(body: TemplateCreate, svc: TemplateService = Depends(get_template_service)):
    """创建自定义平台模板"""
    t = await svc.create_template(
        name=body.name, style_instruction=body.style_instruction,
        filename_suffix=body.filename_suffix, group_name=body.group_name,
        word_count_default=body.word_count_default,
    )
    return ApiResponse(data={"id": t.id, "name": t.name}, message="模板创建成功")


@router.put("/{tid}", response_model=ApiResponse[dict])
async def update_template(
    tid: int, body: TemplateUpdate, svc: TemplateService = Depends(get_template_service),
):
    """更新平台模板"""
    t = await svc.update_template(tid, **body.model_dump(exclude_none=True))
    if not t:
        raise NotFoundError("模板不存在")
    return ApiResponse(data={"id": t.id}, message="模板更新成功")


@router.delete("/{tid}", response_model=ApiResponse[dict])
async def delete_template(tid: int, svc: TemplateService = Depends(get_template_service)):
    """删除/禁用平台模板（内置模板只能禁用）"""
    ok = await svc.delete_template(tid)
    if not ok:
        raise NotFoundError("模板不存在")
    return ApiResponse(message="模板已删除/禁用")


@router.post("/{tid}/reset", response_model=ApiResponse[dict])
async def reset_template(tid: int, svc: TemplateService = Depends(get_template_service)):
    """重置默认模板为原始配置"""
    ok = await svc.reset_default(tid)
    if not ok:
        raise ValidationError("仅默认模板可重置")
    return ApiResponse(message="模板已重置为默认配置")


@router.get("/export", response_model=ApiResponse[list])
async def export_templates(svc: TemplateService = Depends(get_template_service)):
    """导出所有模板配置"""
    return ApiResponse(data=await svc.export_templates())


@router.post("/import", response_model=ApiResponse[dict])
async def import_templates(body: TemplateImportBody, svc: TemplateService = Depends(get_template_service)):
    """导入模板配置"""
    if body.strategy not in {"skip", "overwrite", "append"}:
        raise ValidationError("strategy 必须是 skip/overwrite/append")
    result = await svc.import_templates(body.templates, strategy=body.strategy)
    return ApiResponse(data=result, message="模板导入完成")
