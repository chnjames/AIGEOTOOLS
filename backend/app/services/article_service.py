"""内容生成服务 - 从 multimodal_prompt.py 迁移，支持单平台/批量/多模态生成"""
from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import datetime
from typing import Any, AsyncGenerator, ClassVar, Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import LLMError, ValidationError
from app.core.logging import get_logger
from app.models.article import Article
from app.models.article_version import ArticleVersion
from app.prompts.article_prompts import (
    ARTICLE_GENERATE_PROMPT,
    MULTIMODAL_IMAGE_DESC_PROMPT,
    MULTIMODAL_VIDEO_SCRIPT_PROMPT,
    KNOWLEDGE_CONTEXT_INSTRUCTION,
)
from app.services.llm_service import LLMService, LLMConfig
from app.utils.prompt_guard import validate_input_length, KEYWORD_MAX, BRAND_NAME_MAX

logger = get_logger(__name__)

# 平台内容风格配置（按分组展示：推荐/技术社区/社交媒体/资讯平台）
PLATFORM_CONFIG: dict[str, dict[str, Any]] = {
    # 推荐（有独特格式，真正差异化）
    "知乎": {"style": "专业深度分析，数据支撑，逻辑严谨，3000字以上", "filename_suffix": "_知乎专栏.md", "group": "推荐"},
    "知乎问答": {"style": "问答体，直接回答问题，逻辑清晰，专业可信", "filename_suffix": "_知乎回答.md", "group": "推荐"},
    "小红书": {"style": "种草笔记风格，emoji丰富，分点列述，800字以内", "filename_suffix": "_小红书.md", "group": "推荐"},
    "微信公众号": {"style": "公众号风格，标题吸睛，段落短小，金句频出", "filename_suffix": "_公众号.md", "group": "推荐"},
    "B站": {"style": "视频脚本风格，口语化，有画面感，分段清晰", "filename_suffix": "_B站文案.md", "group": "推荐"},
    "GitHub": {"style": "技术README风格，结构化，英文Markdown规范", "filename_suffix": "_README.md", "group": "推荐"},
    # 技术社区
    "CSDN": {"style": "技术博客风格，代码示例，详细步骤，解决方案", "filename_suffix": "_CSDN博客.md", "group": "技术社区"},
    "掘金": {"style": "技术文章风格，干货输出，有实践案例", "filename_suffix": "_掘金.md", "group": "技术社区"},
    "博客园": {"style": "技术博客风格，原创深度，代码示例", "filename_suffix": "_博客园.md", "group": "技术社区"},
    "思否": {"style": "技术问答风格，问题导向，解决方案清晰", "filename_suffix": "_思否.md", "group": "技术社区"},
    # 社交媒体
    "简书": {"style": "随笔风格，个人化表达，故事性强", "filename_suffix": "_简书.md", "group": "社交媒体"},
    "豆瓣": {"style": "评论/书评风格，有独立观点，文艺气息", "filename_suffix": "_豆瓣.md", "group": "社交媒体"},
    "企鹅号": {"style": "年轻化表达，贴近热点，互动引导", "filename_suffix": "_企鹅号.md", "group": "社交媒体"},
    # 资讯平台（风格相近，合并为一组）
    "头条号": {"style": "资讯风格，标题醒目，信息密度高，快速阅读", "filename_suffix": "_头条号.md", "group": "资讯平台"},
    "百家号": {"style": "科普风格，通俗易懂，适合大众阅读", "filename_suffix": "_百家号.md", "group": "资讯平台"},
    "搜狐号": {"style": "新闻稿风格，客观陈述，信息全面", "filename_suffix": "_搜狐号.md", "group": "资讯平台"},
    "网易号": {"style": "观点评论风格，有态度有分析", "filename_suffix": "_网易号.md", "group": "资讯平台"},
    "大鱼号": {"style": "视频/图文结合，娱乐性强", "filename_suffix": "_大鱼号.md", "group": "资讯平台"},
    "趣头条": {"style": "信息流风格，通俗易懂，接地气", "filename_suffix": "_趣头条.md", "group": "资讯平台"},
    "一点资讯": {"style": "深度解读风格，有独立分析", "filename_suffix": "_一点资讯.md", "group": "资讯平台"},
    "新浪看点": {"style": "热点追踪风格，时效性强", "filename_suffix": "_新浪看点.md", "group": "资讯平台"},
    "凤凰号": {"style": "深度评论风格，宏观视角", "filename_suffix": "_凤凰号.md", "group": "资讯平台"},
}

