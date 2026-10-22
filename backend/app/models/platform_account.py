"""平台账号表 ORM 模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, Boolean, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PlatformAccount(Base, TimestampMixin):
    __tablename__ = "platform_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)
    account_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, default="")
    api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON 字符串
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="1")
    brand: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, default="")

    __table_args__ = (
        UniqueConstraint("platform", "brand", "account_name", name="uq_platform_brand_account"),
        Index("ix_pa_brand", "brand"),
        Index("ix_pa_platform", "platform"),
    )
