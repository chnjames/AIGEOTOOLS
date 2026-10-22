"""资源库 API"""
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_optimization_service, require_api_key
from app.schemas.common import ApiResponse
from app.services.optimization_service import OptimizationService
from app.services.resource_service import get_resources, get_categories, get_verify_query_templates

router = APIRouter(prefix="/resources", tags=["GEO资源库"])


@router.get("", response_model=ApiResponse[list])
async def list_resources(
    category: str = "",
    _auth: None = Depends(require_api_key),
):
    return ApiResponse(data=get_resources(category))


@router.get("/categories", response_model=ApiResponse[list[str]])
async def list_categories(_auth: None = Depends(require_api_key)):
    return ApiResponse(data=get_categories())


@router.get("/techniques", response_model=ApiResponse[list])
async def get_techniques(
    svc: OptimizationService = Depends(get_optimization_service),
    _auth: None = Depends(require_api_key),
):
    return ApiResponse(data=svc.get_techniques())


@router.get("/query-templates", response_model=ApiResponse[list])
async def get_query_templates(
    keyword: str = Query("", description="目标关键词"),
    competitor: str = Query("", description="主要竞品名称"),
    _auth: None = Depends(require_api_key),
):
    """获取 GEO 验证查询模板（4 类：直接推荐/对比评测/场景问题/知识科普）"""
    return ApiResponse(data=get_verify_query_templates(keyword, competitor))
