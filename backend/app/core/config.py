"""应用配置管理 - Pydantic Settings"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，从环境变量和 .env 文件读取"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用配置
    APP_NAME: str = "GEO 智能内容优化平台"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    API_KEY: str = ""  # 全局 API Key 认证（为空则不启用）

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://localhost:3000"

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./geo_data.db"

    # LLM 缓存
    LLM_CACHE_ENABLED: bool = True
    LLM_CACHE_TTL_SECONDS: int = 3600
    LLM_CACHE_MAX_SIZE: int = 1000

    # 文件上传
    UPLOAD_DIR: str = "./uploads"
    KNOWLEDGE_DIR: str = "./knowledge_base"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_UPLOAD_EXTENSIONS: str = ".txt,.md,.pdf,.docx,.doc"

    # 汇率
    USD_TO_CNY_RATE: float = 7.2

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [e.strip().lower() for e in self.ALLOWED_UPLOAD_EXTENSIONS.split(",") if e.strip()]


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
