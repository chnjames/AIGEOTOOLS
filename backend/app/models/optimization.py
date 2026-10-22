"""优化记录表 ORM 模型"""
from typing import Optional

from sqlalchemy import String, Integer, Text, Index, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Optimization(Base, TimestampMixin):
    __tablename__ = "optimizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("articles.id", ondelete="SET NULL"), nullable=True,
    )
    original_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    optimized_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    keyword: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    optimization_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    score_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_optimizations_brand", "brand"),
        Index("ix_optimizations_type", "optimization_type"),
        Index("ix_optimizations_article", "article_id"),
    )
