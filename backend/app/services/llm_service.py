"""LLM 调用服务 - 统一封装异步调用、缓存、成本记录、流式输出、超时、重试、速率限制"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import llm_cache
from app.core.config import get_settings
from app.core.exceptions import LLMError, LLMTimeoutError
from app.core.logging import get_logger
from app.services.llm_factory import build_llm, get_default_model
from app.utils.llm_errors import classify_llm_error, enforce_rate_limit, retry_with_backoff
from app.utils.token_estimator import estimate_tokens

logger = get_logger(__name__)

settings = get_settings()

# 默认超时（秒）和重试次数
DEFAULT_TIMEOUT = 60
DEFAULT_MAX_RETRIES = 2
# 速率限制间隔（秒）
RATE_LIMIT_INTERVAL = 1.0
# 流式调用最大总时长（秒）——防止极长输出无限占用连接
STREAM_MAX_DURATION = 300


class LLMConfig:
    """LLM 调用配置"""
    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.provider = provider or "DeepSeek"
        self.api_key = api_key or ""
        self.model = model or get_default_model(self.provider)
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def _id(self) -> str:
        return f"{self.provider}:{self.model}"


class LLMService:
    """LLM 调用服务：支持同步/异步/流式，带缓存、超时、重试、速率限制"""

    def __init__(self, db: Optional[AsyncSession] = None):
        self._db = db

    def _build_llm(self, cfg: LLMConfig) -> BaseChatModel:
        try:
            return build_llm(cfg.provider, cfg.api_key, cfg.model, cfg.temperature)
        except ValueError as e:
            raise LLMError(str(e), error_type="config_error", provider=cfg.provider, retriable=False)

    def _cache_key(self, cfg: LLMConfig, prompt: str, system: str = "") -> str:
        return llm_cache.make_key(
            provider=cfg.provider,
            model=cfg.model,
            prompt=prompt,
            system=system,
            temperature=cfg.temperature,
        )

    async def _do_invoke(self, llm: BaseChatModel, messages: list[BaseMessage], cfg: LLMConfig) -> str:
        """实际执行一次 invoke 调用（带超时）"""
        async def _call() -> str:
            response = await llm.ainvoke(messages)
            return str(response.content)

        return await asyncio.wait_for(_call(), timeout=cfg.timeout)

    async def invoke(
        self,
        prompt: str,
        cfg: LLMConfig,
        system_prompt: str = "",
        use_cache: bool = True,
        record_cost: bool = False,
        operation_type: str = "",
        brand: str = "",
        keyword: str = "",
        platform: str = "",
    ) -> str:
        """异步调用 LLM，返回完整字符串响应（带缓存、超时、重试、速率限制）"""
        cache_key = self._cache_key(cfg, prompt, system_prompt)
        if use_cache:
            cached = llm_cache.get(cache_key)
            if cached is not None:
                logger.debug("LLM cache hit: %s", cache_key[:16])
                return cached

        llm = self._build_llm(cfg)
        messages: list[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        # 速率限制
        await enforce_rate_limit(cfg.provider, RATE_LIMIT_INTERVAL)

        # 带重试的调用
        async def _attempt() -> str:
            return await self._do_invoke(llm, messages, cfg)

        try:
            result = await retry_with_backoff(
                _attempt,
                max_retries=cfg.max_retries,
                provider=cfg.provider,
            )
        except LLMError:
            raise
        except Exception as e:
            raise classify_llm_error(e, provider=cfg.provider, model=cfg.model, timeout=cfg.timeout)

        if not result.strip():
            raise LLMError("模型返回了空内容", error_type="empty_response", provider=cfg.provider, model=cfg.model, retriable=True)

        if use_cache:
            llm_cache.set(cache_key, result)

        if record_cost and self._db is not None:
            try:
                await self._record_cost(cfg, prompt, result, operation_type, brand, keyword, platform)
            except Exception as e:
                logger.warning("Failed to record API cost: %s", e)

        return result

    async def stream(
        self,
        prompt: str,
        cfg: LLMConfig,
        system_prompt: str = "",
        operation_type: str = "",
        brand: str = "",
        keyword: str = "",
        platform: str = "",
    ) -> AsyncGenerator[str, None]:
        """异步流式调用 LLM，逐 chunk yield 文本（带超时、速率限制）"""
        llm = self._build_llm(cfg)
        messages: list[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        # 速率限制
        await enforce_rate_limit(cfg.provider, RATE_LIMIT_INTERVAL)

        full_response: list[str] = []
        try:
            agen = llm.astream(messages)

            # 使用 per-chunk 超时 + 整体时长限制，防止极长输出无限占用连接
            loop = asyncio.get_running_loop()
            overall_deadline = loop.time() + STREAM_MAX_DURATION

            while True:
                remaining = overall_deadline - loop.time()
                if remaining <= 0:
                    raise asyncio.TimeoutError()
                chunk_timeout = min(cfg.timeout, remaining)
                try:
                    chunk = await asyncio.wait_for(agen.__anext__(), timeout=chunk_timeout)
                    content = str(chunk.content) if chunk.content else ""
                    if content:
                        full_response.append(content)
                        yield content
                except StopAsyncIteration:
                    break

        except asyncio.TimeoutError:
            result = "".join(full_response)
            if self._db is not None and result:
                try:
                    await self._record_cost(cfg, prompt, result, operation_type or "stream", brand, keyword, platform)
                except Exception as e:
                    logger.warning("Failed to record API cost after timeout: %s", e)
            raise LLMTimeoutError(provider=cfg.provider, timeout=cfg.timeout)
        except LLMError:
            raise
        except Exception as e:
            raise classify_llm_error(e, provider=cfg.provider, model=cfg.model, timeout=cfg.timeout)

        # 流式不使用缓存，但记录成本
        result = "".join(full_response)
        if self._db is not None and result:
            try:
                await self._record_cost(cfg, prompt, result, operation_type or "stream", brand, keyword, platform)
            except Exception as e:
                logger.warning("Failed to record API cost: %s", e)

    async def invoke_with_chain(
        self,
        template: str,
        variables: dict[str, Any],
        cfg: LLMConfig,
        use_cache: bool = True,
        **kwargs: Any,
    ) -> str:
        """使用 PromptTemplate + chain 模式调用"""
        prompt_text = ChatPromptTemplate.from_template(template).format(**variables)
        return await self.invoke(prompt_text, cfg, use_cache=use_cache, **kwargs)

    async def stream_with_chain(
        self,
        template: str,
        variables: dict[str, Any],
        cfg: LLMConfig,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """使用 PromptTemplate 流式调用"""
        prompt_text = ChatPromptTemplate.from_template(template).format(**variables)
        async for chunk in self.stream(prompt_text, cfg, **kwargs):
            yield chunk

    async def _record_cost(
        self,
        cfg: LLMConfig,
        input_text: str,
        output_text: str,
        operation_type: str,
        brand: str,
        keyword: str,
        platform: str,
    ) -> None:
        """记录 API 调用成本到数据库"""
        from app.models.api_call import ApiCall
        from app.services.roi_service import ROIService

        input_tokens = estimate_tokens(input_text)
        output_tokens = estimate_tokens(output_text)
        total_tokens = input_tokens + output_tokens
        roi = ROIService()
        cost_usd, cost_cny = roi.calculate_cost(
            cfg.provider, cfg.model, input_tokens, output_tokens
        )

        api_call = ApiCall(
            operation_type=operation_type or "unknown",
            provider=cfg.provider,
            model=cfg.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            cost_cny=cost_cny,
            keyword=keyword or None,
            platform=platform or None,
            brand=brand or None,
        )
        self._db.add(api_call)
        await self._db.flush()
