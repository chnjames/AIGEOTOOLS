"""API Key 认证（常量时间比较，防时序攻击）"""
import hmac

from fastapi import Header

from app.core.config import get_settings
from app.core.exceptions import AuthError

settings = get_settings()


def verify_api_key(x_api_key: str = Header(default="", alias="X-API-Key")) -> None:
    """验证 API Key（常量时间比较，防时序攻击）"""
    if not settings.API_KEY:
        return  # 未配置 API Key，跳过认证
    if not hmac.compare_digest(x_api_key or "", settings.API_KEY):
        raise AuthError("无效的 API Key")