SUPPORTED_PLATFORMS = list(PLATFORM_CONFIG.keys())


def _get_effective_platform_config() -> dict[str, dict[str, Any]]:
    """返回当前生效的平台配置（动态配置优先，回退到默认 PLATFORM_CONFIG）"""
    cfg = ArticleService._platform_config
    if cfg is not None:
        return cfg
    return PLATFORM_CONFIG


def get_platform_style(platform: str) -> str:
    cfg = _get_effective_platform_config()
    return cfg.get(platform, {}).get("style", "专业内容风格，结构清晰，适合阅读")


def get_platform_suffix(platform: str) -> str:
    cfg = _get_effective_platform_config()
    return cfg.get(platform, {}).get("filename_suffix", ".md")


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def _validate_inputs(keyword: str, brand: str) -> None:
    """在调用 LLM 前校验关键词和品牌名称长度，不合法则抛出 ValidationError"""
    err = validate_input_length(keyword, "关键词", KEYWORD_MAX)
    if err:
        raise ValidationError(message=err, details={"field": "keyword", "max_length": KEYWORD_MAX})
    err = validate_input_length(brand, "品牌名称", BRAND_NAME_MAX)
    if err:
        raise ValidationError(message=err, details={"field": "brand", "max_length": BRAND_NAME_MAX})


