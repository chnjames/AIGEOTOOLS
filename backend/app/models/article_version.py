"""文章版本快照表 ORM 模型"""
from typing import Optional

from sqlalchemy import String, Integer, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ArticleVersion(Base, TimestampMixin):
    __tablename__ = "article_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 版本来源: "generated" / "edited" / "optimized_eeat" / "optimized_fact" / "optimized_schema" / "optimized_dds" / "rollback"
    source: Mapped[str] = mapped_column(String(50), default="generated", nullable=False, server_default="generated")
    # 操作描述
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # DDS 评分快照（JSON）
    dds_score: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("article_id", "version_number", name="uq_article_version"),
        Index("ix_av_article_id", "article_id"),
    )
