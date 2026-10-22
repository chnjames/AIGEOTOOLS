"""LLM 响应缓存（TTL + LRU 淘汰）

缓存后端架构说明
================

当前实现使用基于 ``OrderedDict`` 的 **进程内存缓存**，适用于以下场景：

- **单实例部署**：开发环境、小型生产环境（单进程 / 单容器）。
- **低并发读取**：缓存命中在进程内完成，无网络开销。

已知限制（MVP 阶段可接受）：

1. **多实例不共享**：当应用以多实例（多进程 / 多容器 / 多节点）部署时，
   每个实例维护各自独立的缓存副本，缓存命中率会下降，同一 LLM 请求可能
   在不同实例上重复调用。如需跨实例共享缓存，应替换为分布式后端
   （如 ``RedisBackend``）。
2. **重启后丢失**：进程重启后所有缓存条目清空，需要重新预热。对于 LLM
   响应缓存而言，这意味着重启后首批请求会穿透到 LLM Provider。如需持久化，
   应替换为 ``RedisBackend`` 或其他持久化存储。
3. **内存受限**：缓存容量受进程可用内存限制，通过 ``max_size`` 参数控制
   条目上限并执行 LRU 淘汰。

迁移到 Redis 等分布式后端
-------------------------

本模块定义了 :class:`CacheBackendInterface` 抽象基类，规定了缓存后端
必须实现的接口（``get`` / ``set`` / ``clear`` / ``stats``）。
当前使用的 :class:`MemoryCacheBackend` 即为该接口的具体实现。

未来切换到 Redis 时，只需：

1. 实现 ``RedisBackend(CacheBackendInterface)``，在 ``get`` / ``set`` 中
   使用 Redis 的 ``SETEX`` / ``GET`` 命令，TTL 由 Redis 原生管理。
2. 将模块底部的 ``llm_cache`` 实例化替换为 ``RedisBackend`` 实例。
3. 调用方代码（``llm_cache.get(key)`` / ``llm_cache.set(key, value)``）
   无需任何修改，实现无缝切换。

::

    # 示例：未来切换到 Redis
    # llm_cache = RedisBackend(
    #     redis_url="redis://localhost:6379/0",
    #     ttl_seconds=_settings.LLM_CACHE_TTL_SECONDS,
    #     enabled=_settings.LLM_CACHE_ENABLED,
    # )
"""
import hashlib
import json
import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheBackendInterface(ABC):
    """缓存后端抽象基类。

    定义所有缓存后端（内存、Redis 等）必须实现的统一接口。
    通过依赖该接口而非具体实现，调用方代码可在不同后端间无缝切换。

    子类需要实现以下方法：
        - :meth:`get`：获取缓存值
        - :meth:`set`：写入缓存值
        - :meth:`clear`：清空所有缓存
        - :meth:`stats`：返回缓存统计信息
    """

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值。

        Args:
            key: 缓存键。

        Returns:
            缓存值，不存在或已过期时返回 None。
        """
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """写入缓存值。

        Args:
            key: 缓存键。
            value: 缓存值。
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """清空所有缓存条目。"""
        raise NotImplementedError

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """返回缓存统计信息。

        Returns:
            包含 ``enabled``、``total_entries`` 等键的统计字典。
        """
        raise NotImplementedError


class MemoryCacheBackend(CacheBackendInterface):
    """线程安全的内存 LRU 缓存后端，支持 TTL 过期。

    基于 ``OrderedDict`` 实现 LRU（Least Recently Used）淘汰策略，
    配合 TTL（Time-To-Live）自动过期。适用于单实例部署场景。

    局限性：
        - 多实例部署时缓存不共享，每个实例维护独立副本。
        - 进程重启后缓存丢失，需重新预热。
        - 如需跨实例共享或持久化，请使用 ``RedisBackend`` 等分布式后端。

    Args:
        ttl_seconds: 缓存条目存活时间（秒），过期后自动失效。
        max_size: 最大缓存条目数，超出时按 LRU 策略淘汰最早使用的条目。
        enabled: 是否启用缓存，为 False 时 get 始终返回 None、set 为空操作。
    """

    def __init__(
        self,
        ttl_seconds: int = 3600,
        max_size: int = 1000,
        enabled: bool = True,
    ):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self.enabled = enabled
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def make_key(provider: str, model: str, prompt: str, **extra: Any) -> str:
        """基于请求参数生成缓存 key（SHA-256 哈希）"""
        raw = json.dumps(
            {"provider": provider, "model": model, "prompt": prompt, **extra},
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，不存在或已过期返回 None"""
        if not self.enabled:
            return None
        with self._lock:
            if key not in self._cache:
                return None
            expiry, value = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                return None
            # LRU：移到末尾表示最近使用
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        """写入缓存"""
        if not self.enabled:
            return
        with self._lock:
            self._cache[key] = (time.time() + self.ttl, value)
            self._cache.move_to_end(key)
            self._evict()

    def _evict(self) -> None:
        """LRU 淘汰：超出最大容量时删除最早的条目"""
        while len(self._cache) > self.max_size:
            evicted_key, _ = self._cache.popitem(last=False)
            logger.debug("LLM cache evicted key: %s", evicted_key[:16])

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def stats(self) -> dict[str, Any]:
        """返回缓存统计信息"""
        with self._lock:
            now = time.time()
            valid = sum(1 for exp, _ in self._cache.values() if exp > now)
            return {
                "enabled": self.enabled,
                "total_entries": len(self._cache),
                "valid_entries": valid,
                "max_size": self.max_size,
                "ttl_seconds": self.ttl,
            }


# 向后兼容别名：保留 LLMCache 名称，使现有调用方代码无需修改
LLMCache = MemoryCacheBackend


_settings = get_settings()
llm_cache: CacheBackendInterface = MemoryCacheBackend(
    ttl_seconds=_settings.LLM_CACHE_TTL_SECONDS,
    max_size=_settings.LLM_CACHE_MAX_SIZE,
    enabled=_settings.LLM_CACHE_ENABLED,
)
