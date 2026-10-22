"""应用配置表 ORM 模型（替代 config.json）"""
from datetime import datetime

from sqlalchemy import Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AppConfig(Base):
    __tablename__ = "app_config"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
