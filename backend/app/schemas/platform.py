"""平台账号与发布相关 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PlatformAccountCreate(BaseModel):
    platform: str = Field(..., min_length=1)
    account_type: str = "token"
    account_name: str = ""
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    config_json: Optional[dict] = None
    brand: str = ""


class PlatformAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    config_json: Optional[dict] = None
    is_active: Optional[bool] = None


class PlatformAccountResponse(BaseModel):
    id: int
    platform: str
    account_type: str
    account_name: Optional[str] = None
    is_active: bool = True
    brand: Optional[str] = None
    has_api_key: bool = False
    has_token: bool = False
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PlatformInfo(BaseModel):
    key: str
    name: str
    publish_methods: list[str]
    icon: str = ""


class PublishRequest(BaseModel):
    platform: str
    publish_method: str = "copy"  # copy / github / api
    config: Optional[dict] = None


class PublishResponse(BaseModel):
    success: bool
    platform: str
    publish_url: Optional[str] = None
    message: str = ""
    content: Optional[str] = None
    filename: Optional[str] = None


class PublishRecordResponse(BaseModel):
    id: int
    article_id: Optional[int] = None
    platform: str
    publish_method: str
    publish_status: str
    publish_url: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RetryPublishRequest(BaseModel):
    """重试发布请求体（config 仅在需要覆盖原有配置时传入，如 GitHub token/repo）"""
    config: Optional[dict] = None
