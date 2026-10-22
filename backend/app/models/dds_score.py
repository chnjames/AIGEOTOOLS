"""DDS 三维评分模型"""
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, Index

from app.models.base import Base, TimestampMixin


class DDSScore(Base, TimestampMixin):
    """DDS 评分记录（语义深度/数据支持/权威来源）"""
    __tablename__ = "dds_scores"
    __table_args__ = (
        Index("ix_dds_scores_brand", "brand"),
        Index("ix_dds_scores_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=True, index=True)
    brand = Column(String(200), nullable=False, default="")
    # 三个核心维度（各0-100分）
    semantic_depth = Column(Float, nullable=False, default=0, comment="语义深度分")
    data_support = Column(Float, nullable=False, default=0, comment="数据支持分")
    authoritative_source = Column(Float, nullable=False, default=0, comment="权威来源分")
    total_score = Column(Float, nullable=False, default=0, comment="综合分（加权平均）")
    # 各维度子项明细 JSON
    depth_details = Column(Text, nullable=False, default="{}", comment="语义深度子项JSON")
    data_details = Column(Text, nullable=False, default="{}", comment="数据支持子项JSON")
    source_details = Column(Text, nullable=False, default="{}", comment="权威来源子项JSON")
    # 改进建议
    improvements = Column(Text, nullable=False, default="[]", comment="改进建议JSON数组")
    strengths = Column(Text, nullable=False, default="[]", comment="优势JSON数组")


class OptimizationAction(Base, TimestampMixin):
    """优化操作记录（用于ROI归因）"""
    __tablename__ = "optimization_actions"
    __table_args__ = (
        Index("ix_opt_actions_article", "article_id"),
        Index("ix_opt_actions_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_type = Column(String(100), nullable=False, comment="操作类型: eeat/fact_density/schema/keyword/article/other")
    description = Column(String(500), nullable=False, default="")
    brand = Column(String(200), nullable=False, default="", index=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="SET NULL"), nullable=True)
    keyword = Column(String(500), nullable=False, default="")
    platform = Column(String(100), nullable=False, default="")
    # 记录操作前后的评分变化
    score_before = Column(Float, nullable=True)
    score_after = Column(Float, nullable=True)
    # 记录操作时的提及率（后续趋势对比）
    mention_rate_at_action = Column(Float, nullable=True)
    metadata_json = Column(Text, nullable=False, default="{}")
