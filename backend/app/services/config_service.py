"""应用配置服务 - 管理数据库中的配置存储"""
from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.app_config import AppConfig
from app.schemas.config import AppConfigResponse, AppConfigUpdate
from app.utils.text_utils import mask_api_key
from app.utils.crypto_utils import encrypt_api_key, decrypt_api_key, is_encrypted

logger = get_logger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "gen_provider": "DeepSeek",
    "gen_api_key": "",
    "verify_providers": ["DeepSeek"],
    "verify_keys": {"DeepSeek": ""},
    "tongyi_wanxiang_api_key": "",
    "brand": "",
    "advantages": "",
    "competitors": "",
    "temperature": 0.7,
    "use_knowledge_base": False,
    "roi_value_per_mention": 50.0,
    "platform_value_coefficients": {},
    "first_run_completed": False,
    "default_verify_mode": "natural",
}


class ConfigService:
    def __init__(self, db: AsyncSession):
        self._db = db

    # 需要加密存储的 API Key 字段
    _ENCRYPTED_FIELDS = {"gen_api_key", "tongyi_wanxiang_api_key"}
    _VERIFY_KEYS_FIELD = "verify_keys"  # dict 类型的 key 字段

    async def get_config(self) -> dict[str, Any]:
        result = await self._db.execute(select(AppConfig).where(AppConfig.id == 1))
        row = result.scalar_one_or_none()
        if row is None:
            return {**DEFAULT_CONFIG}
        try:
            cfg = json.loads(row.config_json)
            merged = {**DEFAULT_CONFIG, **cfg}
            # 解密 API Key 字段（decrypt_api_key 对明文/旧格式均安全，直接调用以支持自动迁移）
            for field in self._ENCRYPTED_FIELDS:
                if merged.get(field):
                    merged[field] = decrypt_api_key(merged[field])
            # 解密 verify_keys 字典中的值
            vk = merged.get(self._VERIFY_KEYS_FIELD, {})
            if isinstance(vk, dict):
                for k, v in vk.items():
                    if v:
                        vk[k] = decrypt_api_key(v)
            return merged
        except json.JSONDecodeError:
            logger.warning("Failed to parse app_config JSON, using defaults")
            return {**DEFAULT_CONFIG}

    async def save_config(self, cfg: dict[str, Any]) -> dict[str, Any]:
        merged = {**(await self.get_config()), **{k: v for k, v in cfg.items() if v is not None}}
        # 加密 API Key 字段后再存储
        to_save = {**merged}
        for field in self._ENCRYPTED_FIELDS:
            val = to_save.get(field, "")
            if val and not is_encrypted(val):
                to_save[field] = encrypt_api_key(val)
        # 加密 verify_keys 字典中的值
        vk = to_save.get(self._VERIFY_KEYS_FIELD, {})
        if isinstance(vk, dict):
            encrypted_vk = {}
            for k, v in vk.items():
                encrypted_vk[k] = encrypt_api_key(v) if v and not is_encrypted(v) else v
            to_save[self._VERIFY_KEYS_FIELD] = encrypted_vk
        result = await self._db.execute(select(AppConfig).where(AppConfig.id == 1))
        row = result.scalar_one_or_none()
        if row is None:
            row = AppConfig(id=1, config_json=json.dumps(to_save, ensure_ascii=False))
            self._db.add(row)
        else:
            row.config_json = json.dumps(to_save, ensure_ascii=False)
        await self._db.flush()
        return merged  # 返回明文版本（供内部使用）

    async def get_response(self) -> AppConfigResponse:
        cfg = await self.get_config()
        gen_key = cfg.get("gen_api_key", "")
        verify_keys = cfg.get("verify_keys", {})
        return AppConfigResponse(
            gen_provider=cfg.get("gen_provider", "DeepSeek"),
            gen_api_key_masked=mask_api_key(gen_key) if gen_key else "",
            gen_api_key_configured=bool(gen_key),
            verify_providers=cfg.get("verify_providers", []),
            verify_keys_configured={p: bool(verify_keys.get(p, "")) for p in cfg.get("verify_providers", [])},
            tongyi_wanxiang_configured=bool(cfg.get("tongyi_wanxiang_api_key", "")),
            brand=cfg.get("brand", ""),
            advantages=cfg.get("advantages", ""),
            competitors=cfg.get("competitors", ""),
            temperature=cfg.get("temperature", 0.7),
            use_knowledge_base=cfg.get("use_knowledge_base", False),
            roi_value_per_mention=cfg.get("roi_value_per_mention", 50.0),
            platform_value_coefficients=cfg.get("platform_value_coefficients", {}),
            first_run_completed=cfg.get("first_run_completed", False),
            default_verify_mode=cfg.get("default_verify_mode", "natural"),
        )

    async def update_from_schema(self, update: AppConfigUpdate) -> AppConfigResponse:
        data = update.model_dump(exclude_unset=True)
        await self.save_config(data)
        return await self.get_response()

    async def get_llm_config(self) -> dict[str, Any]:
        """返回可直接用于 LLM 构建的配置（含明文 key，仅供内部使用）"""
        return await self.get_config()
