"""审计日志服务

提供简单的审计日志记录辅助函数，用于在关键操作（配置变更、账号绑定/删除、
文章删除、知识库删除等）时记录审计轨迹。

审计日志记录包含：action（操作类型）、resource_type（资源类型）、
resource_id（资源ID）、operator（操作者）、details（操作详情 JSON）。
"""
from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.audit_log import AuditLog

logger = get_logger(__name__)


async def log_audit(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    operator: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    result: str = "success",
    error_message: Optional[str] = None,
) -> None:
    """记录审计日志（简单 async helper）。

    审计日志写入失败不会影响主业务流程（仅记录错误日志）。

    Args:
        db: 异步数据库会话。审计日志会添加到该会话中，由调用方负责提交
            （通常通过 ``get_db`` 依赖在请求结束时自动 commit）。
        action: 操作类型，如 "config_update"、"account_create"、"account_delete"、
            "article_delete"、"knowledge_delete" 等。
        resource_type: 资源类型，如 "config"、"platform_account"、"article"、
            "knowledge_doc" 等。
        resource_id: 操作对象 ID（字符串形式），批量操作时可为 None。
        operator: 操作者标识，从请求头获取或默认 "system"。
        details: 操作详情字典，会被序列化为 JSON 字符串存储。
        result: 操作结果，"success" 或 "failed"。
        error_message: 失败原因（result 为 failed 时填写）。
    """
    try:
        detail_str = json.dumps(details, ensure_ascii=False) if details else None
        log_entry = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            detail=detail_str,
            result=result,
            error_message=error_message,
            operator=operator or "system",
        )
        db.add(log_entry)
        await db.flush()
    except Exception as e:
        # 审计日志写入失败不影响主业务流程
        logger.error("写入审计日志失败: %s", e)


def get_operator_from_request(request) -> str:
    """从请求头获取操作者标识。

    优先级：
    1. X-Operator 请求头（如果存在）
    2. X-API-Key 请求头（如果存在，作为操作者标识）
    3. 默认 "system"

    Args:
        request: FastAPI Request 对象。

    Returns:
        操作者标识字符串。
    """
    operator = request.headers.get("X-Operator")
    if operator:
        return operator
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key[:8]}..."  # 仅记录前8位，避免暴露完整密钥
    return "system"