class ArticleService:
    _platform_config: ClassVar[Optional[dict[str, dict[str, Any]]]] = None

    def __init__(self, db: AsyncSession):
        self._db = db
        self._llm = LLMService(db)

    # ---- 平台配置动态覆盖 ----

    @classmethod
    def set_platform_config(cls, cfg: Optional[dict[str, dict[str, Any]]]) -> None:
        """设置全局动态平台配置（启动时从数据库/模板加载后调用）；传 None 则恢复默认"""
        cls._platform_config = cfg

    @classmethod
    def update_platform_config(cls, config_dict: dict[str, dict[str, Any]]) -> None:
        """实例/类方法：用传入的配置字典覆盖当前平台配置（可在运行时调用）"""
        cls.set_platform_config(config_dict)

    # ---- 文章查询 ----

    async def get_articles(
        self, brand: str = "", platform: str = "", page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        query = select(Article)
        count_query = select(func.count(Article.id))
        if brand:
            query = query.where(Article.brand == brand)
            count_query = count_query.where(Article.brand == brand)
        if platform:
            query = query.where(Article.platform == platform)
            count_query = count_query.where(Article.platform == platform)
        total = (await self._db.execute(count_query)).scalar() or 0
        query = query.order_by(Article.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._db.execute(query)
        items = list(result.scalars().all())
        return {
            "items": items, "total": total, "page": page, "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    async def get_article(self, article_id: int) -> Optional[Article]:
        return await self._db.get(Article, article_id)

    async def search_articles(self, query: str, brand: str = "", limit: int = 20) -> list[Article]:
        """基于关键词和文件名的模糊搜索（LIKE），返回匹配的文章列表"""
        like_pattern = f"%{query}%"
        stmt = select(Article).where(
            or_(
                Article.keyword.like(like_pattern),
                Article.filename.like(like_pattern),
            )
        )
        if brand:
            stmt = stmt.where(Article.brand == brand)
        stmt = stmt.order_by(Article.created_at.desc()).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_original_content(self, article_id: int) -> Optional[str]:
        """返回文章版本 1（原始版本）的内容，用于恢复功能"""
        result = await self._db.execute(
            select(ArticleVersion).where(
                ArticleVersion.article_id == article_id,
                ArticleVersion.version_number == 1,
            )
        )
        ver = result.scalar_one_or_none()
        return ver.content if ver else None

    # ---- 文章写入 ----

    async def save_article(
        self, keyword: str, platform: str, content: str,
        filename: str = "", brand: str = "", source: str = "generated"
    ) -> Article:
        if not filename:
            suffix = get_platform_suffix(platform)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{sanitize_filename(keyword or 'content')}_{ts}{suffix}"
        obj = Article(keyword=keyword, platform=platform, content=content, filename=filename, brand=brand)
        self._db.add(obj)
        await self._db.flush()
        # 保存初始版本
        v = ArticleVersion(
            article_id=obj.id, version_number=1,
            content=content, source=source, note="初始版本"
        )
        self._db.add(v)
        await self._db.flush()
        return obj

    async def _save_version(self, article_id: int, content: str, source: str = "edited", note: str = "") -> ArticleVersion:
        """保存文章版本快照（自动递增版本号，保留最近10个版本）"""
        result = await self._db.execute(
            select(func.max(ArticleVersion.version_number)).where(ArticleVersion.article_id == article_id)
        )
        max_ver = result.scalar() or 0
        new_ver_num = max_ver + 1
        v = ArticleVersion(
            article_id=article_id, version_number=new_ver_num,
            content=content, source=source, note=note or f"版本 {new_ver_num}"
        )
        self._db.add(v)
        await self._db.flush()
        # 清理旧版本（保留最近10个）
        if new_ver_num > 10:
            old_result = await self._db.execute(
                select(ArticleVersion).where(
                    ArticleVersion.article_id == article_id,
                    ArticleVersion.version_number <= new_ver_num - 10
                )
            )
            for old_v in old_result.scalars().all():
                await self._db.delete(old_v)
        return v

    async def update_article(self, article_id: int, save_version: bool = True, source: str = "edited", note: str = "", **kwargs: Any) -> Optional[Article]:
        obj = await self._db.get(Article, article_id)
        if not obj:
            return None
        old_content = obj.content
        # Extract note from kwargs if passed there
        if "note" in kwargs:
            note = kwargs.pop("note") or note
        for k, v in kwargs.items():
            if hasattr(obj, k) and v is not None:
                setattr(obj, k, v)
        await self._db.flush()
        # 如果内容变化了，保存版本快照
        if save_version and kwargs.get("content") and kwargs["content"] != old_content:
            await self._save_version(article_id, kwargs["content"], source=source, note=note)
        return obj

    async def get_versions(self, article_id: int) -> list[ArticleVersion]:
        result = await self._db.execute(
            select(ArticleVersion)
            .where(ArticleVersion.article_id == article_id)
            .order_by(ArticleVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def get_version(self, version_id: int) -> Optional[ArticleVersion]:
        return await self._db.get(ArticleVersion, version_id)

    async def rollback_to_version(self, article_id: int, version_number: int) -> Optional[Article]:
        result = await self._db.execute(
            select(ArticleVersion).where(
                ArticleVersion.article_id == article_id,
                ArticleVersion.version_number == version_number
            )
        )
        ver = result.scalar_one_or_none()
        if not ver:
            return None
        obj = await self._db.get(Article, article_id)
        if not obj:
            return None
        obj.content = ver.content
        await self._db.flush()
        await self._save_version(article_id, ver.content, source="rollback", note=f"回滚到版本 {version_number}")
        return obj

    async def delete_article(self, article_id: int) -> bool:
        obj = await self._db.get(Article, article_id)
        if obj:
            await self._db.delete(obj)
            await self._db.flush()
            return True
        return False

    # ---- LLM 内容生成 ----

    async def generate_and_save(
        self,
        keyword: str, platform: str, brand: str, advantages: str,
        cfg: LLMConfig, knowledge_context: Optional[str] = None,
        word_count: int = 1500,
    ) -> Article:
        """非流式生成并保存文章（用于批量）"""
        _validate_inputs(keyword, brand)
        style_instr = f"风格：{get_platform_style(platform)}"
        knowledge_instr = KNOWLEDGE_CONTEXT_INSTRUCTION.format(knowledge_content=knowledge_context) if knowledge_context else ""
        prompt = ARTICLE_GENERATE_PROMPT.format(
            brand=brand, advantages=advantages, keyword=keyword, platform=platform,
            knowledge_context=knowledge_instr, word_count=word_count, style_instruction=style_instr,
        )
        result = await self._llm.invoke(prompt, cfg, record_cost=True, operation_type="generate", brand=brand, keyword=keyword, platform=platform)
        return await self.save_article(keyword, platform, result, brand=brand, source="generated")

    async def generate_content_stream(
        self,
        keyword: str,
        platform: str,
        brand: str,
        advantages: str,
        cfg: LLMConfig,
        knowledge_context: Optional[str] = None,
        word_count: int = 1500,
        style: str = "professional",  # ignored: style is derived from platform
    ) -> AsyncGenerator[str, None]:
        """单平台内容生成（流式）"""
        _validate_inputs(keyword, brand)
        style_instr = f"风格：{get_platform_style(platform)}"
        knowledge_instr = KNOWLEDGE_CONTEXT_INSTRUCTION.format(knowledge_content=knowledge_context) if knowledge_context else ""

        prompt = ARTICLE_GENERATE_PROMPT.format(
            brand=brand, advantages=advantages,
            keyword=keyword, platform=platform,
            knowledge_context=knowledge_instr,
            word_count=word_count,
            style_instruction=style_instr,
        )
        full: list[str] = []
        async for chunk in self._llm.stream(prompt, cfg):
            full.append(chunk)
            yield chunk

        content = "".join(full)
        if not content.strip():
            raise LLMError("模型返回了空内容", error_type="empty_response", retriable=True)
        await self.save_article(keyword, platform, content, brand=brand)

    async def batch_generate_stream(
        self,
        keywords: list[str],
        platforms: list[str],
        brand: str,
        advantages: str,
        cfg: LLMConfig,
        knowledge_context: Optional[str] = None,
        word_count: int = 1500,
        keyword_platforms: Optional[dict[str, list[str]]] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """批量多平台生成（带进度 SSE 事件）

        当 keyword_platforms 提供时（dict 映射 keyword -> platforms 列表），
        使用该映射生成任务对；否则使用 keywords × platforms 的笛卡尔积。
        """
        # 输入校验：品牌名称
        brand_err = validate_input_length(brand, "品牌名称", BRAND_NAME_MAX)
        if brand_err:
            raise ValidationError(message=brand_err, details={"field": "brand", "max_length": BRAND_NAME_MAX})

        # 收集所有需要校验的关键词（合并 keyword_platforms 中的 keys）
        all_keywords: list[str] = list(keywords)
        if keyword_platforms is not None:
            for kw in keyword_platforms:
                if kw not in all_keywords:
                    all_keywords.append(kw)
        for kw in all_keywords:
            kw_err = validate_input_length(kw, "关键词", KEYWORD_MAX)
            if kw_err:
                raise ValidationError(message=kw_err, details={"field": "keyword", "value": kw, "max_length": KEYWORD_MAX})

        # 构建任务列表：[(keyword, platform), ...]
        if keyword_platforms is not None:
            tasks: list[tuple[str, str]] = []
            for kw, plats in keyword_platforms.items():
                for plat in plats:
                    tasks.append((kw, plat))
        else:
            tasks = [(kw, plat) for kw in keywords for plat in platforms]

        total = len(tasks)
        done = 0
        articles: list[dict] = []
        errors: list[dict] = []

        yield {"event": "start", "data": {"total": total, "keywords": keywords, "platforms": platforms}}

        for kw, plat in tasks:
            done += 1
            progress = done / total * 100 if total > 0 else 100.0
            yield {"event": "progress", "data": {
                "progress": round(progress, 1), "current": done, "total": total,
                "keyword": kw, "platform": plat,
                "message": f"正在生成 [{plat}] {kw}..."
            }}

            try:
                style_instr = f"风格：{get_platform_style(plat)}"
                knowledge_instr = KNOWLEDGE_CONTEXT_INSTRUCTION.format(knowledge_content=knowledge_context) if knowledge_context else ""
                prompt = ARTICLE_GENERATE_PROMPT.format(
                    brand=brand, advantages=advantages,
                    keyword=kw, platform=plat,
                    knowledge_context=knowledge_instr,
                    word_count=word_count, style_instruction=style_instr,
                )
                chunks: list[str] = []
                async for chunk in self._llm.stream(prompt, cfg):
                    chunks.append(chunk)
                content = "".join(chunks)
                if not content.strip():
                    raise LLMError("模型返回了空内容", error_type="empty_response", retriable=True)
                art = await self.save_article(kw, plat, content, brand=brand)
                articles.append({"id": art.id, "keyword": kw, "platform": plat, "filename": art.filename})
                yield {"event": "article_done", "data": {"id": art.id, "keyword": kw, "platform": plat, "filename": art.filename}}
            except Exception as e:
                logger.error("Batch generate failed for %s/%s: %s", kw, plat, e)
                error_type = getattr(e, "error_type", e.__class__.__name__) if isinstance(e, LLMError) else e.__class__.__name__
                error_info = {
                    "keyword": kw,
                    "platform": plat,
                    "error": str(e),
                    "error_type": error_type,
                }
                errors.append(error_info)
                yield {"event": "article_error", "data": error_info}

        yield {
            "event": "complete",
            "data": {
                "total_articles": len(articles),
                "articles": articles,
                "success_count": len(articles),
                "failed_count": len(errors),
                "errors": errors,
            },
        }

    # ---- 多模态 ----

    async def generate_multimodal(
        self, article_id: int, cfg: LLMConfig,
        gen_image: bool = True, gen_video: bool = False,
    ) -> AsyncGenerator[str, None]:
        """生成多模态描述（流式）"""
        article = await self.get_article(article_id)
        if not article or not article.content:
            raise LLMError("文章不存在或内容为空")

        if gen_image:
            prompt = MULTIMODAL_IMAGE_DESC_PROMPT.format(content=article.content[:3000])
            img_chunks: list[str] = []
            async for chunk in self._llm.stream(prompt, cfg):
                img_chunks.append(chunk)
                yield chunk
            img_result = "".join(img_chunks)
        else:
            img_result = ""

        video_result = ""
        if gen_video:
            prompt = MULTIMODAL_VIDEO_SCRIPT_PROMPT.format(
                content=article.content[:3000], brand=article.brand or ""
            )
            vid_chunks: list[str] = []
            async for chunk in self._llm.stream(prompt, cfg):
                vid_chunks.append(chunk)
                yield chunk
            video_result = "".join(vid_chunks)

        # 保存多模态描述
        multimodal_data = json.dumps({
            "image_descriptions": img_result,
            "video_script": video_result,
        }, ensure_ascii=False)
        await self.update_article(article_id, multimodal=multimodal_data)

    # ---- 下载 ----

    async def download_batch_zip(self, article_ids: list[int]) -> bytes:
        """批量下载为 ZIP"""
        query = select(Article).where(Article.id.in_(article_ids)) if article_ids else select(Article)
        result = await self._db.execute(query)
        articles = result.scalars().all()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            used_names: set[str] = set()
            for art in articles:
                fname = art.filename or f"article_{art.id}.md"
                # 处理同名文件
                base, ext = fname.rsplit(".", 1) if "." in fname else (fname, "md")
                final_name = fname
                counter = 1
                while final_name in used_names:
                    final_name = f"{base}_{counter}.{ext}"
                    counter += 1
                used_names.add(final_name)
                content = art.content or ""
                zf.writestr(final_name, content.encode("utf-8"))
        return buf.getvalue()

    # ---- 平台信息（使用动态配置）----

    def get_supported_platforms(self) -> list[dict[str, Any]]:
        cfg = _get_effective_platform_config()
        return [{"key": k, "name": k, "style": v["style"], "group": v.get("group", "其他")} for k, v in cfg.items()]

    def get_platform_groups(self) -> list[dict[str, Any]]:
        """返回平台分组（推荐/常用/全部）"""
        cfg = _get_effective_platform_config()
        groups: dict[str, list[str]] = {"推荐": [], "技术社区": [], "社交媒体": [], "资讯平台": [], "其他": []}
        for k, v in cfg.items():
            g = v.get("group", "其他")
            groups.setdefault(g, []).append(k)
        return [{"group": g, "platforms": ps} for g, ps in groups.items() if ps]
