"""实时进度通知管理器 - 基于 SSE 的长连接进度推送

选型说明：使用 SSE（Server-Sent Events）而非 WebSocket，理由：
1. 进度通知是单向的（服务端→客户端），不需要双向通信
2. SSE 基于 HTTP，原生支持自动重连，部署更简单（无需额外 WebSocket 代理配置）
3. Nginx 反向代理对 SSE 支持良好，只需配置适当的超时
4. 前端使用 EventSource API 即可，无需额外库
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from typing import Any, AsyncGenerator, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class ProgressManager:
    """管理多个正在进行的任务进度，支持 SSE 订阅"""

    def __init__(self):
        self._tasks: dict[str, dict[str, Any]] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def create_task(self, task_id: Optional[str] = None) -> str:
        tid = task_id or str(uuid.uuid4())
        self._tasks[tid] = {
            "status": "pending",
            "progress": 0.0,
            "current_step": "",
            "logs": [],
            "result": None,
            "error": None,
            "created_at": time.time(),
        }
        self._subscribers[tid] = []
        return tid

    async def update_progress(
        self,
        task_id: str,
        progress: float,
        message: str = "",
        step: str = "",
    ) -> None:
        if task_id not in self._tasks:
            return
        task = self._tasks[task_id]
        task["progress"] = min(progress, 100.0)
        if step:
            task["current_step"] = step
        if message:
            entry = {"time": time.time(), "message": message, "progress": progress}
            task["logs"].append(entry)
        await self._broadcast(task_id, {
            "event": "progress",
            "data": {
                "progress": task["progress"],
                "step": task["current_step"],
                "message": message,
            }
        })

    async def add_log(self, task_id: str, message: str) -> None:
        if task_id not in self._tasks:
            return
        self._tasks[task_id]["logs"].append({"time": time.time(), "message": message})
        await self._broadcast(task_id, {
            "event": "log",
            "data": {"message": message}
        })

    async def complete_task(self, task_id: str, result: Any = None) -> None:
        if task_id not in self._tasks:
            return
        task = self._tasks[task_id]
        task["status"] = "completed"
        task["progress"] = 100.0
        task["result"] = result
        await self._broadcast(task_id, {
            "event": "complete",
            "data": {"progress": 100.0, "result": result}
        })
        self._cleanup(task_id)

    async def fail_task(self, task_id: str, error: str) -> None:
        if task_id not in self._tasks:
            return
        task = self._tasks[task_id]
        task["status"] = "failed"
        task["error"] = error
        await self._broadcast(task_id, {
            "event": "error",
            "data": {"error": error}
        })
        self._cleanup(task_id)

    def get_task(self, task_id: str) -> Optional[dict]:
        return self._tasks.get(task_id)

    async def subscribe(self, task_id: str) -> AsyncGenerator[str, None]:
        """SSE 订阅：yield SSE 格式的字符串"""
        queue: asyncio.Queue = asyncio.Queue()
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        self._subscribers[task_id].append(queue)

        # 先发送当前状态
        task = self._tasks.get(task_id, {})
        yield _format_sse("start", {
            "task_id": task_id,
            "status": task.get("status", "unknown"),
            "progress": task.get("progress", 0),
        })

        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield _format_sse(msg["event"], msg["data"])
                    if msg["event"] in ("complete", "error"):
                        break
                except asyncio.TimeoutError:
                    # 发送心跳保活
                    yield ": keepalive\n\n"
        finally:
            if task_id in self._subscribers:
                self._subscribers[task_id] = [
                    s for s in self._subscribers[task_id] if s is not queue
                ]

    async def _broadcast(self, task_id: str, message: dict) -> None:
        subs = self._subscribers.get(task_id, [])
        for q in subs:
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                pass

    def _cleanup(self, task_id: str, delay: float = 60.0) -> None:
        """延迟清理已完成任务"""
        def _delayed_cleanup():
            time.sleep(delay)
            self._tasks.pop(task_id, None)
            self._subscribers.pop(task_id, None)
        t = threading.Thread(target=_delayed_cleanup, daemon=True)
        t.start()


def _format_sse(event: str, data: Any) -> str:
    """格式化为 SSE 协议字符串"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


# 全局单例
progress_manager = ProgressManager()
