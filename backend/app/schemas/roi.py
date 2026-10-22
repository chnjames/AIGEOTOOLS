"""ROI 和报表相关 Schema"""
from typing import Optional, Any
from pydantic import BaseModel, Field


class KPIResponse(BaseModel):
    total_keywords: int = 0
    total_articles: int = 0
    total_optimizations: int = 0
    total_verifications: int = 0
    total_cost_cny: float = 0.0
    mention_rate: float = 0.0


class CostReportResponse(BaseModel):
    total_cost_usd: float = 0.0
    total_cost_cny: float = 0.0
    total_tokens: int = 0
    total_calls: int = 0
    cost_by_operation: dict = Field(default_factory=dict)
    cost_by_provider: dict = Field(default_factory=dict)
    cost_by_keyword: dict = Field(default_factory=dict)
    cost_by_platform: dict = Field(default_factory=dict)
    daily_costs: list[dict] = Field(default_factory=list)


class MentionReportResponse(BaseModel):
    total_verifications: int = 0
    total_mentioned: int = 0
    mention_rate: float = 0.0
    mention_rate_by_model: dict = Field(default_factory=dict)
    mention_trend: list[dict] = Field(default_factory=list)
    top_mentioned_queries: list[dict] = Field(default_factory=list)


class ROIReportResponse(BaseModel):
    total_cost_cny: float = 0.0
    total_mentions: int = 0
    estimated_value_cny: float = 0.0
    roi_ratio: float = 0.0
    keyword_roi: dict = Field(default_factory=dict)
    suggestions: list[dict] = Field(default_factory=list)
    future_cost_estimate: dict = Field(default_factory=dict)


class ScoreRequest(BaseModel):
    content: str
    brand: str = ""
    advantages: str = ""
    platform: str = ""
    temperature: float = 0.7
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class MetricsRequest(BaseModel):
    content: str
    brand: str = ""


class MetricsResponse(BaseModel):
    word_count: int
    paragraph_count: int
    heading_count: int
    list_count: int
    brand_count: int
    keyword_density: float
    readability_score: float = 0.0
    has_faq: bool = False
    has_citations: bool = False
    avg_paragraph_length: float = 0.0


class QuickScoreResponse(BaseModel):
    has_title: bool = False
    has_list: bool = False
    has_faq: bool = False
    brand_count: int = 0
    word_count: int = 0
    quick_score: int = 0


class ResourceResponse(BaseModel):
    title: str
    url: str
    category: str
    description: str = ""


class TechniqueResponse(BaseModel):
    name: str
    category: str
    description: str
    example: str = ""


class ConfigOptimizeRequest(BaseModel):
    current_config: dict
    brand: str = ""
    advantages: str = ""
    competitors: list[str] = Field(default_factory=list)
    temperature: float = 0.7
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class NegativeMentionResponse(BaseModel):
    id: int
    query: Optional[str] = None
    brand: Optional[str] = None
    verify_model: Optional[str] = None
    snippet: Optional[str] = None
    is_negative: bool = True
    created_at: Optional[str] = None
