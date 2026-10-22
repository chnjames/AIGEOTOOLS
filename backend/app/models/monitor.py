"""持续监测数据模型"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, Index

from app.models.base import Base, TimestampMixin


class MonitorTask(Base, TimestampMixin):
    """巡检任务配置"""
    __tablename__ = "monitor_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="任务名称")
    queries = Column(Text, nullable=False, comment="查询词列表（JSON数组，每行一个或JSON）")
    platforms = Column(String(500), nullable=False, default="DeepSeek", comment="验证平台（逗号分隔）")
    schedule_type = Column(String(20), nullable=False, default="daily", comment="调度类型: daily/weekly/manual")
    schedule_time = Column(String(10), nullable=False, default="09:00", comment="执行时间 HH:MM")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")
    brand = Column(String(200), nullable=False, default="", comment="品牌")
    competitors = Column(Text, nullable=False, default="", comment="竞品（逗号分隔）")
    alert_threshold = Column(Float, nullable=False, default=0.5, comment="预警阈值（提及率低于此值告警）")
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)


class MonitorResult(Base, TimestampMixin):
    """巡检结果明细"""
    __tablename__ = "monitor_results"
    __table_args__ = (
        Index("ix_monitor_results_is_alert", "is_alert"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("monitor_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    query = Column(String(500), nullable=False, comment="查询词")
    platform = Column(String(100), nullable=False, comment="AI平台")
    is_mentioned = Column(Boolean, nullable=False, default=False, comment="是否提及品牌")
    mention_position = Column(String(50), nullable=False, default="", comment="提及位置")
    mention_count = Column(Integer, nullable=False, default=0, comment="提及次数")
    sentiment = Column(String(20), nullable=False, default="neutral", comment="情感: positive/neutral/negative")
    content_snippet = Column(Text, nullable=False, default="", comment="内容摘要")
    competitor_mentions = Column(Text, nullable=False, default="", comment="竞品提及情况(JSON)")
    is_alert = Column(Boolean, nullable=False, default=False, comment="是否触发告警")
    run_batch = Column(String(50), nullable=False, index=True, comment="执行批次ID")


class Alert(Base, TimestampMixin):
    """告警记录"""
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_task", "task_id"),
        Index("ix_alerts_result", "result_id"),
        Index("ix_alerts_is_read", "is_read"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(50), nullable=False, comment="告警类型: negative_mention/low_mention_rate/competitor_dominance")
    level = Column(String(20), nullable=False, default="warning", comment="级别: warning/critical")
    title = Column(String(300), nullable=False)
    message = Column(Text, nullable=False, default="")
    task_id = Column(Integer, ForeignKey("monitor_tasks.id", ondelete="SET NULL"), nullable=True)
    result_id = Column(Integer, ForeignKey("monitor_results.id", ondelete="SET NULL"), nullable=True)
    is_read = Column(Boolean, nullable=False, default=False, comment="是否已读")
    metadata_json = Column(Text, nullable=False, default="{}", comment="附加数据")
