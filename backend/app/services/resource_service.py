"""资源推荐服务 - 从 resource_recommender.py 迁移"""
from __future__ import annotations

GEO_QUERY_TEMPLATES: list[dict[str, str]] = [
    {
        "category": "直接推荐型",
        "templates": [
            "{keyword}哪家好？",
            "{keyword}哪个牌子靠谱？",
            "推荐一下好的{keyword}",
            "2026年{keyword}排行榜",
            "{keyword}选哪个比较好？",
        ],
    },
    {
        "category": "对比评测型",
        "templates": [
            "{keyword}和{competitor}哪个好？",
            "{keyword}对比{competitor}有什么优势？",
            "主流{keyword}品牌对比评测",
            "{keyword}各品牌优缺点分析",
        ],
    },
    {
        "category": "场景问题型",
        "templates": [
            "中小企业怎么选{keyword}？",
            "新手适合用什么{keyword}？",
            "{keyword}怎么用效果最好？",
            "选购{keyword}需要注意什么？",
            "{keyword}常见问题有哪些？",
        ],
    },
    {
        "category": "知识科普型",
        "templates": [
            "什么是{keyword}？",
            "{keyword}的原理是什么？",
            "{keyword}有什么功能和作用？",
            "如何判断{keyword}的好坏？",
            "{keyword}的核心指标有哪些？",
        ],
    },
]


def get_verify_query_templates(keyword: str = "", competitor: str = "") -> list[dict[str, list[str]]]:
    """获取 GEO 验证查询模板（替换 {keyword} 和 {competitor} 占位符）"""
    result = []
    for cat in GEO_QUERY_TEMPLATES:
        filled = []
        for tpl in cat["templates"]:
            filled.append(
                tpl.replace("{keyword}", keyword or "[关键词]")
                   .replace("{competitor}", competitor or "[竞品]")
            )
        result.append({"category": cat["category"], "templates": filled})
    return result


RESOURCES: list[dict[str, str]] = [
    {
        "title": "GEO 学术论文 (arxiv.org/abs/2311.09735)",
        "url": "https://arxiv.org/abs/2311.09735",
        "category": "学术研究",
        "description": "GEO（Generative Engine Optimization）原始研究论文，定义了GEO优化框架",
    },
    {
        "title": "Schema.org 官方文档",
        "url": "https://schema.org/docs/schemas.html",
        "category": "技术文档",
        "description": "Schema.org 结构化数据完整参考，用于JSON-LD生成",
    },
    {
        "title": "Google E-E-A-T 指南",
        "url": "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
        "category": "官方指南",
        "description": "Google搜索质量评估指南，E-E-A-T原则详解",
    },
    {
        "title": "LangChain 文档",
        "url": "https://python.langchain.com/",
        "category": "开发工具",
        "description": "LangChain LLM应用开发框架官方文档",
    },
    {
        "title": "DeepSeek API 文档",
        "url": "https://platform.deepseek.com/api-docs",
        "category": "API文档",
        "description": "DeepSeek大模型API使用指南",
    },
    {
        "title": "OpenAI API 文档",
        "url": "https://platform.openai.com/docs",
        "category": "API文档",
        "description": "OpenAI GPT系列API官方文档",
    },
    {
        "title": "内容营销学院 (CMI)",
        "url": "https://contentmarketinginstitute.com/",
        "category": "内容策略",
        "description": "内容营销策略和最佳实践资源",
    },
]


def get_resources(category: str = "") -> list[dict[str, str]]:
    if category:
        return [r for r in RESOURCES if r["category"] == category]
    return RESOURCES


def get_categories() -> list[str]:
    return sorted(set(r["category"] for r in RESOURCES))
