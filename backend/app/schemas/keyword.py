"""关键词相关 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class KeywordResponse(BaseModel):
    id: int
    keyword: str
    brand: Optional[str] = None
    is_favorite: bool = False
    tags: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class KeywordCreate(BaseModel):
    keywords: list[str] = Field(..., min_length=1)
    brand: str = ""


class KeywordGenerateRequest(BaseModel):
    brand: str = ""
    advantages: str = ""
    core_keyword: str = Field(..., description="核心词/行业词")
    wordbanks: Optional[dict[str, list[str]]] = Field(default=None, description="自定义词库")
    max_results: int = Field(default=50, ge=1, le=500)
    polish: bool = Field(default=True, description="是否用LLM润色")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class KeywordMineRequest(BaseModel):
    keyword: str
    brand: str = ""
    temperature: float = 0.7
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class KeywordExpandRequest(BaseModel):
    keywords: list[str]
    brand: str = ""
    temperature: float = 0.7
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class KeywordClusterRequest(BaseModel):
    keywords: list[str]
    brand: str = ""
    temperature: float = 0.7
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class TopicClusterResponse(BaseModel):
    clusters: list[dict]
    summary: str = ""


class TagUpdateRequest(BaseModel):
    """更新关键词标签请求体"""
    tags: list[str] = Field(default_factory=list, description="标签列表")


class ImportRequest(BaseModel):
    """导入关键词请求体"""
    keyword_ids: list[int] = Field(..., min_length=1, description="要导入的关键词 ID 列表")
    target_brand: str = Field(..., description="目标品牌名称")
