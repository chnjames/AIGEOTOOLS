"""工作流相关 Schema"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class WorkflowStep(BaseModel):
    step_type: str  # generate_keywords / generate_content / optimize / verify / etc.
    name: str
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    steps: list[WorkflowStep]
    schedule: Optional[str] = None
    conditions: Optional[dict[str, Any]] = None
    brand: str = ""


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = None
    steps: Optional[list[WorkflowStep]] = None
    schedule: Optional[str] = None
    conditions: Optional[dict[str, Any]] = None
    enabled: Optional[bool] = None


class WorkflowResponse(BaseModel):
    id: str
    name: str
    steps: str  # JSON
    schedule: Optional[str] = None
    conditions: Optional[str] = None
    enabled: bool = True
    brand: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WorkflowExecutionResponse(BaseModel):
    id: int
    workflow_id: str
    status: str
    result: Optional[str] = None
    progress: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    logs: Optional[str] = None

    model_config = {"from_attributes": True}


class WorkflowTemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    steps: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WorkflowExecuteRequest(BaseModel):
    brand: str = ""
    advantages: str = ""
    keywords: Optional[list[str]] = None
    platforms: Optional[list[str]] = None
    temperature: float = 0.7
