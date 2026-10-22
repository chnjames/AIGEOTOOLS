"""关键词表 ORM 模型"""
from typing import Optional

from sqlalchemy import String, Integer, Text, Boolean, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Keyword(Base, TimestampMixin):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 逗号分隔标签

    __table_args__ = (
        UniqueConstraint("keyword", "brand", name="uq_keyword_brand"),
        Index("ix_keywords_brand", "brand"),
        Index("ix_keywords_favorite", "is_favorite"),
    )
