"""ROI 归因分析服务 - 优化动作与效果归因"""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from typing import Any, Optional
from sqlalchemy import select, func, desc, Integer, cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.dds_score import DDSScore, OptimizationAction
from app.models.verify_result import VerifyResult
from app.models.api_call import ApiCall as ApiCallModel

logger = get_logger(__name__)


class AttributionService:
    """ROI 归因分析"""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def record_action(
        self, action_type: str, description: str = "", brand: str = "",
        article_id: Optional[int] = None, keyword: str = "", platform: str = "",
        score_before: Optional[float] = None, score_after: Optional[float] = None,
        metadata: Optional[dict] = None,
    ) -> OptimizationAction:
        """记录一次优化操作"""
        # 获取当前提及率
        mention_rate = await self._get_current_mention_rate(brand)
        action = OptimizationAction(
            action_type=action_type, description=description, brand=brand,
            article_id=article_id, keyword=keyword, platform=platform,
            score_before=score_before, score_after=score_after,
            mention_rate_at_action=mention_rate,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
        self._db.add(action)
        await self._db.flush()
        await self._db.refresh(action)
        return action

    async def get_roi_overview(self, brand: str = "", days: int = 30) -> dict[str, Any]:
        """ROI 概览仪表盘数据"""
        since = datetime.utcnow() - timedelta(days=days)

        # 总优化动作数
        action_stmt = select(func.count(OptimizationAction.id)).where(
            OptimizationAction.created_at >= since
        )
        if brand:
            action_stmt = action_stmt.where(OptimizationAction.brand == brand)
        total_actions = (await self._db.execute(action_stmt)).scalar() or 0

        # 按类型统计
        type_stmt = select(
            OptimizationAction.action_type,
            func.count(OptimizationAction.id),
        ).where(OptimizationAction.created_at >= since)
        if brand:
            type_stmt = type_stmt.where(OptimizationAction.brand == brand)
        type_stmt = type_stmt.group_by(OptimizationAction.action_type)
        type_counts = {row[0]: row[1] for row in (await self._db.execute(type_stmt)).all()}

        # 总费用
        cost_stmt = select(func.coalesce(func.sum(ApiCallModel.cost_cny), 0.0)).where(
            ApiCallModel.created_at >= since
        )
        if brand:
            cost_stmt = cost_stmt.where(ApiCallModel.brand == brand)
        total_cost = (await self._db.execute(cost_stmt)).scalar() or 0.0

        # 提及率变化
        mention_trend = await self._get_mention_trend(brand, days)
        current_rate = mention_trend[-1]["rate"] if mention_trend else 0
        start_rate = mention_trend[0]["rate"] if mention_trend else 0
        rate_change = current_rate - start_rate

        # 平均分数变化
        score_change = await self._get_score_trend(brand, days)

        return {
            "total_actions": total_actions,
            "actions_by_type": type_counts,
            "total_cost_cny": round(total_cost, 4),
            "current_mention_rate": current_rate,
            "mention_rate_change": round(rate_change, 4),
            "mention_rate_change_pct": round(rate_change * 100, 1) if start_rate > 0 else 0,
            "avg_score_change": round(score_change, 2),
            "cost_per_action": round(total_cost / total_actions, 4) if total_actions > 0 else 0,
            "trend_days": days,
        }

    async def get_action_effect_ranking(self, brand: str = "", days: int = 30, limit: int = 10) -> list[dict]:
        """优化动作效果排名"""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = select(OptimizationAction).where(
            OptimizationAction.created_at >= since
        )
        if brand:
            stmt = stmt.where(OptimizationAction.brand == brand)
        stmt = stmt.order_by(desc(OptimizationAction.created_at)).limit(limit)
        actions = (await self._db.execute(stmt)).scalars().all()

        results = []
        for a in actions:
            score_delta = None
            if a.score_before is not None and a.score_after is not None:
                score_delta = a.score_after - a.score_before
            results.append({
                "id": a.id,
                "action_type": a.action_type,
                "description": a.description,
                "platform": a.platform,
                "keyword": a.keyword,
                "score_before": a.score_before,
                "score_after": a.score_after,
                "score_delta": score_delta,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

        # Sort by score delta descending (best first)
        results.sort(key=lambda x: x["score_delta"] if x["score_delta"] is not None else -999, reverse=True)
        return results[:limit]

    async def get_optimization_timeline(self, brand: str = "", days: int = 30) -> dict:
        """优化时间线（用于图表标注）"""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = select(OptimizationAction).where(
            OptimizationAction.created_at >= since
        )
        if brand:
            stmt = stmt.where(OptimizationAction.brand == brand)
        stmt = stmt.order_by(OptimizationAction.created_at)
        actions = (await self._db.execute(stmt)).scalars().all()

        # Get mention rate trend
        mention_trend = await self._get_mention_trend(brand, days)

        # Annotations for chart
        annotations = []
        for a in actions:
            annotations.append({
                "date": a.created_at.strftime("%Y-%m-%d") if a.created_at else "",
                "type": a.action_type,
                "description": a.description or a.action_type,
            })

        return {
            "mention_trend": mention_trend,
            "annotations": annotations,
        }

    async def get_ab_comparison(self, brand: str = "") -> dict[str, Any]:
        """A/B 对比：优化前后引用率"""
        # Get first optimization action date as split point
        first_action_stmt = select(func.min(OptimizationAction.created_at))
        if brand:
            first_action_stmt = first_action_stmt.where(OptimizationAction.brand == brand)
        first_date = (await self._db.execute(first_action_stmt)).scalar()

        if not first_date:
            return {"has_data": False, "message": "暂无优化操作记录"}

        # Before
        before_mentions = await self._get_avg_mention_rate_range(brand, None, first_date)
        after_mentions = await self._get_avg_mention_rate_range(brand, first_date, None)

        # Score comparison
        before_score = await self._get_avg_score_range(brand, None, first_date)
        after_score = await self._get_avg_score_range(brand, first_date, None)

        return {
            "has_data": True,
            "split_date": first_date.isoformat(),
            "mention_rate_before": round(before_mentions, 4),
            "mention_rate_after": round(after_mentions, 4),
            "mention_rate_lift": round(after_mentions - before_mentions, 4),
            "avg_score_before": round(before_score, 2),
            "avg_score_after": round(after_score, 2),
            "score_lift": round(after_score - before_score, 2),
        }

    async def _get_current_mention_rate(self, brand: str) -> Optional[float]:
        stmt = select(
            func.count(VerifyResult.id),
            func.sum(cast(VerifyResult.is_mentioned, Integer)),
        )
        if brand:
            stmt = stmt.where(VerifyResult.brand == brand)
        result = (await self._db.execute(stmt)).first()
        if result and result[0] > 0:
            return (result[1] or 0) / result[0]
        return None

    async def _get_mention_trend(self, brand: str, days: int) -> list[dict]:
        since = datetime.utcnow() - timedelta(days=days)
        stmt = select(
            func.date(VerifyResult.created_at).label("d"),
            func.count(VerifyResult.id),
            func.sum(cast(VerifyResult.is_mentioned, Integer)),
        ).where(VerifyResult.created_at >= since)
        if brand:
            stmt = stmt.where(VerifyResult.brand == brand)
        stmt = stmt.group_by(func.date(VerifyResult.created_at)).order_by("d")
        rows = (await self._db.execute(stmt)).all()
        return [
            {"date": str(r[0]), "total": r[1], "mentioned": r[2] or 0,
             "rate": ((r[2] or 0) / r[1]) if r[1] > 0 else 0}
            for r in rows
        ]

    async def _get_score_trend(self, brand: str, days: int) -> float:
        since = datetime.utcnow() - timedelta(days=days)
        # Get earliest and latest average scores
        first_stmt = select(func.avg(DDSScore.total_score)).where(DDSScore.created_at >= since)
        if brand:
            first_stmt = first_stmt.where(DDSScore.brand == brand)
        avg = (await self._db.execute(first_stmt)).scalar()
        return avg or 0.0

    async def _get_avg_mention_rate_range(self, brand: str, start: Optional[datetime], end: Optional[datetime]) -> float:
        stmt = select(
            func.count(VerifyResult.id),
            func.sum(cast(VerifyResult.is_mentioned, Integer)),
        )
        if brand:
            stmt = stmt.where(VerifyResult.brand == brand)
        if start:
            stmt = stmt.where(VerifyResult.created_at >= start)
        if end:
            stmt = stmt.where(VerifyResult.created_at < end)
        r = (await self._db.execute(stmt)).first()
        if r and r[0] > 0:
            return (r[1] or 0) / r[0]
        return 0.0

    async def _get_avg_score_range(self, brand: str, start: Optional[datetime], end: Optional[datetime]) -> float:
        stmt = select(func.avg(DDSScore.total_score))
        if brand:
            stmt = stmt.where(DDSScore.brand == brand)
        if start:
            stmt = stmt.where(DDSScore.created_at >= start)
        if end:
            stmt = stmt.where(DDSScore.created_at < end)
        return (await self._db.execute(stmt)).scalar() or 0.0
