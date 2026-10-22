"""知识库文档表 ORM 模型"""
from typing import Optional

from sqlalchemy import String, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class KnowledgeDoc(Base, TimestampMixin):
    __tablename__ = "knowledge_docs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_kd_brand", "brand"),
    )
