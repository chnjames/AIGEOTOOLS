"""工作流相关 ORM 模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, Text, Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    steps: Mapped[str] = mapped_column(Text, nullable=False)  # JSON 字符串
    schedule: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON 字符串
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="1")
    brand: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    executions: Mapped[list["WorkflowExecution"]] = relationship(
        "WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan"
    )


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")  # pending/running/completed/failed
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON 字符串
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, server_default="0")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON 数组，执行日志
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="executions")

    __table_args__ = (
        Index("ix_we_workflow_id", "workflow_id"),
        Index("ix_we_status", "status"),
        Index("ix_we_created", "created_at"),
    )


class WorkflowTemplate(Base, TimestampMixin):
    __tablename__ = "workflow_templates"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps: Mapped[str] = mapped_column(Text, nullable=False)  # JSON 字符串
