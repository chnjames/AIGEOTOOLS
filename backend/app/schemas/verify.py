"""验证相关 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class VerifyResultResponse(BaseModel):
    id: int
    query: Optional[str] = None
    brand: Optional[str] = None
    verify_model: Optional[str] = None
    mention_count: int = 0
    mention_position: Optional[str] = None
    content_snippet: Optional[str] = None
    is_mentioned: bool = False
    sentiment: Optional[str] = None
    positive_mentions: int = 0
    negative_mentions: int = 0
    verification_mode: Optional[str] = None
    diagnosis: Optional[str] = None
    recommended_brands: Optional[str] = None
    full_response: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class VerifyRequest(BaseModel):
    query: str = Field(..., description="要验证的问题/关键词")
    brand: str = ""
    providers: list[str] = Field(default_factory=list, description="验证模型列表(使用全局配置则为空)")
    temperature: float = 0.7
    mode: str = Field(default="natural", description="验证模式：natural（自然模式，问题中不提品牌）/ prompted（提示模式，明确关注品牌）")
    # 如果不传 api_key，使用全局配置中保存的 key
    verify_keys: Optional[dict[str, str]] = None


class CompetitorVerifyRequest(BaseModel):
    query: str
    brand: str = ""
    competitors: list[str] = Field(default_factory=list)
    providers: list[str] = Field(default_factory=list)
    temperature: float = 0.7
    verify_keys: Optional[dict[str, str]] = None
