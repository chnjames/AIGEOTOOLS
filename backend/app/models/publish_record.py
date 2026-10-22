"""发布记录表 ORM 模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PublishRecord(Base, TimestampMixin):
    __tablename__ = "publish_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("articles.id", ondelete="SET NULL"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    publish_method: Mapped[str] = mapped_column(String(50), nullable=False)
    publish_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    publish_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    publish_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_pr_article", "article_id"),
        Index("ix_pr_platform", "platform"),
        Index("ix_pr_status", "publish_status"),
    )
