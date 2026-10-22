"""内容优化服务 - 从 eeat_enhancer/fact_density_enhancer/schema_generator/content_uniqueness/content_metrics/technical_config_generator/optimization_techniques 迁移"""
from __future__ import annotations

import json
import re
from typing import Any, AsyncGenerator, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.article import Article
from app.models.article_version import ArticleVersion
from app.models.optimization import Optimization
from app.prompts.optimization_prompts import (
    EEAT_ENHANCE_PROMPT,
    FACT_DENSITY_ENHANCE_PROMPT,
    SCHEMA_GENERATE_PROMPT,
    SEMANTIC_RICHNESS_ENHANCE_PROMPT,
)
from app.services.llm_service import LLMService, LLMConfig

logger = get_logger(__name__)


# ---- 规则指标分析（纯逻辑，从 content_metrics.py 迁移） ----

def analyze_metrics(content: str, brand: str = "") -> dict[str, Any]:
    """基于规则的内容指标分析（不调用LLM）"""
    word_count = len(content)
    paragraphs = [p for p in content.split("\n\n") if p.strip()]
    paragraph_count = len(paragraphs)
    headings = len(re.findall(r"^#{1,6}\s+", content, re.MULTILINE))
    lists = len(re.findall(r"^[-*•]\s+|^\d+[\.\)]\s+", content, re.MULTILINE))
    brand_count = len(re.findall(re.escape(brand), content, re.IGNORECASE)) if brand else 0
    has_faq = bool(re.search(r"FAQ|常见问题|Q[：:]|问[：:]", content, re.IGNORECASE))
    has_citations = bool(re.search(r"https?://|[\[\(]\d+[\]\)]|引用|来源|参考", content))
    avg_para_len = word_count / paragraph_count if paragraph_count > 0 else 0

    # 简易可读性评分（基于段落长度和列表比例）
    readability = 0.0
    if avg_para_len > 0:
        length_score = max(0, min(1, 300 / avg_para_len)) if avg_para_len > 0 else 0
        list_ratio = lists / paragraph_count if paragraph_count > 0 else 0
        readability = min(100, (length_score * 40) + (list_ratio * 30) + (20 if headings > 2 else headings * 10) + (10 if has_faq else 0))

    # 简易关键词密度估算
    clean = re.sub(r"[#\-\*\[\]\(\)>]", " ", content)
    total_chars = len(clean.replace(" ", ""))
    keyword_density = (brand_count / total_chars * 1000) if (brand_count > 0 and total_chars > 0) else 0

    return {
        "word_count": word_count,
        "paragraph_count": paragraph_count,
        "heading_count": headings,
        "list_count": lists,
        "brand_count": brand_count,
        "keyword_density": round(keyword_density, 2),
        "readability_score": round(readability, 1),
        "has_faq": has_faq,
        "has_citations": has_citations,
        "avg_paragraph_length": round(avg_para_len, 1),
    }


# ---- 内容独特性检测（纯逻辑，从 content_uniqueness.py 迁移） ----

def check_uniqueness(content: str, reference_contents: list[str]) -> dict[str, Any]:
    """基于 n-gram 的内容独特性检测"""
    def get_ngrams(text: str, n: int = 4) -> set[str]:
        clean = re.sub(r"\s+", "", text)
        return {clean[i:i + n] for i in range(max(0, len(clean) - n + 1))}

    content_ngrams = get_ngrams(content)
    if not content_ngrams:
        return {
            "uniqueness_score": 100.0,
            "duplicate_segments": [],
            "suggestions": ["内容为空或过短"],
        }

    duplicate_segments: list[str] = []
    max_overlap_ratio = 0.0

    for ref in reference_contents:
        ref_ngrams = get_ngrams(ref)
        if not ref_ngrams:
            continue
        overlap = content_ngrams & ref_ngrams
        ratio = len(overlap) / len(content_ngrams) if content_ngrams else 0
        max_overlap_ratio = max(max_overlap_ratio, ratio)
        if ratio > 0.1 and len(overlap) > 0:
            # 提取重复片段示例
            samples = list(overlap)[:3]
            duplicate_segments.extend(samples)

    uniqueness_score = max(0, 100 - max_overlap_ratio * 100)

    suggestions = []
    if uniqueness_score < 70:
        suggestions.append("内容重复度较高，建议大幅改写")
    if uniqueness_score < 90:
        suggestions.append("部分内容与已有内容相似，建议增加原创分析")
    if not suggestions:
        suggestions.append("内容独特性良好")

    return {
        "uniqueness_score": round(uniqueness_score, 1),
        "duplicate_segments": duplicate_segments[:10],
        "suggestions": suggestions,
    }


