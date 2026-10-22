"""配置管理 API"""
import asyncio

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_config_service, require_api_key, get_db
from app.schemas.common import ApiResponse
from app.schemas.config import AppConfigResponse, AppConfigUpdate, ProviderTestRequest, ProviderTestResponse
from app.services.config_service import ConfigService
from app.services.audit_service import log_audit, get_operator_from_request
from app.services.llm_factory import build_llm, get_default_model
from app.core.exceptions import GEOAppException, LLMError

router = APIRouter(prefix="/config", tags=["配置管理"])


@router.get("", response_model=ApiResponse[AppConfigResponse])
async def get_config(
    svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    resp = await svc.get_response()
    return ApiResponse(data=resp)


@router.put("", response_model=ApiResponse[AppConfigResponse])
async def update_config(
    update: AppConfigUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    resp = await svc.update_from_schema(update)
    # 审计日志：记录配置变更（仅记录变更的字段名，不记录敏感值）
    changed_fields = update.model_dump(exclude_unset=True)
    # 过滤掉敏感字段的具体值，仅记录字段名
    sensitive_fields = {"gen_api_key", "tongyi_wanxiang_api_key", "verify_keys"}
    audit_details = {
        "changed_fields": list(changed_fields.keys()),
        "sensitive_fields_changed": [
            f for f in changed_fields if f in sensitive_fields
        ],
    }
    await log_audit(
        db=db,
        action="config_update",
        resource_type="config",
        resource_id="1",
        operator=get_operator_from_request(request),
        details=audit_details,
    )
    return ApiResponse(data=resp)


@router.post("/test", response_model=ApiResponse[ProviderTestResponse])
async def test_provider(
    req: ProviderTestRequest,
    _auth: None = Depends(require_api_key),
):
    model = req.model or get_default_model(req.provider)
    base_url = req.base_url or ""
    try:
        llm = build_llm(req.provider, req.api_key, model, 0.7, base_url=base_url)
        result = await asyncio.wait_for(llm.ainvoke("回复'连接成功'四个字"), timeout=30)
        return ApiResponse(data=ProviderTestResponse(success=True, message="连接成功"))
    except GEOAppException as e:
        return ApiResponse(data=ProviderTestResponse(success=False, message=e.message))
    except asyncio.TimeoutError:
        return ApiResponse(data=ProviderTestResponse(
            success=False,
            message=f"连接超时（30秒），请检查：1) API Key 是否正确 2) 模型名称 '{model}' 是否可用 3) 网络是否可达该提供商",
        ))
    except ValueError as e:
        # build_llm 抛出的 ValueError，包含具体的初始化失败原因
        return ApiResponse(data=ProviderTestResponse(
            success=False,
            message=f"初始化失败: {e}",
        ))
    except Exception as e:
        # 其他未预期错误，返回具体异常类型和信息
        return ApiResponse(data=ProviderTestResponse(
            success=False,
            message=f"{type(e).__name__}: {e}",
        ))
