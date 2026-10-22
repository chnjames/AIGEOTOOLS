"""LLM 错误分类工具 - 将各种提供商的错误统一分类为标准错误类型"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

from app.core.exceptions import (
    LLMError, LLMAuthError, LLMBalanceError, LLMTimeoutError,
    LLMRateLimitError, LLMModelNotFoundError, LLMNetworkError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# 速率限制状态：记录每个提供商最后调用时间
_rate_limit_state: dict[str, float] = {}
_rate_limit_lock = asyncio.Lock()
DEFAULT_INTERVAL = 1.0  # 默认调用间隔 1 秒


def classify_llm_error(error: Exception, provider: str = "", model: str = "", timeout: int = 60) -> LLMError:
    """
    将任意异常分类为标准 LLM 错误类型。
    检查 HTTP 状态码、错误消息关键词来确定错误类型。
    """
    err_str = str(error).lower()
    err_type = type(error).__name__

    # 提取原始响应文本（前 200 字符）
    raw = str(error)[:500]

    # 1. 超时错误
    if isinstance(error, asyncio.TimeoutError) or "timeout" in err_str or "timed out" in err_str:
        return LLMTimeoutError(provider=provider, timeout=timeout, raw=raw)

    # 2. 认证错误 (401/403)
    if "401" in err_str or "403" in err_str or "unauthorized" in err_str or "forbidden" in err_str or "invalid api" in err_str or "authentication" in err_str or ("api key" in err_str and "invalid" in err_str):
        return LLMAuthError(provider=provider, raw=raw)

    # 3. 速率限制 (429)
    if "429" in err_str or "rate limit" in err_str or "too many requests" in err_str or "quota exceeded" in err_str or "requests per minute" in err_str:
        return LLMRateLimitError(provider=provider, raw=raw)

    # 4. 余额不足
    if ("insufficient" in err_str and ("balance" in err_str or "quota" in err_str or "credit" in err_str or "fund" in err_str)) or ("billing" in err_str and ("hard" in err_str or "limit" in err_str)) or "余额" in str(error) or "欠费" in str(error):
        return LLMBalanceError(provider=provider, raw=raw)

    # 5. 模型不存在 (404)
    if ("404" in err_str and "model" in err_str) or "model not found" in err_str or "model_not_exist" in err_str or "invalid model" in err_str or ("does not exist" in err_str and "model" in err_str):
        return LLMModelNotFoundError(provider=provider, model=model, raw=raw)

    # 6. 网络错误
    if ("connection" in err_str and ("error" in err_str or "refused" in err_str or "reset" in err_str or "aborted" in err_str)) or "network" in err_str or "dns" in err_str or "ssl" in err_str:
        return LLMNetworkError(provider=provider, raw=raw)

    # 7. 通用错误 - 显示错误类型和前 200 字符
    detail = f"{err_type}: {str(error)[:200]}"
    return LLMError(
        message=f"调用失败：{detail}",
        error_type="unknown", provider=provider, model=model,
        raw_response=raw, retriable=False,
    )


async def enforce_rate_limit(provider: str, interval: float = DEFAULT_INTERVAL) -> None:
    """
    强制速率限制：确保与上次同提供商调用间隔至少 interval 秒。
    """
    async with _rate_limit_lock:
        now = time.monotonic()
        last = _rate_limit_state.get(provider, 0)
        wait = last + interval - now
        if wait > 0:
            await asyncio.sleep(wait)
        _rate_limit_state[provider] = time.monotonic()


async def retry_with_backoff(
    func,
    *args,
    max_retries: int = 2,
    base_delay: float = 1.0,
    provider: str = "",
    **kwargs,
):
    """
    带指数退避的重试装饰器。
    仅对可重试错误（超时、网络、速率限制）重试。
    401/403/404 等不可重试错误直接抛出。
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            classified = classify_llm_error(e, provider=provider) if not isinstance(e, LLMError) else e
            last_error = classified

            if not classified.retriable or attempt >= max_retries:
                raise classified

            # 指数退避：1s, 2s, 4s...
            delay = base_delay * (2 ** attempt)
            if isinstance(classified, LLMRateLimitError):
                delay = max(delay, 5.0)  # 速率限制至少等 5 秒
            logger.warning("LLM call failed (attempt %d/%d), retrying in %.1fs: %s",
                           attempt + 1, max_retries + 1, delay, classified.message)
            await asyncio.sleep(delay)

    raise last_error  # type: ignore
