"""营销报告数据模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Index

from app.models.base import Base, TimestampMixin


class MarketingReport(Base, TimestampMixin):
    """自动化营销报告"""
    __tablename__ = "marketing_reports"
    __table_args__ = (
        Index("ix_reports_created_at", "created_at"),
        Index("ix_reports_date_range", "date_from", "date_to"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    report_type = Column(String(50), nullable=False, default="weekly", comment="类型: daily/weekly/monthly/custom")
    brand = Column(String(200), nullable=False, default="", index=True)
    date_from = Column(DateTime(timezone=True), nullable=True)
    date_to = Column(DateTime(timezone=True), nullable=True)
    # 报告内容
    summary = Column(Text, nullable=False, default="", comment="摘要")
    kpi_data = Column(Text, nullable=False, default="{}", comment="KPI数据JSON")
    mention_trend = Column(Text, nullable=False, default="[]", comment="提及趋势JSON")
    cost_data = Column(Text, nullable=False, default="{}", comment="费用数据JSON")
    optimization_effect = Column(Text, nullable=False, default="[]", comment="优化效果JSON")
    competitor_analysis = Column(Text, nullable=False, default="{}", comment="竞品分析JSON")
    recommendations = Column(Text, nullable=False, default="[]", comment="建议JSON")
    # 完整Markdown报告
    markdown_content = Column(Text, nullable=False, default="")
    # 分享 — nullable 允许多条未分享记录而不违反 UNIQUE
    share_token = Column(String(100), nullable=True, unique=True, index=True)
    is_published = Column(Boolean, nullable=False, default=False)
