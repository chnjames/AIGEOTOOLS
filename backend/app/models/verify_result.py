"""验证结果表 ORM 模型"""
from typing import Optional

from sqlalchemy import String, Integer, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class VerifyResult(Base, TimestampMixin):
    __tablename__ = "verify_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    verify_model: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    mention_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mention_position: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    content_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 完整LLM响应
    is_mentioned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    positive_mentions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    negative_mentions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verification_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="prompted")
    diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_brands: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_verify_brand", "brand"),
        Index("ix_verify_model", "verify_model"),
    )
