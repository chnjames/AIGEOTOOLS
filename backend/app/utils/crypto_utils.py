"""API Key 加密/解密工具

使用 cryptography.Fernet（AES-128-CBC + HMAC-SHA256）提供密码学安全的对称加密。
加密结果带 `enc:v1:` 前缀，便于 is_encrypted() 严格判断。
兼容历史 XOR 数据：decrypt 时无前缀的旧密文会尝试 legacy XOR 解密。
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

_PREFIX = "enc:v1:"

# 新密钥来源：优先 GEO_ENCRYPTION_KEY（完整 Fernet key），其次从 GEO_ENCRYPTION_SEED 派生
_KEY_ENV = "GEO_ENCRYPTION_KEY"
_SEED_ENV = "GEO_ENCRYPTION_SEED"
_SEED_FILE = ".encryption_seed"


def _get_fernet() -> Fernet:
    """获取 Fernet 实例，密钥从环境变量或种子文件派生。

    密钥来源优先级：
    1. 环境变量 ``GEO_ENCRYPTION_KEY``（完整的 Fernet key，urlsafe base64 编码）
    2. 环境变量 ``GEO_ENCRYPTION_SEED``（种子，派生为 Fernet key）
    3. 本地种子文件 ``.encryption_seed``（派生为 Fernet key），首次使用时自动生成

    种子文件以 0o600 权限写入，仅限当前用户读写，避免密钥泄露。
    """
    # 优先从环境变量 GEO_ENCRYPTION_KEY 读取完整 Fernet key
    key_b64 = os.environ.get(_KEY_ENV, "").strip()
    if not key_b64:
        # 兼容旧 GEO_ENCRYPTION_SEED：派生 Fernet key
        seed_hex = os.environ.get(_SEED_ENV, "").strip()
        if not seed_hex and os.path.exists(_SEED_FILE):
            try:
                with open(_SEED_FILE, "r") as f:
                    seed_hex = f.read().strip()
            except OSError:
                seed_hex = ""
        if not seed_hex:
            seed_hex = secrets.token_hex(32)
            try:
                # 写入种子文件后立即设置严格权限 0o600，仅当前用户可读写
                with open(_SEED_FILE, "w") as f:
                    f.write(seed_hex)
                os.chmod(_SEED_FILE, 0o600)
            except OSError:
                pass
            os.environ[_SEED_ENV] = seed_hex
        derived = hashlib.sha256(seed_hex.encode("utf-8")).digest()
        key_b64 = base64.urlsafe_b64encode(derived).decode("ascii")
    return Fernet(key_b64.encode("ascii"))


def _legacy_xor(data: bytes, key: bytes) -> bytes:
    """旧版 XOR 解密（仅用于兼容历史数据）。"""
    kl = len(key)
    return bytes(b ^ key[i % kl] for i, b in enumerate(data))


def _legacy_seed() -> bytes:
    seed_hex = os.environ.get(_SEED_ENV, "").strip()
    if not seed_hex and os.path.exists(_SEED_FILE):
        try:
            with open(_SEED_FILE, "r") as f:
                seed_hex = f.read().strip()
        except OSError:
            seed_hex = ""
    if not seed_hex:
        return b""
    return hashlib.sha256(seed_hex.encode("utf-8")).digest()


def encrypt_api_key(plain_key: str) -> str:
    """加密 API Key，返回带 enc:v1: 前缀的字符串。"""
    if not plain_key:
        return ""
    token = _get_fernet().encrypt(plain_key.encode("utf-8")).decode("ascii")
    return _PREFIX + token


def decrypt_api_key(encrypted_key: str) -> str:
    """解密 API Key。

    - `enc:v1:` 前缀：用 Fernet 解密（失败抛 InvalidToken，不再回退明文）
    - 无前缀：尝试 legacy XOR 解密（兼容历史数据），成功返回明文
    - 均失败：视为明文返回，并记录 warning 提示重新保存以加密
    """
    if not encrypted_key:
        return ""
    if encrypted_key.startswith(_PREFIX):
        token = encrypted_key[len(_PREFIX):]
        return _get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    # legacy: 尝试旧 XOR 解密
    seed = _legacy_seed()
    if seed:
        try:
            data = base64.urlsafe_b64decode(encrypted_key.encode("ascii"))
            result = _legacy_xor(data, seed).decode("utf-8")
            if all(c.isprintable() or c in "\n\r\t" for c in result):
                logger.info("decrypt_api_key: 已用 legacy 方式解密历史数据，建议重新保存以升级为 Fernet 加密。")
                return result
        except Exception:
            pass
    logger.warning("decrypt_api_key: 未识别为加密格式，按明文返回（建议重新保存以加密）。")
    return encrypted_key


def is_encrypted(key: str) -> bool:
    """判断是否已用新格式加密（仅认 enc:v1: 前缀，严格判断）。"""
    if not key:
        return False
    return key.startswith(_PREFIX)
