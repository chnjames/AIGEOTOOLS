"""文章表 ORM 模型"""
from typing import Optional

from sqlalchemy import String, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Article(Base, TimestampMixin):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    filename: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    publish_status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    publish_urls: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 多模态描述（配图、视频脚本等，JSON 字符串）
    multimodal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_articles_brand", "brand"),
        Index("ix_articles_platform", "platform"),
    )
