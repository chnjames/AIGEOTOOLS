"""异步 LLM 工厂模块 - 构建支持 async 调用的 LLM 客户端"""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Any, Optional

from app.core.logging import get_logger
from app.services.chat_doubao import create_chat_doubao

logger = get_logger(__name__)

# 用于保护环境变量修改的锁，避免并发请求时文心一言的 temp_env_vars 竞态
_env_lock = threading.Lock()


@contextmanager
def temp_env_vars(vars_dict: dict[str, str]):
    """线程安全地临时设置环境变量"""
    with _env_lock:
        old_values: dict[str, Optional[str]] = {}
        for key, value in vars_dict.items():
            old_values[key] = os.environ.get(key)
            os.environ[key] = value
        try:
            yield
        finally:
            for key, old_value in old_values.items():
                if old_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old_value


def build_deepseek(api_key: str, model: str, temperature: float, base_url: str = ""):
    from langchain_deepseek import ChatDeepSeek
    kwargs: dict = dict(api_key=api_key, model=model, temperature=temperature, streaming=True)
    if base_url:
        kwargs["api_base"] = base_url
    return ChatDeepSeek(**kwargs)


def build_openai(api_key: str, model: str, temperature: float, base_url: str = ""):
    from langchain_openai import ChatOpenAI
    kwargs: dict = dict(api_key=api_key, model=model, temperature=temperature, streaming=True)
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def build_tongyi(api_key: str, model: str, temperature: float, base_url: str = ""):
    try:
        from langchain_community.chat_models import ChatTongyi
        kwargs: dict = dict(api_key=api_key, model=model, model_kwargs={"temperature": temperature}, streaming=True)
        return ChatTongyi(**kwargs)
    except ImportError:
        from langchain_aliyun import ChatTongyi  # type: ignore
        kwargs: dict = dict(api_key=api_key, model=model, temperature=temperature, streaming=True)
        return ChatTongyi(**kwargs)


def build_groq(api_key: str, model: str, temperature: float, base_url: str = ""):
    from langchain_groq import ChatGroq
    kwargs: dict = dict(api_key=api_key, model=model, temperature=temperature, streaming=True)
    if base_url:
        kwargs["base_url"] = base_url
    return ChatGroq(**kwargs)


def build_moonshot(api_key: str, model: str, temperature: float, base_url: str = ""):
    try:
        from langchain_moonshot import ChatMoonshot  # type: ignore
        kwargs: dict = dict(api_key=api_key, model=model, temperature=temperature, streaming=True)
        if base_url:
            kwargs["base_url"] = base_url
        return ChatMoonshot(**kwargs)
    except ImportError:
        from langchain_community.chat_models import MoonshotChat  # type: ignore
        kwargs: dict = dict(api_key=api_key, model=model, temperature=temperature, streaming=True)
        return MoonshotChat(**kwargs)


def build_doubao(api_key: str, temperature: float, model: str = "", base_url: str = ""):
    return create_chat_doubao(api_key=api_key, temperature=temperature)


def build_wenxin(api_key: str, model: str, temperature: float, base_url: str = ""):
    parts = api_key.split(":", 1)
    if len(parts) != 2:
        raise ValueError("文心一言 API Key 格式错误，应为：app_key:app_secret（用冒号分隔）")
    app_key, app_secret = parts
    try:
        from langchain_community.chat_models import QianfanChatEndpoint
        with temp_env_vars({"QIANFAN_AK": app_key, "QIANFAN_SK": app_secret}):
            return QianfanChatEndpoint(
                model=model if model else "ernie-4.0-8k",
                temperature=temperature,
                streaming=True,
            )
    except ImportError:
        try:
            from langchain_wenxin import ChatWenxin
            return ChatWenxin(
                baidu_api_key=app_key,
                baidu_secret_key=app_secret,
                model=model if model else "ernie-4.0-8k",
                temperature=temperature,
                streaming=True,
            )
        except ImportError as e:
            raise ValueError(f"文心一言初始化失败：缺少依赖库。错误：{e}")


PROVIDER_BUILDERS: dict[str, Any] = {
    "DeepSeek": lambda ak, m, t, bu="": build_deepseek(ak, m, t, bu),
    "OpenAI (GPT)": lambda ak, m, t, bu="": build_openai(ak, m, t, bu),
    "Tongyi (通义千问)": lambda ak, m, t, bu="": build_tongyi(ak, m, t, bu),
    "Groq": lambda ak, m, t, bu="": build_groq(ak, m, t, bu),
    "Moonshot (Kimi)": lambda ak, m, t, bu="": build_moonshot(ak, m, t, bu),
    "豆包（字节跳动）": lambda ak, m, t, bu="": build_doubao(ak, t, m, bu),
    "文心一言（百度）": lambda ak, m, t, bu="": build_wenxin(ak, m, t, bu),
}


def build_llm(provider: str, api_key: str, model: str, temperature: float, base_url: str = ""):
    """
    构建支持 async/streaming 的 LLM 实例。
    Returns: LangChain BaseChatModel 实例
    Raises: ValueError 如果 provider 不支持或初始化失败
    """
    builder = PROVIDER_BUILDERS.get(provider)
    if builder is None:
        raise ValueError(f"不支持的 LLM 提供商: {provider}。支持的提供商: {', '.join(PROVIDER_BUILDERS.keys())}")
    if not api_key or not api_key.strip():
        raise ValueError(f"{provider} 的 API Key 未配置")
    try:
        llm = builder(api_key, model, temperature, base_url)
        logger.info("LLM initialized: provider=%s model=%s base_url=%s", provider, model, base_url or "(default)")
        return llm
    except ValueError:
        raise
    except Exception as e:
        logger.error("LLM init failed: provider=%s error=%s", provider, e)
        raise ValueError(f"{provider} 初始化失败：{type(e).__name__}: {e}")


def get_supported_providers() -> list[str]:
    return list(PROVIDER_BUILDERS.keys())


def get_default_model(provider: str) -> str:
    defaults = {
        "DeepSeek": "deepseek-v4-flash",
        "OpenAI (GPT)": "gpt-4o-mini",
        "Tongyi (通义千问)": "qwen-max",
        "Groq": "llama-3.3-70b-versatile",
        "Moonshot (Kimi)": "moonshot-v1-128k",
        "豆包（字节跳动）": "",
        "文心一言（百度）": "ernie-4.0-8k",
    }
    return defaults.get(provider, "")


PROVIDER_LIST = get_supported_providers()
