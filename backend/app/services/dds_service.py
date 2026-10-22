"""DDS（Deep semantic depth / Data support / Authoritative source）三维评分服务"""
from __future__ import annotations

import json
import re
from typing import Any, AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.dds_score import DDSScore, OptimizationAction
from app.prompts.dds_prompts import DDS_SCORE_PROMPT
from app.services.llm_service import LLMService, LLMConfig
from app.utils.text_utils import extract_json

logger = get_logger(__name__)

# 维度权重
DEPTH_WEIGHT = 0.35
DATA_WEIGHT = 0.35
SOURCE_WEIGHT = 0.30

# 各维度对应的子项键名
DEPTH_SUB_KEYS = ("logic", "reasoning", "insight", "richness")
DATA_SUB_KEYS = ("data_points", "citations", "examples", "statistics")
SOURCE_SUB_KEYS = ("credentials", "expert_quotes", "references", "venue_quality")


def _compute_weighted_total(depth: float, data: float, source: float) -> float:
    """按权重计算总分，保留1位小数"""
    total = depth * DEPTH_WEIGHT + data * DATA_WEIGHT + source * SOURCE_WEIGHT
    return round(total, 1)


def _build_fallback_result(raw_text: str) -> dict[str, Any]:
    """解析失败时的兜底结果"""
    # 尝试从文本中提取总分数字
    total_match = re.search(r"总分[：:]\s*(\d+(?:\.\d+)?)", raw_text)
    total = float(total_match.group(1)) if total_match else 0.0
    dim_score = round(total / 3, 1) if total > 0 else 0.0
    sub = min(int(dim_score / 4), 25)
    return {
        "semantic_depth": {
            "score": dim_score,
            "sub_scores": {k: sub for k in DEPTH_SUB_KEYS},
            "details": "解析结果失败，请手动查看评分内容",
        },
        "data_support": {
            "score": dim_score,
            "sub_scores": {k: sub for k in DATA_SUB_KEYS},
            "details": "解析结果失败，请手动查看评分内容",
        },
        "authoritative_source": {
            "score": dim_score,
            "sub_scores": {k: sub for k in SOURCE_SUB_KEYS},
            "details": "解析结果失败，请手动查看评分内容",
        },
        "total_score": total,
        "improvements": ["请检查内容语义深度、数据支持和权威来源是否符合 GEO 原则"],
        "strengths": [],
    }


def _normalize_dimension(raw: Any, sub_keys: tuple[str, ...]) -> dict[str, Any]:
    """规范化单维度结果，确保字段完整且分数合法"""
    if not isinstance(raw, dict):
        raw = {}
    sub_raw = raw.get("sub_scores", {}) if isinstance(raw.get("sub_scores"), dict) else {}
    sub_scores: dict[str, int] = {}
    for key in sub_keys:
        try:
            val = int(sub_raw.get(key, 0))
        except (TypeError, ValueError):
            val = 0
        sub_scores[key] = max(0, min(val, 25))
    # 优先使用 LLM 返回的总分，否则由子项求和
    try:
        score = float(raw.get("score", sum(sub_scores.values())))
    except (TypeError, ValueError):
        score = float(sum(sub_scores.values()))
    score = max(0.0, min(score, 100.0))
    details = str(raw.get("details", ""))
    return {"score": score, "sub_scores": sub_scores, "details": details}


def get_dds_level(total_score: float) -> tuple[str, str]:
    """根据总分返回等级及颜色"""
    if total_score >= 90:
        return ("优秀", "#10B981")
    elif total_score >= 75:
        return ("良好", "#3B82F6")
    elif total_score >= 60:
        return ("中等", "#F59E0B")
    else:
        return ("需改进", "#EF4444")


