"""内容优化相关 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OptimizationResponse(BaseModel):
    id: int
    article_id: Optional[int] = None
    original_content: Optional[str] = None
    optimized_content: Optional[str] = None
    changes: Optional[str] = None
    platform: Optional[str] = None
    brand: Optional[str] = None
    keyword: Optional[str] = None
    optimization_type: Optional[str] = None
    applied: bool = False
    score_result: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OptimizeRequest(BaseModel):
    content: str = Field(..., min_length=10)
    brand: str = ""
    keyword: str = ""
    advantages: str = ""
    platform: str = ""
    temperature: float = 0.7
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    article_id: Optional[int] = None
    use_knowledge: bool = False
    knowledge_context: Optional[str] = None


class OriginalContentResponse(BaseModel):
    article_id: int
    original_content: Optional[str] = None


class SchemaGenerateRequest(BaseModel):
    content: str
    schema_type: str = "Article"  # Article / Product / FAQ / HowTo
    brand: str = ""
    temperature: float = 0.7
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class SchemaResponse(BaseModel):
    json_ld: str
    schema_type: str


class TechConfigRequest(BaseModel):
    brand: str = ""
    website_url: str = ""
    keywords: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)


class TechConfigResponse(BaseModel):
    robots_txt: str
    sitemap_xml: str
    meta_tags: str
    structured_data: str


class UniquenessRequest(BaseModel):
    content: str
    reference_contents: list[str] = Field(default_factory=list)


class UniquenessResponse(BaseModel):
    uniqueness_score: float
    duplicate_segments: list[str]
    suggestions: list[str]
