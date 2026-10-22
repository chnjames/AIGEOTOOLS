"""平台发布服务 - 从 platform_sync/ 迁移"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.platform_account import PlatformAccount
from app.models.publish_record import PublishRecord
from app.models.article import Article
from app.utils.crypto_utils import encrypt_api_key, decrypt_api_key, is_encrypted

logger = get_logger(__name__)

# PlatformAccount 中需要加密存储的凭据字段
_CRED_FIELDS = ("api_key", "api_secret", "access_token", "refresh_token")

SUPPORTED_PLATFORMS_INFO: list[dict[str, Any]] = [
    {"key": "zhihu", "name": "知乎", "publish_methods": ["copy", "api"], "icon": "知"},
    {"key": "xiaohongshu", "name": "小红书", "publish_methods": ["copy"], "icon": "红"},
    {"key": "csdn", "name": "CSDN", "publish_methods": ["copy", "api"], "icon": "C"},
    {"key": "wechat", "name": "微信公众号", "publish_methods": ["copy"], "icon": "微"},
    {"key": "bilibili", "name": "B站", "publish_methods": ["copy"], "icon": "B"},
    {"key": "github", "name": "GitHub", "publish_methods": ["github"], "icon": "G"},
    {"key": "juejin", "name": "掘金", "publish_methods": ["copy"], "icon": "掘"},
    {"key": "toutiao", "name": "头条号", "publish_methods": ["copy"], "icon": "头"},
    {"key": "baijia", "name": "百家号", "publish_methods": ["copy"], "icon": "百"},
    {"key": "sohu", "name": "搜狐号", "publish_methods": ["copy"], "icon": "搜"},
]


class PlatformService:
    def __init__(self, db: AsyncSession):
        self._db = db

    def get_supported_platforms(self) -> list[dict[str, Any]]:
        return SUPPORTED_PLATFORMS_INFO

    async def add_account(self, platform: str, account_type: str,
                          account_name: str = "", api_key: str = "",
                          api_secret: str = "", access_token: str = "",
                          config_json: Optional[dict] = None, brand: str = "") -> PlatformAccount:
        acct = PlatformAccount(
            platform=platform, account_type=account_type,
            account_name=account_name,
            api_key=encrypt_api_key(api_key) if api_key else None,
            api_secret=encrypt_api_key(api_secret) if api_secret else None,
            access_token=encrypt_api_key(access_token) if access_token else None,
            config_json=json.dumps(config_json, ensure_ascii=False) if config_json else None,
            brand=brand, is_active=True,
        )
        self._db.add(acct)
        await self._db.flush()
        return acct

    async def get_accounts(self, brand: str = "") -> list[PlatformAccount]:
        query = select(PlatformAccount)
        if brand:
            query = query.where(PlatformAccount.brand == brand)
        result = await self._db.execute(query.order_by(PlatformAccount.created_at.desc()))
        return list(result.scalars().all())

    async def update_account(self, account_id: int, **kwargs: Any) -> Optional[PlatformAccount]:
        acct = await self._db.get(PlatformAccount, account_id)
        if not acct:
            return None
        if "config_json" in kwargs and kwargs["config_json"] is not None:
            kwargs["config_json"] = json.dumps(kwargs["config_json"], ensure_ascii=False)
        for k, v in kwargs.items():
            if hasattr(acct, k) and v is not None:
                # 凭据字段加密后再写入（避免明文落库）
                if k in _CRED_FIELDS:
                    v = encrypt_api_key(v) if not is_encrypted(v) else v
                setattr(acct, k, v)
        await self._db.flush()
        return acct

    def decrypt_credentials(self, acct: PlatformAccount) -> dict[str, Optional[str]]:
        """解密平台账号凭据，返回明文字典（仅供需要使用凭据的内部场景调用）。"""
        return {
            "api_key": decrypt_api_key(acct.api_key) if acct.api_key else None,
            "api_secret": decrypt_api_key(acct.api_secret) if acct.api_secret else None,
            "access_token": decrypt_api_key(acct.access_token) if acct.access_token else None,
            "refresh_token": decrypt_api_key(acct.refresh_token) if acct.refresh_token else None,
        }

    async def delete_account(self, account_id: int) -> bool:
        acct = await self._db.get(PlatformAccount, account_id)
        if acct:
            await self._db.delete(acct)
            await self._db.flush()
            return True
        return False

    def account_to_response(self, acct: PlatformAccount) -> dict[str, Any]:
        return {
            "id": acct.id, "platform": acct.platform,
            "account_type": acct.account_type, "account_name": acct.account_name,
            "is_active": acct.is_active, "brand": acct.brand,
            "has_api_key": bool(acct.api_key),
            "has_token": bool(acct.access_token),
            "created_at": acct.created_at.isoformat() if acct.created_at else None,
        }

    async def publish_article(
        self, article_id: int, platform: str, publish_method: str = "copy",
        config: Optional[dict] = None
    ) -> dict[str, Any]:
        article = await self._db.get(Article, article_id)
        if not article:
            return {"success": False, "message": "文章不存在"}

        record = PublishRecord(
            article_id=article_id, platform=platform,
            publish_method=publish_method, publish_status="pending",
        )
        self._db.add(record)
        await self._db.flush()

        try:
            if publish_method == "copy":
                # 复制到剪贴板（在Web环境中返回内容供前端复制）
                record.publish_status = "success"
                record.published_at = datetime.now(timezone.utc)
                article.publish_status = "ready"
                await self._db.flush()
                return {
                    "success": True, "platform": platform,
                    "message": "内容已准备好，请复制到平台发布",
                    "content": article.content, "filename": article.filename,
                }

            elif publish_method == "github":
                token = (config or {}).get("token", "")
                repo = (config or {}).get("repo", "")
                branch = (config or {}).get("branch", "main")
                path = (config or {}).get("path", f"geo-articles/{article.filename or article.keyword}.md")
                if not token or not repo:
                    raise ValueError("GitHub 发布需要 token 和 repo 参数")
                file_url = await self._publish_to_github(
                    token=token, repo=repo, path=path, branch=branch,
                    content=article.content,
                    commit_msg=f"GEO: add {article.keyword} for {article.platform}",
                )
                record.publish_status = "success"
                record.published_at = datetime.now(timezone.utc)
                record.publish_url = file_url
                article.publish_status = "published"
                article.publish_urls = file_url
                await self._db.flush()
                return {
                    "success": True, "platform": "GitHub",
                    "publish_url": file_url,
                    "message": f"已发布到 GitHub: {repo}/{path}",
                }

            else:
                raise ValueError(f"不支持的发布方式: {publish_method}")

        except Exception as e:
            record.publish_status = "failed"
            record.error_message = str(e)[:500]
            record.retry_count = (record.retry_count or 0) + 1
            await self._db.flush()
            logger.error("Publish failed: %s", e)
            return {"success": False, "platform": platform, "message": str(e)[:200]}

    async def get_publish_records(self, article_id: Optional[int] = None) -> list[PublishRecord]:
        query = select(PublishRecord)
        if article_id:
            query = query.where(PublishRecord.article_id == article_id)
        result = await self._db.execute(query.order_by(PublishRecord.created_at.desc()))
        return list(result.scalars().all())

    async def _publish_to_github(
        self, token: str, repo: str, path: str, branch: str,
        content: str, commit_msg: str,
    ) -> str:
        """通过 GitHub Contents API 创建/更新文件，返回文件 URL。"""
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        body: dict[str, Any] = {"message": commit_msg, "content": encoded, "branch": branch}

        # 检查文件是否已存在（若存在需获取 sha 才能更新）
        async with httpx.AsyncClient(timeout=30) as client:
            check_resp = await client.get(url, headers=headers, params={"ref": branch})
            if check_resp.status_code == 200:
                existing_sha = check_resp.json().get("sha", "")
                body["sha"] = existing_sha

            resp = await client.put(url, headers=headers, json=body)
            if resp.status_code not in (200, 201):
                # 安全考虑：错误信息只返回状态码和简短提示，不包含完整 body，
                # 避免泄露 token 或敏感信息（GitHub 偶尔会在错误响应中回显请求信息）。
                # 完整响应体仅记录到日志供排查，且日志中绝不包含 Authorization 头。
                try:
                    err_body = resp.text[:300]
                except Exception:
                    err_body = "<unreadable>"
                logger.warning(
                    "GitHub Contents API PUT failed: status=%s repo=%s path=%s body=%s",
                    resp.status_code, repo, path, err_body,
                )
                # 映射常见状态码到简短提示
                if resp.status_code in (401, 403):
                    msg = f"GitHub 鉴权失败（{resp.status_code}），请检查 token 权限"
                elif resp.status_code == 404:
                    msg = f"GitHub 仓库或路径不存在（{resp.status_code}），请检查 repo/branch/path"
                elif resp.status_code == 422:
                    msg = f"GitHub 请求参数无效（{resp.status_code}），请检查 branch/path 是否正确"
                else:
                    msg = f"GitHub API 返回错误状态码 {resp.status_code}"
                raise ValueError(msg)
            data = resp.json()
            file_url = data.get("content", {}).get("html_url", f"https://github.com/{repo}/blob/{branch}/{path}")
            return file_url

    async def get_publish_record(self, record_id: int) -> Optional[PublishRecord]:
        return await self._db.get(PublishRecord, record_id)

    async def retry_publish(self, record_id: int, config: Optional[dict] = None) -> dict[str, Any]:
        """重试失败的发布记录

        Args:
            record_id: 发布记录 ID
            config: 可选的发布配置覆盖（如 GitHub token/repo）；不传则沿用原有逻辑（copy 模式无需配置）

        Returns:
            dict: 与 publish_article 一致的结果字典
        """
        record = await self._db.get(PublishRecord, record_id)
        if not record:
            raise NotFoundError("发布记录不存在")

        if record.publish_status == "success":
            raise ValidationError("该发布记录已成功，无需重试")

        if record.publish_status == "pending":
            raise ValidationError("该发布正在进行中，请勿重复操作")

        MAX_RETRIES = 5
        if (record.retry_count or 0) >= MAX_RETRIES:
            raise ValidationError(f"已达到最大重试次数（{MAX_RETRIES}次），请检查配置后重新创建发布任务")

        article = await self._db.get(Article, record.article_id) if record.article_id else None
        if not article:
            raise NotFoundError("关联文章不存在或已被删除")

        # 重置记录状态
        record.publish_status = "pending"
        record.error_message = None
        record.retry_count = (record.retry_count or 0) + 1
        await self._db.flush()

        publish_method = record.publish_method
        platform = record.platform

        try:
            if publish_method == "copy":
                record.publish_status = "success"
                record.published_at = datetime.now(timezone.utc)
                record.error_message = None
                await self._db.flush()
                return {
                    "success": True, "platform": platform,
                    "message": "内容已准备好，请复制到平台发布",
                    "content": article.content, "filename": article.filename,
                }

            elif publish_method == "github":
                token = (config or {}).get("token", "")
                repo = (config or {}).get("repo", "")
                branch = (config or {}).get("branch", "main")
                path = (config or {}).get("path", f"geo-articles/{article.filename or article.keyword}.md")
                if not token or not repo:
                    raise ValueError("GitHub 重试发布需要提供 token 和 repo 参数")
                file_url = await self._publish_to_github(
                    token=token, repo=repo, path=path, branch=branch,
                    content=article.content,
                    commit_msg=f"GEO: update {article.keyword}",
                )
                record.publish_status = "success"
                record.published_at = datetime.now(timezone.utc)
                record.publish_url = file_url
                record.error_message = None
                await self._db.flush()
                return {
                    "success": True, "platform": "GitHub",
                    "publish_url": file_url,
                    "message": f"已发布到 GitHub: {repo}/{path}",
                }

            else:
                raise ValueError(f"不支持的发布方式: {publish_method}")

        except Exception as e:
            record.publish_status = "failed"
            record.error_message = str(e)
            await self._db.flush()
            logger.error("Retry publish failed for record %s: %s", record_id, e)
            return {"success": False, "platform": platform, "message": str(e)}
