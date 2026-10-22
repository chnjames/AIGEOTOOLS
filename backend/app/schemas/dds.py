"""DDS（语义深度/数据支持/权威来源）评分相关 Pydantic Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 子项结构
# ---------------------------------------------------------------------------

class DDSSubScores(BaseModel):
    """单维度的四个子项分数（各 0-25）"""
    logic: int = Field(0, ge=0, le=25, description="逻辑完整性（语义深度维度）")
    reasoning: int = Field(0, ge=0, le=25, description="推理链条（语义深度维度）")
    insight: int = Field(0, ge=0, le=25, description="洞察深度（语义深度维度）")
    richness: int = Field(0, ge=0, le=25, description="概念丰富度（语义深度维度）")
    # 数据支持维度子项
    data_points: int = Field(0, ge=0, le=25, description="数据点密度（数据支持维度）")
    citations: int = Field(0, ge=0, le=25, description="来源引用（数据支持维度）")
    examples: int = Field(0, ge=0, le=25, description="案例例证（数据支持维度）")
    statistics: int = Field(0, ge=0, le=25, description="统计权威性（数据支持维度）")
    # 权威来源维度子项
    credentials: int = Field(0, ge=0, le=25, description="资质信号（权威来源维度）")
    expert_quotes: int = Field(0, ge=0, le=25, description="专家引用（权威来源维度）")
    references: int = Field(0, ge=0, le=25, description="权威参考文献（权威来源维度）")
    venue_quality: int = Field(0, ge=0, le=25, description="发布渠道质量（权威来源维度）")


class DDSScoreDimension(BaseModel):
    """单个维度的评分结果"""
    score: float = Field(0, ge=0, le=100, description="该维度总分 0-100")
    sub_scores: dict[str, int] = Field(default_factory=dict, description="四个子项分数，各 0-25")
    details: str = Field("", description="该维度评估详情文字")


# ---------------------------------------------------------------------------
# 评分响应
# ---------------------------------------------------------------------------

class DDSScoreResponse(BaseModel):
    """DDS 三维评分完整响应"""
    id: Optional[int] = Field(None, description="数据库记录 ID（保存后返回）")
    article_id: Optional[int] = Field(None, description="关联文章 ID")
    brand: str = Field("", description="评估品牌")
    semantic_depth: DDSScoreDimension = Field(default_factory=DDSScoreDimension, description="语义深度评分")
    data_support: DDSScoreDimension = Field(default_factory=DDSScoreDimension, description="数据支持评分")
    authoritative_source: DDSScoreDimension = Field(default_factory=DDSScoreDimension, description="权威来源评分")
    total_score: float = Field(0, ge=0, le=100, description="加权综合分（深度0.35 + 数据0.35 + 来源0.30）")
    improvements: list[str] = Field(default_factory=list, description="改进建议列表")
    strengths: list[str] = Field(default_factory=list, description="内容优势列表")
    created_at: Optional[datetime] = Field(None, description="评分时间")

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 评分请求
# ---------------------------------------------------------------------------

class DDSScoreRequest(BaseModel):
    """DDS 评分请求"""
    content: str = Field(..., min_length=10, description="待评估内容")
    brand: str = Field("", description="目标品牌")
    article_id: Optional[int] = Field(None, description="关联文章 ID")
    temperature: float = Field(0.7, ge=0, le=2, description="LLM 温度参数")
    provider: Optional[str] = Field(None, description="LLM 提供商")
    api_key: Optional[str] = Field(None, description="API Key")
    model: Optional[str] = Field(None, description="模型名称")


# ---------------------------------------------------------------------------
# 优化操作记录（ROI 归因）
# ---------------------------------------------------------------------------

class OptimizationActionCreate(BaseModel):
    """创建优化操作记录请求"""
    action_type: str = Field(..., description="操作类型: eeat/fact_density/schema/keyword/article/other")
    description: str = Field("", max_length=500, description="操作描述")
    brand: str = Field("", description="品牌")
    article_id: Optional[int] = Field(None, description="关联文章 ID")
    keyword: str = Field("", description="目标关键词")
    platform: str = Field("", description="平台")
    score_before: Optional[float] = Field(None, description="操作前评分")
    score_after: Optional[float] = Field(None, description="操作后评分")
    mention_rate_at_action: Optional[float] = Field(None, description="操作时提及率")
    metadata: dict = Field(default_factory=dict, description="附加元数据")


class OptimizationActionResponse(BaseModel):
    """优化操作记录响应"""
    id: int
    action_type: str
    description: str
    brand: str
    article_id: Optional[int] = None
    keyword: str
    platform: str
    score_before: Optional[float] = None
    score_after: Optional[float] = None
    mention_rate_at_action: Optional[float] = None
    metadata_json: str = "{}"
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
