"""结构化数据 Schema 工具 API（增强版）"""
from typing import Literal

from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel, Field

from app.api.deps import get_schema_service, require_api_key, get_config_service
from app.schemas.common import ApiResponse
from app.services.schema_service import SchemaService
from app.services.config_service import ConfigService
from app.services.llm_service import LLMConfig
from app.services.llm_factory import get_default_model

router = APIRouter(prefix="/schema", tags=["结构化数据Schema"])


class SchemaGenerateRequest(BaseModel):
    content: str = Field(..., max_length=100000)
    schema_type: Literal["Article", "FAQPage", "HowTo", "Product", "Organization", "Review", "BreadcrumbList", "WebPage"] = "Article"
    brand: str = ""
    temperature: float = Field(0.3, ge=0, le=2)
    provider: str | None = None
    api_key: str | None = None


class SchemaValidateRequest(BaseModel):
    json_ld: str
    schema_type: str = ""


@router.get("/types", response_model=ApiResponse)
async def list_schema_types(
    svc: SchemaService = Depends(get_schema_service),
    _auth: None = Depends(require_api_key),
):
    """获取支持的 Schema 类型列表"""
    return ApiResponse(data=svc.get_supported_types())


@router.post("/recommend", response_model=ApiResponse)
async def recommend_types(
    body: dict = Body(...),
    svc: SchemaService = Depends(get_schema_service),
    _auth: None = Depends(require_api_key),
):
    """根据内容推荐 Schema 类型"""
    recs = svc.recommend_schema_types(body.get("content", ""))
    return ApiResponse(data=recs)


@router.post("/validate", response_model=ApiResponse)
async def validate_schema(
    body: SchemaValidateRequest,
    svc: SchemaService = Depends(get_schema_service),
    _auth: None = Depends(require_api_key),
):
    """验证 JSON-LD Schema 有效性"""
    result = svc.validate_schema(body.json_ld, body.schema_type)
    return ApiResponse(data=result)


@router.post("/generate", response_model=ApiResponse)
async def generate_schema(
    body: SchemaGenerateRequest,
    svc: SchemaService = Depends(get_schema_service),
    config_svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    """生成 JSON-LD Schema"""
    cfg_data = await config_svc.get_config()
    provider = body.provider or cfg_data.get("gen_provider", "DeepSeek")
    api_key = body.api_key or cfg_data.get("gen_api_key", "")
    model = get_default_model(provider)
    llm_cfg = LLMConfig(provider=provider, api_key=api_key, model=model, temperature=body.temperature)
    result = await svc.generate_schema(body.content, body.schema_type, body.brand, llm_cfg)
    return ApiResponse(data=result)
