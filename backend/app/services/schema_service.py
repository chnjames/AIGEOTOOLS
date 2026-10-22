"""结构化数据增强服务 - Schema.org JSON-LD 生成与验证"""
from __future__ import annotations
import json
import re
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.llm_service import LLMService, LLMConfig
from app.utils.text_utils import extract_json

logger = get_logger(__name__)

SUPPORTED_SCHEMA_TYPES = {
    "Article": {
        "required": ["headline", "author", "datePublished"],
        "description": "通用文章、博客帖子",
    },
    "FAQPage": {
        "required": ["mainEntity"],
        "description": "常见问题页面",
    },
    "HowTo": {
        "required": ["name", "step"],
        "description": "教程、操作指南",
    },
    "Product": {
        "required": ["name"],
        "description": "产品页面",
    },
    "Organization": {
        "required": ["name"],
        "description": "组织/品牌信息",
    },
    "Review": {
        "required": ["itemReviewed", "reviewRating"],
        "description": "评价/评论",
    },
    "BreadcrumbList": {
        "required": ["itemListElement"],
        "description": "面包屑导航",
    },
    "WebPage": {
        "required": ["name"],
        "description": "网页元数据",
    },
}


class SchemaService:
    """结构化数据服务"""

    def __init__(self, db: AsyncSession):
        self._db = db
        self._llm = LLMService(db)

    async def generate_schema(
        self, content: str, schema_type: str, brand: str = "",
        cfg: Optional[LLMConfig] = None,
    ) -> dict[str, Any]:
        """生成指定类型的 JSON-LD Schema"""
        from app.prompts.optimization_prompts import SCHEMA_GENERATE_PROMPT
        prompt = SCHEMA_GENERATE_PROMPT.format(
            content=content[:3000], schema_type=schema_type, brand=brand,
        )
        if cfg is None:
            from app.core.exceptions import ConfigError
            raise ConfigError("LLM 配置未初始化，请先在设置中配置模型和 API Key")
        raw = await self._llm.invoke(prompt, cfg, record_cost=True, operation_type="schema", brand=brand)
        parsed = extract_json(raw)
        if not parsed:
            # Fallback minimal schema
            parsed = self._generate_minimal_schema(schema_type, content, brand)
        json_ld = {
            "@context": "https://schema.org",
            "@type": schema_type,
            **(parsed if isinstance(parsed, dict) else {}),
        }
        return {
            "schema_type": schema_type,
            "json_ld": json.dumps(json_ld, ensure_ascii=False, indent=2),
            "json_ld_raw": json_ld,
        }

    def validate_schema(self, json_ld_str: str, schema_type: str = "") -> dict[str, Any]:
        """验证 JSON-LD 格式和必填字段"""
        errors: list[str] = []
        warnings: list[str] = []

        # JSON 语法检查
        try:
            data = json.loads(json_ld_str) if isinstance(json_ld_str, str) else json_ld_str
        except json.JSONDecodeError as e:
            return {"valid": False, "errors": [f"JSON 语法错误: {e}"], "warnings": [], "score": 0}

        # @context 检查
        if "@context" not in data:
            errors.append("缺少 @context 字段（应为 https://schema.org）")
        elif data["@context"] != "https://schema.org":
            warnings.append(f"@context 建议使用 https://schema.org，当前: {data['@context']}")

        # @type 检查
        detected_type = data.get("@type", schema_type)
        if not detected_type:
            errors.append("缺少 @type 字段")

        # 必填字段检查
        type_config = SUPPORTED_SCHEMA_TYPES.get(detected_type or schema_type, {})
        required = type_config.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"缺少必填字段: {field}")

        # Google Rich Results 最佳实践检查
        if detected_type == "FAQPage":
            entities = data.get("mainEntity", [])
            if isinstance(entities, list) and len(entities) == 0:
                warnings.append("FAQPage 建议至少包含一个问题")
            for entity in entities if isinstance(entities, list) else []:
                if isinstance(entity, dict):
                    if "acceptedAnswer" not in entity:
                        errors.append("FAQ 条目缺少 acceptedAnswer 字段")

        if detected_type == "Article":
            if "image" not in data:
                warnings.append("建议添加 image 字段以获得更好的富媒体展示")
            if "publisher" not in data:
                warnings.append("建议添加 publisher 字段（发布者信息）")

        score = max(0, 100 - len(errors) * 20 - len(warnings) * 5)
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "score": score,
            "detected_type": detected_type,
        }

    def recommend_schema_types(self, content: str) -> list[dict[str, Any]]:
        """根据内容推荐最适合的 Schema 类型"""
        recommendations = []
        content_lower = content.lower()

        # FAQ 检测
        if re.search(r"(faq|常见问题|q[：:]|问[：:]|faq)", content_lower) or content.count("?") > 3:
            recommendations.append({
                "type": "FAQPage",
                "confidence": 0.85,
                "reason": "内容中包含多个问题/问答对",
            })

        # HowTo 检测
        if re.search(r"(步骤|step|如何|怎么|教程|指南)", content_lower) or re.search(r"^\s*\d+[\.\)]", content, re.MULTILINE):
            recommendations.append({
                "type": "HowTo",
                "confidence": 0.8,
                "reason": "内容包含步骤说明或操作教程",
            })

        # Product 检测
        if re.search(r"(价格|购买|产品|规格|参数|￥|¥|\\$)", content_lower):
            recommendations.append({
                "type": "Product",
                "confidence": 0.7,
                "reason": "内容包含产品相关信息（价格、规格等）",
            })

        # 文章
        recommendations.append({
            "type": "Article",
            "confidence": 0.9,
            "reason": "通用文章类型，适用于大多数内容",
        })

        # Organization (如果包含品牌信息)
        if re.search(r"(关于我们|公司简介|品牌介绍|about us)", content_lower):
            recommendations.append({
                "type": "Organization",
                "confidence": 0.75,
                "reason": "内容包含组织/品牌介绍信息",
            })

        return sorted(recommendations, key=lambda x: x["confidence"], reverse=True)

    def _generate_minimal_schema(self, schema_type: str, content: str, brand: str) -> dict:
        """生成最小化 Schema（LLM 失败时的fallback）"""
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else (brand or "Untitled")
        base = {"headline": title, "name": title}
        if schema_type == "FAQPage":
            questions = re.findall(r"(?:^|\n)\s*(?:Q[：:]|问[：:])\s*(.+?)(?=\n\s*(?:A[：:]|答[：:])|\n\n|$)", content)
            answers = re.findall(r"(?:^|\n)\s*(?:A[：:]|答[：:])\s*(.+?)(?=\n\s*(?:Q[：:]|问[：:])|\n\n|$)", content, re.DOTALL)
            main_entity = []
            for i, q in enumerate(questions[:10]):
                ans = answers[i].strip() if i < len(answers) else ""
                main_entity.append({
                    "@type": "Question",
                    "name": q.strip(),
                    "acceptedAnswer": {"@type": "Answer", "text": ans[:500]},
                })
            return {"mainEntity": main_entity}
        return base

    @staticmethod
    def get_supported_types() -> list[dict[str, str]]:
        return [
            {"type": k, "description": v["description"], "required": v["required"]}
            for k, v in SUPPORTED_SCHEMA_TYPES.items()
        ]
