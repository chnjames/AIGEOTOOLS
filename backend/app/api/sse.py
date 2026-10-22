"""SSE 响应工具函数"""
import asyncio
import json
from typing import Any, AsyncGenerator

from fastapi.responses import StreamingResponse

from app.core.exceptions import GEOAppException
from app.core.logging import get_logger

logger = get_logger(__name__)


def sse_format(event: str, data: Any) -> str:
    """格式化为 SSE 协议字符串"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _safe_error_message(e: Exception) -> str:
    """从异常中提取安全的用户可见错误信息，不泄露内部路径/SQL等"""
    if isinstance(e, GEOAppException):
        return e.message
    return "生成失败，请稍后重试"


async def sse_stream_handler(generator: AsyncGenerator[dict | str, None]) -> AsyncGenerator[str, None]:
    """包装 async generator 为 SSE 流（含错误处理和 generator 清理）"""
    try:
        yield sse_format("start", {"message": "连接已建立"})
        async for item in generator:
            if isinstance(item, str):
                yield sse_format("chunk", {"content": item})
            elif isinstance(item, dict):
                event = item.get("event", "message")
                data = item.get("data", item)
                yield sse_format(event, data)
        yield sse_format("done", {"message": "完成"})
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled by client")
        raise
    except Exception as e:
        logger.error("SSE stream error: %s", e, exc_info=True)
        yield sse_format("error", {"message": _safe_error_message(e)})
        yield sse_format("done", {"message": "异常终止"})
    finally:
        # 确保底层 generator 被正确关闭，释放资源
        try:
            await generator.aclose()
        except Exception:
            pass


def create_sse_response(generator: AsyncGenerator[dict | str, None]) -> StreamingResponse:
    """创建 SSE StreamingResponse"""
    return StreamingResponse(
        sse_stream_handler(generator),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def llm_stream_to_sse(
    chunk_generator: AsyncGenerator[str, None],
    meta: dict[str, Any] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """将 LLM chunk stream 转为 SSE event stream，错误时传出部分响应"""
    if meta:
        yield {"event": "start", "data": meta}
    full: list[str] = []
    try:
        async for chunk in chunk_generator:
            full.append(chunk)
            yield {"event": "chunk", "data": {"content": chunk}}
        yield {"event": "complete", "data": {"full_content": "".join(full)}}
    except asyncio.CancelledError:
        # 客户端断开，将已收到的部分内容传出后重新抛出
        partial = "".join(full)
        if partial:
            yield {"event": "complete", "data": {"full_content": partial, "partial": True}}
        raise
    except Exception:
        # 将已收到的内容一并传出（部分响应），由 sse_stream_handler 发送 error 事件
        partial = "".join(full)
        if partial:
            yield {"event": "complete", "data": {"full_content": partial, "partial": True}}
        raise
