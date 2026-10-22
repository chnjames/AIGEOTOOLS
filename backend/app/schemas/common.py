"""通用 Pydantic Schema"""
from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None


class PageResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class SSEMessage(BaseModel):
    """SSE 事件消息"""
    event: str  # start | progress | chunk | complete | error
    data: dict[str, Any]


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
