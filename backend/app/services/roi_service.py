"""ROI 分析服务 - 从原 roi_analyzer.py 迁移（纯计算逻辑，异步兼容）"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.api_call import ApiCall
from app.models.verify_result import VerifyResult

logger = get_logger(__name__)


class ROIService:
    """ROI 分析器 - 纯计算逻辑，无 UI 依赖"""

    def __init__(self, usd_to_cny_rate: float = 7.2, mention_value: float = 50.0):
        self.usd_to_cny_rate = usd_to_cny_rate
        self.mention_value = mention_value
        self.pricing_config: dict[str, Any] = {
            "DeepSeek": {"input": 0.00014, "output": 0.00028},
            "OpenAI (GPT)": {
                "gpt-4": {"input": 0.03, "output": 0.06},
                "gpt-4o": {"input": 0.005, "output": 0.015},
                "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
                "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            },
            "Tongyi (通义千问)": {
                "qwen-plus": {"input": 0.002, "output": 0.008},
                "qwen-max": {"input": 0.004, "output": 0.012},
                "qwen-turbo": {"input": 0.0008, "output": 0.002},
            },
            "Groq": {"input": 0.0, "output": 0.0},
            "Moonshot (Kimi)": {
                "moonshot-v1-8k": {"input": 0.012, "output": 0.012},
                "moonshot-v1-128k": {"input": 0.012, "output": 0.012},
                "moonshot-v1-32k": {"input": 0.024, "output": 0.024},
            },
            "豆包（字节跳动）": {
                "doubao-pro-4k": {"input": 0.0008, "output": 0.002},
                "doubao-lite-4k": {"input": 0.0004, "output": 0.001},
            },
            "文心一言（百度）": {
                "ernie-4.0": {"input": 0.012, "output": 0.012},
                "ernie-bot-turbo": {"input": 0.002, "output": 0.002},
                "ernie-3.5": {"input": 0.002, "output": 0.002},
            },
        }

    def calculate_cost(
        self, provider: str, model: str, input_tokens: int, output_tokens: int
    ) -> tuple[float, float]:
        pricing = self.pricing_config.get(provider, {})
        if not pricing:
            return 0.0, 0.0

        if "input" in pricing and "output" in pricing:
            input_price = pricing["input"]
            output_price = pricing["output"]
        elif model in pricing:
            mp = pricing[model]
            input_price = mp.get("input", 0.0)
            output_price = mp.get("output", 0.0)
        else:
            logger.warning("Unknown model %s for provider %s, using fallback pricing", model, provider)
            first_model = list(pricing.keys())[0]
            if isinstance(pricing[first_model], dict):
                input_price = pricing[first_model].get("input", 0.0)
                output_price = pricing[first_model].get("output", 0.0)
            else:
                input_price = pricing.get("input", 0.0)
                output_price = pricing.get("output", 0.0)

        cost_usd = (input_tokens / 1000.0 * input_price) + (output_tokens / 1000.0 * output_price)
        cost_cny = cost_usd * self.usd_to_cny_rate
        return cost_usd, cost_cny

    async def get_cost_report(
        self, db: AsyncSession, brand: str = "",
        date_from: Optional[date] = None, date_to: Optional[date] = None,
    ) -> dict[str, Any]:
        query = select(ApiCall)
        if brand:
            query = query.where(ApiCall.brand == brand)
        if date_from:
            query = query.where(ApiCall.created_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc))
        if date_to:
            query = query.where(ApiCall.created_at <= datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc))
        if not date_from and not date_to:
            cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            query = query.where(ApiCall.created_at >= cutoff)
        result = await db.execute(query)
        calls = result.scalars().all()

        if not calls:
            return {
                "total_cost_usd": 0.0, "total_cost_cny": 0.0,
                "total_tokens": 0, "total_calls": 0,
                "cost_by_operation": {}, "cost_by_provider": {},
                "cost_by_keyword": {}, "cost_by_platform": {}, "daily_costs": [],
            }

        total_cost_usd = sum(c.cost_usd for c in calls)
        total_cost_cny = sum(c.cost_cny for c in calls)
        total_tokens = sum(c.total_tokens for c in calls)

        cost_by_op: dict[str, dict] = {}
        cost_by_prov: dict[str, dict] = {}
        cost_by_kw: dict[str, dict] = {}
        cost_by_plat: dict[str, dict] = {}
        daily: dict[str, dict] = {}

        for c in calls:
            for d, key in [
                (cost_by_op, c.operation_type),
                (cost_by_prov, c.provider or "unknown"),
                (cost_by_plat, c.platform or "unknown"),
            ]:
                if key not in d:
                    d[key] = {"cost_usd": 0, "cost_cny": 0, "calls": 0, "tokens": 0}
                d[key]["cost_usd"] += c.cost_usd
                d[key]["cost_cny"] += c.cost_cny
                d[key]["calls"] += 1
                d[key]["tokens"] += c.total_tokens

            if c.keyword:
                if c.keyword not in cost_by_kw:
                    cost_by_kw[c.keyword] = {"cost_usd": 0, "cost_cny": 0, "calls": 0, "tokens": 0}
                cost_by_kw[c.keyword]["cost_usd"] += c.cost_usd
                cost_by_kw[c.keyword]["cost_cny"] += c.cost_cny
                cost_by_kw[c.keyword]["calls"] += 1
                cost_by_kw[c.keyword]["tokens"] += c.total_tokens

            if c.created_at:
                day = c.created_at.date().isoformat() if c.created_at else ""
                if day not in daily:
                    daily[day] = {"date": day, "cost_usd": 0, "cost_cny": 0, "calls": 0, "tokens": 0}
                daily[day]["cost_usd"] += c.cost_usd
                daily[day]["cost_cny"] += c.cost_cny
                daily[day]["calls"] += 1
                daily[day]["tokens"] += c.total_tokens

        daily_costs = sorted(daily.values(), key=lambda x: x["date"])

        return {
            "total_cost_usd": round(total_cost_usd, 6),
            "total_cost_cny": round(total_cost_cny, 4),
            "total_tokens": total_tokens,
            "total_calls": len(calls),
            "cost_by_operation": cost_by_op,
            "cost_by_provider": cost_by_prov,
            "cost_by_keyword": cost_by_kw,
            "cost_by_platform": cost_by_plat,
            "daily_costs": daily_costs,
        }

    async def get_mention_report(
        self, db: AsyncSession, brand: str = "",
        date_from: Optional[date] = None, date_to: Optional[date] = None,
    ) -> dict[str, Any]:
        query = select(VerifyResult)
        if brand:
            query = query.where(VerifyResult.brand == brand)
        if date_from:
            query = query.where(VerifyResult.created_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc))
        if date_to:
            query = query.where(VerifyResult.created_at <= datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc))
        result = await db.execute(query)
        results = result.scalars().all()

        total = len(results)
        mentioned = sum(1 for r in results if r.is_mentioned)
        mention_rate = mentioned / total if total > 0 else 0.0

        by_model: dict[str, dict] = {}
        for r in results:
            model = r.verify_model or "unknown"
            if model not in by_model:
                by_model[model] = {"total": 0, "mentioned": 0, "rate": 0.0}
            by_model[model]["total"] += 1
            if r.is_mentioned:
                by_model[model]["mentioned"] += 1
        for m in by_model.values():
            m["rate"] = m["mentioned"] / m["total"] if m["total"] > 0 else 0.0

        return {
            "total_verifications": total,
            "total_mentioned": mentioned,
            "mention_rate": round(mention_rate, 4),
            "mention_rate_by_model": by_model,
            "mention_trend": [],
            "top_mentioned_queries": [],
        }

    async def get_roi_report(
        self, db: AsyncSession, brand: str = "",
        date_from: Optional[date] = None, date_to: Optional[date] = None,
    ) -> dict[str, Any]:
        cost_report = await self.get_cost_report(db, brand, date_from, date_to)
        mention_report = await self.get_mention_report(db, brand, date_from, date_to)
        total_cost = cost_report["total_cost_cny"]
        total_mentions = mention_report["total_mentioned"]
        mention_value = self.mention_value
        estimated_value = total_mentions * mention_value
        roi_ratio = ((estimated_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

        suggestions = self._get_suggestions(cost_report)
        future = self._estimate_future(cost_report)

        return {
            "total_cost_cny": total_cost,
            "total_mentions": total_mentions,
            "estimated_value_cny": estimated_value,
            "roi_ratio": round(roi_ratio, 2),
            "keyword_roi": {},
            "suggestions": suggestions,
            "future_cost_estimate": future,
        }

    def _get_suggestions(self, cost_report: dict) -> list[dict]:
        suggestions = []
        total_cost = cost_report.get("total_cost_cny", 0)
        cost_by_prov = cost_report.get("cost_by_provider", {})
        if cost_by_prov and total_cost > 0:
            sorted_provs = sorted(cost_by_prov.items(), key=lambda x: x[1]["cost_cny"], reverse=True)
            top = sorted_provs[0]
            if top[1]["cost_cny"] > total_cost * 0.5:
                suggestions.append({
                    "type": "provider", "priority": "高",
                    "title": f"考虑使用更便宜的提供商替代 {top[0]}",
                    "description": f"{top[0]} 占总成本的 {top[1]['cost_cny']/total_cost*100:.1f}%",
                    "savings_estimate": top[1]["cost_cny"] * 0.3,
                })
        if not suggestions:
            suggestions.append({"type": "general", "priority": "低", "title": "成本控制良好", "description": "当前成本结构合理"})
        return suggestions

    def _estimate_future(self, cost_report: dict, days: int = 30) -> dict:
        daily = cost_report.get("daily_costs", [])
        if daily:
            avg_daily = sum(d["cost_cny"] for d in daily) / len(daily)
            confidence = "高" if len(daily) >= 7 else ("中" if len(daily) >= 3 else "低")
            return {
                "estimated_daily_cost_cny": round(avg_daily, 4),
                "estimated_total_cost_cny": round(avg_daily * days, 4),
                "confidence": confidence,
                "data_points": len(daily),
            }
        return {"estimated_daily_cost_cny": 0, "estimated_total_cost_cny": 0, "confidence": "低", "data_points": 0}

    async def get_kpi(self, db: AsyncSession, brand: str = "") -> dict[str, Any]:
        from app.models.keyword import Keyword
        from app.models.article import Article
        from app.models.optimization import Optimization

        async def count(model):
            q = select(func.count(model.id))
            if brand and hasattr(model, 'brand'):
                q = q.where(model.brand == brand)
            r = await db.execute(q)
            return r.scalar() or 0

        kws = await count(Keyword)
        arts = await count(Article)
        opts = await count(Optimization)
        cost_report = await self.get_cost_report(db, brand)
        mention_report = await self.get_mention_report(db, brand)

        return {
            "total_keywords": kws,
            "total_articles": arts,
            "total_optimizations": opts,
            "total_verifications": mention_report["total_verifications"],
            "total_cost_cny": cost_report["total_cost_cny"],
            "mention_rate": mention_report["mention_rate"],
        }
