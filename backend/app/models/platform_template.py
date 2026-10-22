"""平台模板配置表 ORM 模型 - 支持自定义平台内容模板"""
from typing import Optional

from sqlalchemy import String, Integer, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PlatformTemplate(Base, TimestampMixin):
    __tablename__ = "platform_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)  # 平台名称
    style_instruction: Mapped[str] = mapped_column(Text, nullable=False)  # 风格指令
    filename_suffix: Mapped[str] = mapped_column(String(50), default=".md", nullable=False)  # 文件后缀
    group_name: Mapped[str] = mapped_column(String(50), default="其他", nullable=False)  # 分组
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 是否内置模板
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # 是否启用
    word_count_default: Mapped[int] = mapped_column(Integer, default=1500, nullable=False)  # 默认字数
    extra_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 额外JSON配置

    __table_args__ = (
        Index("ix_platform_tpl_group", "group_name"),
        Index("ix_platform_tpl_active", "is_active"),
    )
