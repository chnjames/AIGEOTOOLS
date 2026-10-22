"""知识库相关 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class KnowledgeDocResponse(BaseModel):
    id: int
    filename: str
    file_type: Optional[str] = None
    brand: Optional[str] = None
    chunk_count: int = 0
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    brand: str = ""
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeChunkResponse(BaseModel):
    doc_id: int
    filename: str
    content: str
    score: float = 0.0
