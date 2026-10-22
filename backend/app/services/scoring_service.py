"""内容评分服务 - 从 content_scorer.py 迁移"""
from __future__ import annotations

import re
from typing import Any, AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.prompts.scoring_prompts import CONTENT_SCORING_PROMPT
from app.services.llm_service import LLMService, LLMConfig
from app.services.optimization_service import analyze_metrics
from app.utils.text_utils import extract_json

logger = get_logger(__name__)


def quick_assessment(content: str, brand: str = "") -> dict[str, Any]:
    """快速规则评估（不调用LLM）"""
    has_title = bool(re.search(r"^#+\s+|^标题|^##", content, re.MULTILINE))
    has_list = bool(re.search(r"[-*•]\s+|^\d+[\.\)]\s+", content, re.MULTILINE))
    has_faq = bool(re.search(r"FAQ|常见问题|Q[：:]|问[：:]", content, re.IGNORECASE))
    brand_count = len(re.findall(re.escape(brand), content, re.IGNORECASE)) if brand else 0
    word_count = len(content)

    quick_score = 0
    if has_title:
        quick_score += 5
    if has_list:
        quick_score += 5
    if has_faq:
        quick_score += 5
    if 2 <= brand_count <= 4:
        quick_score += 10
    elif brand_count > 4:
        quick_score += 5

    return {
        "has_title": has_title,
        "has_list": has_list,
        "has_faq": has_faq,
        "brand_count": brand_count,
        "word_count": word_count,
        "quick_score": min(quick_score, 30),
    }


def get_score_level(total_score: int) -> tuple[str, str]:
    if total_score >= 90:
        return ("优秀", "#10B981")
    elif total_score >= 75:
        return ("良好", "#3B82F6")
    elif total_score >= 60:
        return ("中等", "#F59E0B")
    else:
        return ("需改进", "#EF4444")


class ScoringService:
    def __init__(self, db: Optional[AsyncSession] = None):
        self._db = db
        self._llm = LLMService(db)

    async def score_content_stream(
        self, content: str, brand: str, advantages: str, platform: str, cfg: LLMConfig
    ) -> AsyncGenerator[str, None]:
        """LLM 4维度评分（流式返回）"""
        prompt = CONTENT_SCORING_PROMPT.format(
            content=content, brand=brand, advantages=advantages, platform=platform
        )
        async for chunk in self._llm.stream(prompt, cfg):
            yield chunk

    async def score_content(
        self, content: str, brand: str, advantages: str, platform: str, cfg: LLMConfig
    ) -> dict[str, Any]:
        """LLM 4维度评分（同步返回完整结果）"""
        prompt = CONTENT_SCORING_PROMPT.format(
            content=content, brand=brand, advantages=advantages, platform=platform
        )
        result = await self._llm.invoke(
            prompt, cfg, use_cache=True, record_cost=True, operation_type="score", brand=brand, platform=platform
        )
        parsed = extract_json(result)
        if isinstance(parsed, dict) and "scores" in parsed:
            return parsed

        # 备用：尝试从文本提取总分
        total_match = re.search(r"总分[：:]\s*(\d+(?:\.\d+)?)", result)
        total = float(total_match.group(1)) if total_match else 0
        avg = total / 4 if total > 0 else 0
        return {
            "scores": {
                "structure": avg, "brand_mention": avg,
                "authority": avg, "citations": avg, "total": total,
            },
            "details": {
                "structure": "解析结果失败，手动查看评分内容",
                "brand_mention": "", "authority": "", "citations": "",
            },
            "improvements": ["请检查内容是否符合 GEO 原则"],
            "strengths": [],
        }

    def analyze_metrics(self, content: str, brand: str = "") -> dict[str, Any]:
        return analyze_metrics(content, brand)