# ---- 技术配置生成（纯逻辑模板，从 technical_config_generator.py 迁移） ----

def generate_tech_config(brand: str, website_url: str, keywords: list[str], platforms: list[str]) -> dict[str, str]:
    """生成 robots.txt / sitemap.xml / meta tags 等技术配置"""
    kw_str = ", ".join(keywords[:10])

    robots_txt = f"""# robots.txt for {brand}
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/

# Sitemap
Sitemap: {website_url}/sitemap.xml
"""

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{website_url}/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{website_url}/blog</loc>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>"""

    meta_tags = f"""<!-- Primary Meta Tags -->
<title>{brand} - 官方网站</title>
<meta name="title" content="{brand}">
<meta name="description" content="{brand} - {', '.join(keywords[:5])}">
<meta name="keywords" content="{kw_str}">

<!-- Open Graph / Facebook -->
<meta property="og:type" content="website">
<meta property="og:title" content="{brand}">
<meta property="og:description" content="{brand}">

<!-- Twitter -->
<meta property="twitter:card" content="summary_large_image">
<meta property="twitter:title" content="{brand}">"""

    structured_data = json.dumps({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": brand,
        "url": website_url,
    }, ensure_ascii=False, indent=2)

    return {
        "robots_txt": robots_txt,
        "sitemap_xml": sitemap_xml,
        "meta_tags": meta_tags,
        "structured_data": structured_data,
    }


# ---- GEO 优化技巧（从 optimization_techniques.py 迁移） ----

GEO_TECHNIQUES: list[dict[str, str]] = [
    {"name": "结论先行", "category": "结构", "description": "文章开头直接给出明确答案，让AI能立即提取品牌信息", "example": "直接回答：推荐XX品牌，原因如下..."},
    {"name": "AI答案块", "category": "结构", "description": "文章开头100字内放置150-200字确定性答案摘要，AI优先提取开头内容", "example": "首段直接回答用户问题，不含模糊词"},
    {"name": "结构化数据标记", "category": "技术", "description": "使用Schema.org标记内容，帮助AI理解内容类型和实体", "example": "添加Article/Product/FAQ等JSON-LD"},
    {"name": "统计数据引用", "category": "权威", "description": "包含具体数字和统计数据占位，提升内容可引用性", "example": "据统计，XX市场规模达XX亿元"},
    {"name": "FAQ 结尾", "category": "结构", "description": "文章末尾添加3-5个常见问题，匹配AI对话回答格式", "example": "Q: 哪个品牌最好？A: ..."},
    {"name": "品牌提及位置", "category": "品牌", "description": "品牌在文章前1/3处至少出现一次，结尾再提及一次", "example": "开篇引出→中段分析→结尾CTA"},
    {"name": "比较表格", "category": "结构", "description": "使用对比表格展示品牌优势，便于AI提取对比信息", "example": "Markdown表格对比各品牌特性"},
    {"name": "E-E-A-T信号", "category": "权威", "description": "添加作者信息、发布日期、引用来源，提升可信度", "example": "作者：XX专家，更新时间：2026年7月"},
    {"name": "长尾问句标题", "category": "关键词", "description": "使用口语化问句作为小标题，匹配AI搜索query", "example": "XX哪家好？如何选择XX？"},
    {"name": "语义关联词", "category": "关键词", "description": "核心关键词附近自然融入同义词、上位词、相关概念，增强语义匹配", "example": "CRM→客户关系管理软件、企业SaaS工具"},
    {"name": "引用前置", "category": "权威", "description": "引用来源和权威数据放在文章前1/3，AI对前部引用赋权更高", "example": "开篇即引用XX研究机构2026年数据"},
    {"name": "确定性语言", "category": "语言", "description": "避免模糊词（可能/也许/大概），用有条件的确定性表述代替", "example": "在XX场景下，效果提升40%（非：可能提升不少）"},
]


# ---- 优化服务（含LLM调用） ----

class OptimizationService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._llm = LLMService(db)

    async def get_optimizations(self, brand: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
        query = select(Optimization)
        count_query = select(func.count(Optimization.id))
        if brand:
            query = query.where(Optimization.brand == brand)
            count_query = count_query.where(Optimization.brand == brand)
        total = (await self._db.execute(count_query)).scalar() or 0
        query = query.order_by(Optimization.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._db.execute(query)
        items = list(result.scalars().all())
        return {
            "items": items, "total": total, "page": page, "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    async def _save_optimization(
        self, original: str, optimized: str, changes: str,
        opt_type: str, platform: str, brand: str, score: Optional[dict] = None,
        article_id: Optional[int] = None, keyword: str = "",
    ) -> Optimization:
        obj = Optimization(
            article_id=article_id,
            original_content=original,
            optimized_content=optimized,
            changes=changes,
            optimization_type=opt_type,
            platform=platform,
            brand=brand,
            keyword=keyword,
            applied=False,
            score_result=json.dumps(score, ensure_ascii=False) if score else None,
        )
        self._db.add(obj)
        await self._db.flush()
        return obj

    async def enhance_eeat(
        self, content: str, brand: str, advantages: str, platform: str, cfg: LLMConfig,
        knowledge_context: Optional[str] = None, article_id: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """E-E-A-T 增强（流式）"""
        kb_instr = f"【知识库参考内容】\n{knowledge_context}" if knowledge_context else ""
        prompt = EEAT_ENHANCE_PROMPT.format(
            content=content, brand=brand, advantages=advantages, platform=platform,
            knowledge_context=kb_instr,
        )
        full: list[str] = []
        try:
            async for chunk in self._llm.stream(prompt, cfg):
                full.append(chunk)
                yield chunk
        except Exception as e:
            logger.error("E-E-A-T enhance stream error: %s", e, exc_info=True)
            raise
        # 后处理：解析结果并保存（内容已全部流式输出，此处保存失败不应影响响应）
        try:
            result = "".join(full)
            # Split on last standalone "---" at the end, not on horizontal rules within content
            parts = result.rsplit("\n---\n", 1)
            if len(parts) < 2:
                # Fallback: try rsplit on "---" at the end
                parts = result.rstrip().rsplit("\n---", 1)
            opt_content = parts[0].strip()
            changes = parts[1].strip() if len(parts) > 1 else ""
            await self._save_optimization(content, opt_content, changes, "eeat", platform, brand, article_id=article_id)
            if article_id:
                await self._save_article_version(article_id, opt_content, "optimized_eeat", "E-E-A-T增强")
        except Exception as e:
            logger.warning("Failed to save E-E-A-T optimization result: %s", e, exc_info=True)

    async def enhance_fact_density(
        self, content: str, brand: str, platform: str, cfg: LLMConfig,
        knowledge_context: Optional[str] = None, article_id: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """事实密度增强（流式）"""
        kb_instr = f"【知识库参考内容】\n{knowledge_context}" if knowledge_context else ""
        prompt = FACT_DENSITY_ENHANCE_PROMPT.format(
            content=content, brand=brand, platform=platform, knowledge_context=kb_instr
        )
        full: list[str] = []
        try:
            async for chunk in self._llm.stream(prompt, cfg):
                full.append(chunk)
                yield chunk
        except Exception as e:
            logger.error("Fact density enhance stream error: %s", e, exc_info=True)
            raise
        # 后处理：解析结果并保存（内容已全部流式输出，此处保存失败不应影响响应）
        try:
            result = "".join(full)
            # Split on last standalone "---" at the end, not on horizontal rules within content
            parts = result.rsplit("\n---\n", 1)
            if len(parts) < 2:
                # Fallback: try rsplit on "---" at the end
                parts = result.rstrip().rsplit("\n---", 1)
            opt_content = parts[0].strip()
            changes = parts[1].strip() if len(parts) > 1 else ""
            await self._save_optimization(content, opt_content, changes, "fact_density", platform, brand, article_id=article_id)
            if article_id:
                await self._save_article_version(article_id, opt_content, "optimized_fact", "事实密度增强")
        except Exception as e:
            logger.warning("Failed to save fact density optimization result: %s", e, exc_info=True)

    async def enhance_semantic_richness(
        self, content: str, brand: str, keyword: str, platform: str, cfg: LLMConfig,
        knowledge_context: Optional[str] = None, article_id: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """语义丰富度增强（流式）- 同义词/上位词/相关概念/实体关系优化"""
        kb_instr = f"【知识库参考内容】\n{knowledge_context}" if knowledge_context else ""
        prompt = SEMANTIC_RICHNESS_ENHANCE_PROMPT.format(
            content=content, brand=brand, keyword=keyword, platform=platform,
            knowledge_context=kb_instr,
        )
        full: list[str] = []
        try:
            async for chunk in self._llm.stream(prompt, cfg):
                full.append(chunk)
                yield chunk
        except Exception as e:
            logger.error("Semantic richness enhance stream error: %s", e, exc_info=True)
            raise
        try:
            result = "".join(full)
            # Split on last standalone "---" at the end, not on horizontal rules within content
            parts = result.rsplit("\n---\n", 1)
            if len(parts) < 2:
                # Fallback: try rsplit on "---" at the end
                parts = result.rstrip().rsplit("\n---", 1)
            opt_content = parts[0].strip()
            changes = parts[1].strip() if len(parts) > 1 else ""
            await self._save_optimization(content, opt_content, changes, "semantic_richness", platform, brand, article_id=article_id, keyword=keyword)
            if article_id:
                await self._save_article_version(article_id, opt_content, "optimized_semantic", "语义丰富度增强")
        except Exception as e:
            logger.warning("Failed to save semantic richness optimization result: %s", e, exc_info=True)

    async def _save_article_version(self, article_id: int, content: str, source: str, note: str) -> None:
        """保存优化后的版本快照到 article_versions"""
        try:
            res = await self._db.execute(
                select(func.max(ArticleVersion.version_number)).where(ArticleVersion.article_id == article_id)
            )
            max_ver = res.scalar() or 0
            v = ArticleVersion(
                article_id=article_id, version_number=max_ver + 1,
                content=content, source=source, note=note
            )
            self._db.add(v)
            await self._db.flush()
        except Exception as e:
            logger.warning("Failed to save article version: %s", e, exc_info=True)

    async def apply_optimization(self, opt_id: int) -> dict[str, Any]:
        """将优化结果应用到关联文章（更新文章内容为优化后的版本）。

        - 优化记录不存在 -> NotFoundError
        - 优化记录未关联文章 -> ValidationError
        - optimized_content 为 None 或空 -> ValidationError（防止清空文章内容）
        - 关联文章不存在 -> NotFoundError
        - 已应用过 -> 直接返回 already_applied=True

        Returns:
            dict: {"article_id", "optimization_id", "applied", "already_applied"?}
        """
        from app.core.exceptions import NotFoundError, ValidationError

        opt = await self._db.get(Optimization, opt_id)
        if not opt:
            raise NotFoundError("优化记录不存在")
        if not opt.article_id:
            raise ValidationError("该优化记录未关联文章，无法应用")
        if opt.applied:
            return {
                "article_id": opt.article_id,
                "optimization_id": opt_id,
                "applied": True,
                "already_applied": True,
            }
        # 校验 optimized_content 不为 None/空，防止清空文章内容
        if opt.optimized_content is None or not str(opt.optimized_content).strip():
            raise ValidationError("该优化记录的优化内容为空，无法应用")
        article = await self._db.get(Article, opt.article_id)
        if not article:
            raise NotFoundError("关联文章不存在")
        article.content = opt.optimized_content
        opt.applied = True
        await self._db.flush()
        return {
            "article_id": opt.article_id,
            "optimization_id": opt_id,
            "applied": True,
        }

    async def get_original_content(self, article_id: int) -> Optional[str]:
        """获取文章原文（版本1的内容）。

        1. 查询 ArticleVersion 中 version_number=1 的记录，返回其 content
        2. 若 v1 不存在（旧数据无版本快照），回退到当前文章 content
        3. 若文章本身不存在，返回 None
        """
        # 先确认文章存在
        article = await self._db.get(Article, article_id)
        if article is None:
            return None
        # 查找 version_number=1 的快照
        res = await self._db.execute(
            select(ArticleVersion).where(
                ArticleVersion.article_id == article_id,
                ArticleVersion.version_number == 1,
            )
        )
        v1 = res.scalar_one_or_none()
        if v1 is not None:
            return v1.content
        # v1 快照不存在（可能是版本快照功能上线前创建的文章），回退到当前内容
        return article.content

    async def generate_schema(
        self, content: str, schema_type: str, brand: str, cfg: LLMConfig
    ) -> dict[str, str]:
        """生成 Schema.org JSON-LD"""
        prompt = SCHEMA_GENERATE_PROMPT.format(content=content, schema_type=schema_type, brand=brand)
        result = await self._llm.invoke(prompt, cfg, use_cache=True, record_cost=True, operation_type="schema", brand=brand)
        # 提取 ```json 块
        json_match = re.search(r"```json\s*\n?([\s\S]*?)\n?```", result)
        json_ld = json_match.group(1).strip() if json_match else result.strip()
        try:
            json.loads(json_ld)
        except json.JSONDecodeError:
            from app.core.exceptions import LLMError
            raise LLMError("生成的 Schema.org JSON-LD 格式无效，请重试", error_type="invalid_response", retriable=True)
        return {"json_ld": json_ld, "schema_type": schema_type}

    def get_techniques(self) -> list[dict[str, str]]:
        return GEO_TECHNIQUES