class DDSService:
    """DDS 三维评分服务：支持流式 SSE 输出 + 数据库持久化"""

    def __init__(self, db: Optional[AsyncSession] = None):
        self._db = db
        self._llm = LLMService(db)

    # ------------------------------------------------------------------
    # 流式评分
    # ------------------------------------------------------------------

    async def score_content(
        self,
        content: str,
        brand: str,
        cfg: LLMConfig,
        article_id: Optional[int] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        DDS 三维评分（SSE 流式）。

        Yields 事件字典:
          - {event: "start",     data: {...}}
          - {event: "chunk",     data: {content: str}}
          - {event: "complete",  data: {result: DDSScoreResponse-like dict}}
          - {event: "error",     data: {error: str}}
        完成后自动保存 DDSScore 记录到数据库。
        """
        yield {"event": "start", "data": {"message": "开始 DDS 三维评分..."}}

        prompt = DDS_SCORE_PROMPT.format(content=content, brand=brand or "（未指定）")

        chunks: list[str] = []
        try:
            async for chunk in self._llm.stream(prompt, cfg):
                chunks.append(chunk)
                yield {"event": "chunk", "data": {"content": chunk}}
        except Exception as e:
            logger.error("DDS LLM stream failed: %s", e)
            yield {"event": "error", "data": {"error": f"LLM 调用失败: {e}"}}
            return

        full_text = "".join(chunks)
        logger.debug("DDS raw response length: %d", len(full_text))

        # 解析 JSON
        parsed = extract_json(full_text)
        if not isinstance(parsed, dict) or "semantic_depth" not in parsed:
            logger.warning("DDS JSON parse failed, using fallback. Raw (first 200): %s", full_text[:200])
            parsed = _build_fallback_result(full_text)

        # 规范化各维度
        depth_dim = _normalize_dimension(parsed.get("semantic_depth"), DEPTH_SUB_KEYS)
        data_dim = _normalize_dimension(parsed.get("data_support"), DATA_SUB_KEYS)
        source_dim = _normalize_dimension(parsed.get("authoritative_source"), SOURCE_SUB_KEYS)

        # 以子项求和后的规范化分数重新计算加权总分，保证一致性
        total_score = _compute_weighted_total(
            depth_dim["score"], data_dim["score"], source_dim["score"]
        )

        improvements = parsed.get("improvements", [])
        if not isinstance(improvements, list):
            improvements = []
        improvements = [str(x) for x in improvements]

        strengths = parsed.get("strengths", [])
        if not isinstance(strengths, list):
            strengths = []
        strengths = [str(x) for x in strengths]

        result: dict[str, Any] = {
            "brand": brand,
            "article_id": article_id,
            "semantic_depth": depth_dim,
            "data_support": data_dim,
            "authoritative_source": source_dim,
            "total_score": total_score,
            "improvements": improvements,
            "strengths": strengths,
        }

        # 保存到数据库
        saved_id: Optional[int] = None
        if self._db is not None:
            try:
                saved_id = await self._save_score_record(
                    brand=brand,
                    article_id=article_id,
                    depth_dim=depth_dim,
                    data_dim=data_dim,
                    source_dim=source_dim,
                    total_score=total_score,
                    improvements=improvements,
                    strengths=strengths,
                )
                result["id"] = saved_id
                logger.info("DDS score saved: id=%d total=%.1f brand=%s", saved_id, total_score, brand)
            except Exception as e:
                logger.error("Failed to save DDS score to DB: %s", e)
                yield {"event": "error", "data": {"error": f"评分结果保存失败: {e}"}}

        level, level_color = get_dds_level(total_score)
        result["level"] = level
        result["level_color"] = level_color

        yield {"event": "complete", "data": {"result": result}}

    # ------------------------------------------------------------------
    # 同步评分（非流式，直接返回解析结果，可选保存）
    # ------------------------------------------------------------------

    async def score_content_sync(
        self,
        content: str,
        brand: str,
        cfg: LLMConfig,
        article_id: Optional[int] = None,
        save: bool = True,
    ) -> dict[str, Any]:
        """
        DDS 三维评分（同步，返回完整 dict 结果）。
        与 score_content 逻辑一致，但不流式输出。
        """
        prompt = DDS_SCORE_PROMPT.format(content=content, brand=brand or "（未指定）")
        raw = await self._llm.invoke(
            prompt, cfg, use_cache=True, record_cost=True, operation_type="dds_score", brand=brand
        )

        parsed = extract_json(raw)
        if not isinstance(parsed, dict) or "semantic_depth" not in parsed:
            logger.warning("DDS sync JSON parse failed, using fallback.")
            parsed = _build_fallback_result(raw)

        depth_dim = _normalize_dimension(parsed.get("semantic_depth"), DEPTH_SUB_KEYS)
        data_dim = _normalize_dimension(parsed.get("data_support"), DATA_SUB_KEYS)
        source_dim = _normalize_dimension(parsed.get("authoritative_source"), SOURCE_SUB_KEYS)
        total_score = _compute_weighted_total(
            depth_dim["score"], data_dim["score"], source_dim["score"]
        )

        improvements = [str(x) for x in (parsed.get("improvements") or []) if isinstance(parsed.get("improvements"), list)]
        strengths = [str(x) for x in (parsed.get("strengths") or []) if isinstance(parsed.get("strengths"), list)]

        result: dict[str, Any] = {
            "brand": brand,
            "article_id": article_id,
            "semantic_depth": depth_dim,
            "data_support": data_dim,
            "authoritative_source": source_dim,
            "total_score": total_score,
            "improvements": improvements,
            "strengths": strengths,
        }

        if save and self._db is not None:
            try:
                saved_id = await self._save_score_record(
                    brand=brand,
                    article_id=article_id,
                    depth_dim=depth_dim,
                    data_dim=data_dim,
                    source_dim=source_dim,
                    total_score=total_score,
                    improvements=improvements,
                    strengths=strengths,
                )
                result["id"] = saved_id
            except Exception as e:
                logger.error("Failed to save DDS sync score: %s", e)

        level, level_color = get_dds_level(total_score)
        result["level"] = level
        result["level_color"] = level_color
        return result

    # ------------------------------------------------------------------
    # 优化操作记录（ROI 归因）
    # ------------------------------------------------------------------

    async def record_action(
        self,
        action_type: str,
        description: str = "",
        brand: str = "",
        article_id: Optional[int] = None,
        keyword: str = "",
        platform: str = "",
        score_before: Optional[float] = None,
        score_after: Optional[float] = None,
        mention_rate_at_action: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> OptimizationAction:
        """
        记录一次优化操作，用于 ROI 追踪。

        Parameters
        ----------
        action_type : str
            操作类型，如 eeat / fact_density / schema / keyword / article / other
        description : str
            操作内容描述
        brand : str
            目标品牌
        article_id : int | None
            关联文章 ID
        keyword : str
            目标关键词
        platform : str
            目标平台
        score_before : float | None
            操作前的评分（DDS 总分或其他评分）
        score_after : float | None
            操作后的评分
        mention_rate_at_action : float | None
            操作时的 AI 提及率
        metadata : dict | None
            附加元数据（序列化为 JSON 存储）

        Returns
        -------
        OptimizationAction
            已持久化的 ORM 对象（含 id）
        """
        if self._db is None:
            raise RuntimeError("DDSService 未初始化数据库会话，无法记录操作")

        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)

        action = OptimizationAction(
            action_type=action_type,
            description=description[:500] if description else "",
            brand=brand,
            article_id=article_id,
            keyword=keyword,
            platform=platform,
            score_before=score_before,
            score_after=score_after,
            mention_rate_at_action=mention_rate_at_action,
            metadata_json=metadata_json,
        )
        self._db.add(action)
        await self._db.flush()
        logger.info(
            "OptimizationAction recorded: id=%d type=%s brand=%s score=%.1f->%s",
            action.id,
            action_type,
            brand,
            score_before if score_before is not None else -1,
            f"{score_after}" if score_after is not None else "N/A",
        )
        return action

    # ------------------------------------------------------------------
    # 内部：保存评分记录
    # ------------------------------------------------------------------

    async def _save_score_record(
        self,
        brand: str,
        article_id: Optional[int],
        depth_dim: dict[str, Any],
        data_dim: dict[str, Any],
        source_dim: dict[str, Any],
        total_score: float,
        improvements: list[str],
        strengths: list[str],
    ) -> int:
        """将 DDS 评分结果写入 dds_scores 表，返回新记录 id。"""
        record = DDSScore(
            brand=brand,
            article_id=article_id,
            semantic_depth=depth_dim["score"],
            data_support=data_dim["score"],
            authoritative_source=source_dim["score"],
            total_score=total_score,
            depth_details=json.dumps(depth_dim, ensure_ascii=False),
            data_details=json.dumps(data_dim, ensure_ascii=False),
            source_details=json.dumps(source_dim, ensure_ascii=False),
            improvements=json.dumps(improvements, ensure_ascii=False),
            strengths=json.dumps(strengths, ensure_ascii=False),
        )
        self._db.add(record)
        await self._db.flush()
        return record.id  # type: ignore[return-value]
