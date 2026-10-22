"""平台账号与发布 API"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_platform_service, require_api_key, get_db
from app.core.exceptions import NotFoundError
from app.schemas.common import ApiResponse
from app.schemas.platform import (
    PlatformAccountCreate, PlatformAccountUpdate, PlatformAccountResponse,
    PlatformInfo, PublishRequest, PublishResponse, PublishRecordResponse,
    RetryPublishRequest,
)
from app.services.platform_service import PlatformService
from app.services.audit_service import log_audit, get_operator_from_request

router = APIRouter(prefix="/platforms", tags=["平台同步"])


@router.get("/supported", response_model=ApiResponse[list[PlatformInfo]])
async def supported_platforms(
    svc: PlatformService = Depends(get_platform_service),
    _auth: None = Depends(require_api_key),
):
    return ApiResponse(data=[PlatformInfo(**p) for p in svc.get_supported_platforms()])


@router.get("/accounts", response_model=ApiResponse[list[dict]])
async def list_accounts(
    brand: str = "",
    svc: PlatformService = Depends(get_platform_service),
    _auth: None = Depends(require_api_key),
):
    accts = await svc.get_accounts(brand)
    return ApiResponse(data=[svc.account_to_response(a) for a in accts])


@router.post("/accounts", response_model=ApiResponse[dict])
async def create_account(
    req: PlatformAccountCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    svc: PlatformService = Depends(get_platform_service),
    _auth: None = Depends(require_api_key),
):
    acct = await svc.add_account(
        platform=req.platform, account_type=req.account_type,
        account_name=req.account_name, api_key=req.api_key or "",
        api_secret=req.api_secret or "", access_token=req.access_token or "",
        config_json=req.config_json, brand=req.brand,
    )
    # 审计日志：记录平台账号绑定（不记录凭据明文）
    await log_audit(
        db=db,
        action="account_create",
        resource_type="platform_account",
        resource_id=str(acct.id),
        operator=get_operator_from_request(request),
        details={
            "platform": req.platform,
            "account_type": req.account_type,
            "account_name": req.account_name,
            "brand": req.brand,
        },
    )
    return ApiResponse(data=svc.account_to_response(acct))


@router.put("/accounts/{account_id}", response_model=ApiResponse[dict])
async def update_account(
    account_id: int, req: PlatformAccountUpdate,
    svc: PlatformService = Depends(get_platform_service),
    _auth: None = Depends(require_api_key),
):
    acct = await svc.update_account(account_id, **req.model_dump(exclude_unset=True))
    if not acct:
        raise NotFoundError("平台账号不存在")
    return ApiResponse(data=svc.account_to_response(acct))


@router.delete("/accounts/{account_id}", response_model=ApiResponse[dict])
async def delete_account(
    account_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    svc: PlatformService = Depends(get_platform_service),
    _auth: None = Depends(require_api_key),
):
    ok = await svc.delete_account(account_id)
    if not ok:
        raise NotFoundError("平台账号不存在")
    # 审计日志：记录平台账号删除
    await log_audit(
        db=db,
        action="account_delete",
        resource_type="platform_account",
        resource_id=str(account_id),
        operator=get_operator_from_request(request),
        details={"account_id": account_id},
    )
    return ApiResponse(data={"ok": ok})


@router.post("/publish/{article_id}", response_model=ApiResponse[PublishResponse])
async def publish_article(
    article_id: int, req: PublishRequest,
    svc: PlatformService = Depends(get_platform_service),
    _auth: None = Depends(require_api_key),
):
    result = await svc.publish_article(
        article_id, req.platform, req.publish_method, req.config
    )
    if not result.get("success", False) and "不存在" in result.get("message", ""):
        raise NotFoundError(result["message"])
    return ApiResponse(data=PublishResponse(**result))


@router.post("/publish/{record_id}/retry", response_model=ApiResponse[PublishResponse])
async def retry_publish(
    record_id: int,
    req: Optional[RetryPublishRequest] = None,
    svc: PlatformService = Depends(get_platform_service),
    _auth: None = Depends(require_api_key),
):
    """重试失败的发布记录

    对状态为 failed 的发布记录重新执行发布操作。
    对于 GitHub 等需要配置的发布方式，可在请求体中传入 config 覆盖原有配置。
    copy 模式无需请求体，可直接 POST 空请求。
    """
    record = await svc.get_publish_record(record_id)
    if not record:
        raise NotFoundError("发布记录不存在")
    config = req.config if req else None
    result = await svc.retry_publish(record_id, config=config)
    return ApiResponse(data=PublishResponse(**result))


@router.get("/publish-records", response_model=ApiResponse[list[PublishRecordResponse]])
async def publish_records(
    article_id: int = Query(0, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: PlatformService = Depends(get_platform_service),
    _auth: None = Depends(require_api_key),
):
    aid = article_id if article_id > 0 else None
    all_records = await svc.get_publish_records(aid)
    start = (page - 1) * page_size
    end = start + page_size
    records = all_records[start:end]
    return ApiResponse(data=[PublishRecordResponse.model_validate(r) for r in records])
