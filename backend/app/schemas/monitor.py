"""持续监测相关 Schema"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


class MonitorTaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="任务名称")
    queries: str = Field(..., description="查询词列表（JSON数组或换行分隔）")
    platforms: str = Field(default="deepseek", description="验证平台（逗号分隔）")
    schedule_type: str = Field(default="daily", description="调度类型: daily/weekly/manual")
    schedule_time: str = Field(default="09:00", description="执行时间 HH:MM")
    brand: str = Field(default="", description="品牌")
    competitors: str = Field(default="", description="竞品（逗号分隔）")
    alert_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="预警阈值（提及率低于此值告警）")
    is_active: bool = Field(default=True, description="是否启用")


class MonitorTaskUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    queries: Optional[str] = None
    platforms: Optional[str] = None
    schedule_type: Optional[str] = None
    schedule_time: Optional[str] = None
    brand: Optional[str] = None
    competitors: Optional[str] = None
    alert_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    is_active: Optional[bool] = None


class MonitorTaskResponse(BaseModel):
    id: int
    name: str
    queries: str
    platforms: str
    schedule_type: str
    schedule_time: str
    is_active: bool
    brand: str
    competitors: str
    alert_threshold: float
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MonitorResultResponse(BaseModel):
    id: int
    task_id: int
    query: str
    platform: str
    is_mentioned: bool = False
    mention_position: str = ""
    mention_count: int = 0
    sentiment: str = "neutral"
    content_snippet: str = ""
    competitor_mentions: str = ""
    is_alert: bool = False
    run_batch: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AlertResponse(BaseModel):
    id: int
    alert_type: str
    level: str
    title: str
    message: str
    task_id: Optional[int] = None
    result_id: Optional[int] = None
    is_read: bool = False
    metadata_json: str = "{}"
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TrendPoint(BaseModel):
    """趋势数据点"""
    date: str
    platform: str
    mention_rate: float = 0.0
    total_checks: int = 0
    mentioned_count: int = 0
