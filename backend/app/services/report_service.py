"""自动化营销报告生成服务"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.report import MarketingReport
from app.services.roi_service import ROIService
from app.services.attribution_service import AttributionService

logger = get_logger(__name__)


class ReportService:
    """营销报告服务"""

    def __init__(self, db: AsyncSession, mention_value: float = 50.0):
        self._db = db
        self._roi = ROIService(mention_value=mention_value)
        self._attr = AttributionService(db)

    async def generate_report(
        self, report_type: str = "weekly", brand: str = "",
        date_from: Optional[datetime] = None, date_to: Optional[datetime] = None,
        title: str = "",
    ) -> MarketingReport:
        """生成一份营销报告"""
        if date_to is None:
            date_to = datetime.utcnow()
        if date_from is None:
            days_map = {"daily": 1, "weekly": 7, "monthly": 30}
            days = days_map.get(report_type, 7)
            date_from = date_to - timedelta(days=days)

        if not title:
            type_labels = {"daily": "日报", "weekly": "周报", "monthly": "月报", "custom": "自定义报告"}
            title = f"GEO {type_labels.get(report_type, '报告')} - {date_from.strftime('%m/%d')}~{date_to.strftime('%m/%d')}"

        # 收集数据
        kpi_data = await self._collect_kpi(brand, date_from, date_to)
        mention_trend = await self._collect_mention_trend(brand, date_from, date_to)
        cost_data = await self._collect_costs(brand, date_from, date_to)
        opt_effect = await self._collect_optimization_effects(brand, date_from, date_to)
        competitor_data = await self._collect_competitor_data(brand, date_from, date_to)
        recommendations = await self._generate_recommendations(kpi_data, opt_effect)

        days = (date_to - date_from).days
        roi_data = await self._attr.get_roi_overview(brand, days=days)

        # 生成 Markdown
        md = self._render_markdown(title, kpi_data, mention_trend, cost_data, opt_effect, recommendations, date_from, date_to)

        # 保存报告
        share_token = uuid.uuid4().hex[:16]
        report = MarketingReport(
            title=title,
            report_type=report_type,
            brand=brand,
            date_from=date_from,
            date_to=date_to,
            summary=recommendations[0] if recommendations else "",
            kpi_data=json.dumps(kpi_data, ensure_ascii=False, default=str),
            mention_trend=json.dumps(mention_trend, ensure_ascii=False, default=str),
            cost_data=json.dumps(cost_data, ensure_ascii=False, default=str),
            optimization_effect=json.dumps(opt_effect, ensure_ascii=False, default=str),
            competitor_analysis=json.dumps(competitor_data, ensure_ascii=False),
            recommendations=json.dumps(recommendations, ensure_ascii=False),
            markdown_content=md,
            share_token=share_token,
        )
        self._db.add(report)
        await self._db.flush()
        await self._db.refresh(report)
        return report

    async def list_reports(self, brand: str = "", page: int = 1, page_size: int = 20) -> dict:
        count_stmt = select(func.count(MarketingReport.id))
        if brand:
            count_stmt = count_stmt.where(MarketingReport.brand == brand)
        total = (await self._db.execute(count_stmt)).scalar() or 0

        stmt = select(MarketingReport).order_by(desc(MarketingReport.created_at))
        if brand:
            stmt = stmt.where(MarketingReport.brand == brand)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = (await self._db.execute(stmt)).scalars().all()

        return {
            "items": [self._report_to_dict(r) for r in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_report(self, report_id: int) -> Optional[dict]:
        stmt = select(MarketingReport).where(MarketingReport.id == report_id)
        r = (await self._db.execute(stmt)).scalar_one_or_none()
        return self._report_to_dict(r) if r else None

    async def get_by_share_token(self, token: str) -> Optional[dict]:
        stmt = select(MarketingReport).where(MarketingReport.share_token == token)
        r = (await self._db.execute(stmt)).scalar_one_or_none()
        return self._report_to_dict(r, include_content=True) if r else None

    async def delete_report(self, report_id: int) -> bool:
        stmt = select(MarketingReport).where(MarketingReport.id == report_id)
        r = (await self._db.execute(stmt)).scalar_one_or_none()
        if r:
            await self._db.delete(r)
            await self._db.flush()
            return True
        return False

    async def _collect_competitor_data(self, brand: str, d_from: datetime, d_to: datetime) -> dict:
        """从已保存的验证结果中提取竞品分析数据"""
        from app.models.verify_result import VerifyResult
        stmt = select(VerifyResult).where(VerifyResult.created_at.between(d_from, d_to))
        if brand:
            stmt = stmt.where(VerifyResult.brand == brand)
        result = await self._db.execute(stmt)
        rows = result.scalars().all()
        if not rows:
            return {"total_queries": 0, "by_model": {}, "competitor_mentions": {}}
        by_model: dict[str, dict] = {}
        comp_mentions: dict[str, int] = {}
        for r in rows:
            model = r.verify_model or "unknown"
            if model not in by_model:
                by_model[model] = {"total": 0, "mentioned": 0}
            by_model[model]["total"] += 1
            if r.is_mentioned:
                by_model[model]["mentioned"] += 1
            # 解析 full_response 中的竞品提及
            if r.full_response:
                import re
                competitors_str = r.competitors or ""
                for comp in [c.strip() for c in competitors_str.split(",") if c.strip()]:
                    if re.search(re.escape(comp), r.full_response, re.IGNORECASE):
                        comp_mentions[comp] = comp_mentions.get(comp, 0) + 1
        for m in by_model.values():
            m["rate"] = round(m["mentioned"] / m["total"] * 100, 1) if m["total"] > 0 else 0
        return {
            "total_queries": len(rows),
            "by_model": by_model,
            "competitor_mentions": dict(sorted(comp_mentions.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

    def _report_to_dict(self, r: MarketingReport, include_content: bool = False) -> dict:
        base = {
            "id": r.id,
            "title": r.title,
            "report_type": r.report_type,
            "brand": r.brand,
            "date_from": r.date_from.isoformat() if r.date_from else None,
            "date_to": r.date_to.isoformat() if r.date_to else None,
            "summary": r.summary,
            "share_token": r.share_token,
            "is_published": r.is_published,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        if include_content:
            base.update({
                "kpi_data": json.loads(r.kpi_data or "{}"),
                "mention_trend": json.loads(r.mention_trend or "[]"),
                "cost_data": json.loads(r.cost_data or "{}"),
                "optimization_effect": json.loads(r.optimization_effect or "[]"),
                "recommendations": json.loads(r.recommendations or "[]"),
                "markdown_content": r.markdown_content,
            })
        return base

    async def _collect_kpi(self, brand: str, d_from: datetime, d_to: datetime) -> dict:
        # Simplified KPI collection
        from app.models.keyword import Keyword
        from app.models.article import Article
        from app.models.optimization import Optimization
        from app.models.verify_result import VerifyResult
        from app.models.api_call import ApiCall

        async def _count(model, brand_f=True):
            stmt = select(func.count(model.id)).where(model.created_at.between(d_from, d_to))
            if brand and brand_f and hasattr(model, 'brand'):
                stmt = stmt.where(model.brand == brand)
            return (await self._db.execute(stmt)).scalar() or 0

        return {
            "period": {"from": d_from.isoformat(), "to": d_to.isoformat()},
            "new_keywords": await _count(Keyword),
            "new_articles": await _count(Article),
            "new_optimizations": await _count(Optimization),
            "new_verifications": await _count(VerifyResult),
        }

    async def _collect_mention_trend(self, brand: str, d_from: datetime, d_to: datetime) -> list:
        from app.models.verify_result import VerifyResult
        from sqlalchemy import cast, Integer
        stmt = select(
            func.date(VerifyResult.created_at).label("d"),
            func.count(VerifyResult.id),
            func.sum(cast(VerifyResult.is_mentioned, Integer)),
        ).where(VerifyResult.created_at.between(d_from, d_to))
        if brand:
            stmt = stmt.where(VerifyResult.brand == brand)
        stmt = stmt.group_by(func.date(VerifyResult.created_at)).order_by("d")
        rows = (await self._db.execute(stmt)).all()
        return [
            {"date": str(r[0]), "total": r[1], "mentioned": r[2] or 0,
             "rate": round(((r[2] or 0) / r[1]) * 100, 1) if r[1] > 0 else 0}
            for r in rows
        ]

    async def _collect_costs(self, brand: str, d_from: datetime, d_to: datetime) -> dict:
        kpi = await self._roi.get_cost_report(
            self._db, brand,
            date_from=d_from.date() if hasattr(d_from, 'date') else d_from,
            date_to=d_to.date() if hasattr(d_to, 'date') else d_to,
        )
        return {
            "total_cost_cny": kpi.get("total_cost_cny", 0),
            "total_tokens": kpi.get("total_tokens", 0),
            "total_calls": kpi.get("total_calls", 0),
        }

    async def _collect_optimization_effects(self, brand: str, d_from: datetime, d_to: datetime) -> list:
        return await self._attr.get_action_effect_ranking(brand, days=(d_to - d_from).days)

    async def _generate_recommendations(self, kpi: dict, effects: list) -> list:
        recs = []
        if kpi.get("new_verifications", 0) == 0:
            recs.append("建议增加品牌可见性验证频率，至少每周验证一次")
        if kpi.get("new_articles", 0) == 0:
            recs.append("建议增加内容产出，保持每周3-5篇GEO优化文章")
        if kpi.get("new_keywords", 0) == 0:
            recs.append("建议扩充关键词库，通过AI蒸馏和竞品挖掘持续补充")
        recs.append("持续监控品牌在AI搜索中的提及率，低于60%时需加强优化")
        return recs[:8]

    def _render_markdown(
        self, title: str, kpi: dict, trend: list, costs: dict,
        effects: list, recs: list, d_from: datetime, d_to: datetime,
    ) -> str:
        lines = [
            f"# {title}",
            "",
            f"> 报告周期：{d_from.strftime('%Y-%m-%d')} ~ {d_to.strftime('%Y-%m-%d')}",
            f"> 生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 📊 核心数据概览",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
            f"| 新增关键词 | {kpi.get('new_keywords', 0)} 个 |",
            f"| 新增文章 | {kpi.get('new_articles', 0)} 篇 |",
            f"| 优化操作 | {kpi.get('new_optimizations', 0)} 次 |",
            f"| 验证次数 | {kpi.get('new_verifications', 0)} 次 |",
            f"| Token消耗 | {costs.get('total_tokens', 0):,} |",
            f"| 总费用(¥) | {costs.get('total_cost_cny', 0):.2f} |",
            "",
        ]
        if trend:
            avg_rate = sum(t["rate"] for t in trend) / len(trend)
            lines += [
                "## 📈 品牌提及率趋势",
                "",
                f"周期平均提及率：**{avg_rate:.1f}%**",
                "",
                "| 日期 | 验证总数 | 提及次数 | 提及率 |",
                "|------|----------|----------|--------|",
            ]
            for t in trend:
                lines.append(f"| {t['date']} | {t['total']} | {t['mentioned']} | {t['rate']}% |")
            lines.append("")
        if effects:
            lines += ["## 🔧 优化效果排名", ""]
            for i, e in enumerate(effects[:5], 1):
                delta = f"+{e['score_delta']:.1f}" if e.get('score_delta') and e['score_delta'] > 0 else str(e.get('score_delta', '-'))
                lines.append(f"{i}. **{e.get('action_type', '')}** - 评分变化：{delta}")
            lines.append("")
        lines += ["## 💡 建议与下一步行动", ""]
        for i, r in enumerate(recs, 1):
            lines.append(f"{i}. {r}")
        lines.append("")
        return "\n".join(lines)
