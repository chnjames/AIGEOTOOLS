"""操作审计日志表 ORM 模型"""
from typing import Optional

from sqlalchemy import String, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # delete/clear/config_change/import/export/cleanup
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # keyword/article/verify_result/workflow/knowledge_doc/config/data
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 操作对象ID（可为空表示批量）
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 操作详情JSON
    result: Mapped[str] = mapped_column(String(20), default="success", nullable=False)  # success/failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 失败原因
    operator: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 操作者（系统/API Key标识）

    __table_args__ = (
        Index("ix_audit_action", "action"),
        Index("ix_audit_resource", "resource_type"),
        Index("ix_audit_created", "created_at"),
    )
