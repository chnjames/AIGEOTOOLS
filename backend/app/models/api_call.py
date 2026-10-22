"""API 调用记录表 ORM 模型"""
from typing import Optional

from sqlalchemy import String, Integer, Float, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ApiCall(Base, TimestampMixin):
    __tablename__ = "api_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost_cny: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    keyword: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    __table_args__ = (
        Index("ix_api_calls_brand", "brand"),
        Index("ix_api_calls_operation", "operation_type"),
        Index("ix_api_calls_provider", "provider"),
    )
