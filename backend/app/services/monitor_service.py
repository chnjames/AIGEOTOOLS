"""持续监测服务 - 定时巡检、结果存储、告警生成、趋势分析"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime, date, timedelta, timezone
from typing import Any, AsyncGenerator, Optional

from sqlalchemy import select, func, and_, case, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.monitor import MonitorTask, MonitorResult, Alert
from app.prompts.verify_prompts import VERIFY_BRAND_PROMPT
from app.services.llm_factory import get_default_model
from app.services.llm_service import LLMService, LLMConfig

logger = get_logger(__name__)

# 限制并发 LLM 调用数，防止多任务并行时压垮上游模型 API
_LLM_CONCURRENCY_SEMAPHORE = asyncio.Semaphore(5)


# ---------------------------------------------------------------------------
# Response parsing helpers (mirrors parse_verify_result in verify_service.py)
# ---------------------------------------------------------------------------

def _parse_queries(queries_raw: str) -> list[str]:
    """解析查询词列表，支持 JSON 数组或换行分隔格式"""
    queries_raw = queries_raw.strip()
    if not queries_raw:
        return []
    # Try JSON first
    try:
        parsed = json.loads(queries_raw)
        if isinstance(parsed, list):
            return [str(q).strip() for q in parsed if str(q).strip()]
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback: newline or comma separated
    return [
        line.strip()
        for line in re.split(r"[\n,;]", queries_raw)
        if line.strip()
    ]


def _parse_platforms(platforms_raw: str) -> list[str]:
    """解析平台列表（逗号分隔）"""
    if not platforms_raw:
        return []
    return [p.strip() for p in platforms_raw.split(",") if p.strip()]


def _parse_monitor_result(response_text: str, brand: str, platform: str, query: str) -> dict[str, Any]:
    """解析 LLM 验证响应，提取品牌分析、情感、竞品信息"""
    # Basic mention detection (same logic as verify_service.parse_verify_result)
    is_mentioned = bool(brand) and brand in response_text
    mention_count = response_text.count(brand) if brand else 0

    position = "未提及"
    if brand and brand in response_text:
        idx = response_text.find(brand)
        ratio = idx / len(response_text) if response_text else 1
        if ratio < 0.33:
            position = "开头前1/3"
        elif ratio < 0.66:
            position = "中间1/3"
        else:
            position = "末尾1/3"

    # Parse structured analysis section
    sentiment = "neutral"
    competitor_mentions: dict[str, Any] = {"recommended_brands": [], "competitors_found": []}

    analysis_match = re.search(r"---\s*品牌分析[：:]\s*([\s\S]*)", response_text)
    analysis_text = ""
    if analysis_match:
        analysis_text = analysis_match.group(1).strip()

        # 是否提及
        mention_match = re.search(r"是否提及[【\[][^\]】]*[】\]]\s*[：:]\s*(是|否)", analysis_text)
        if mention_match:
            is_mentioned = mention_match.group(1) == "是"

        # 提及次数
        count_match = re.search(r"提及次数\s*[：:]\s*(\d+)", analysis_text)
        if count_match:
            mention_count = int(count_match.group(1))

        # 提及位置
        pos_match = re.search(r"提及位置\s*[：:]\s*(开头前1/3|中间1/3|末尾1/3|未提及)", analysis_text)
        if pos_match:
            position = pos_match.group(1)

        # 情感（提及语境）
        sent_match = re.search(r"提及语境\s*[：:]\s*(正面|中性|负面|未提及)", analysis_text)
        if sent_match:
            raw_sent = sent_match.group(1)
            sentiment = {"正面": "positive", "中性": "neutral", "负面": "negative"}.get(raw_sent, "neutral")

        # 推荐品牌
        rec_match = re.search(r"推荐的?品牌\s*[：:]\s*(.+)", analysis_text)
        if rec_match:
            brands_str = rec_match.group(1).strip()
            recommended = [
                b.strip()
                for b in re.split(r"[、,，;；\s]+", brands_str)
                if b.strip() and b.strip() != "无" and b.strip() != "未提及"
            ]
            competitor_mentions["recommended_brands"] = recommended
            if brand:
                competitor_mentions["competitors_found"] = [
                    b for b in recommended if b != brand
                ]

    # Content snippet: first line containing the brand
    snippet = ""
    if brand:
        for line in response_text.split("\n"):
            if brand in line:
                snippet = line.strip()[:200]
                break
    if not snippet:
        snippet = response_text[:200].strip()

    # Competitor dominance detection
    competitors_found = competitor_mentions.get("competitors_found", [])
    is_competitor_dominant = False
    if competitors_found and brand:
        # If brand not in recommended but competitors are
        recommended = competitor_mentions.get("recommended_brands", [])
        if recommended and brand not in recommended and competitors_found:
            is_competitor_dominant = True

    return {
        "platform": platform,
        "query": query,
        "is_mentioned": is_mentioned,
        "mention_position": position,
        "mention_count": mention_count,
        "sentiment": sentiment,
        "content_snippet": snippet,
        "competitor_mentions": json.dumps(competitor_mentions, ensure_ascii=False),
        "is_competitor_dominant": is_competitor_dominant,
        "full_response": response_text,
    }


# ---------------------------------------------------------------------------
# Monitor Service
# ---------------------------------------------------------------------------

class MonitorService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._llm = LLMService(db)

    # ---- CRUD for MonitorTask -------------------------------------------------

    async def create_task(self, data: dict[str, Any]) -> MonitorTask:
        """创建监测任务"""
        task = MonitorTask(**data)
        self._db.add(task)
        await self._db.flush()
        logger.info("Monitor task created: id=%s name=%s", task.id, task.name)
        return task

    async def list_tasks(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """分页列出监测任务"""
        count_query = select(func.count(MonitorTask.id))
        total = (await self._db.execute(count_query)).scalar() or 0
        query = (
            select(MonitorTask)
            .order_by(MonitorTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._db.execute(query)
        items = list(result.scalars().all())
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    async def get_task(self, task_id: int) -> MonitorTask:
        """获取单个监测任务"""
        task = await self._db.get(MonitorTask, task_id)
        if task is None:
            raise NotFoundError(f"监测任务不存在: id={task_id}")
        return task

    async def update_task(self, task_id: int, data: dict[str, Any]) -> MonitorTask:
        """更新监测任务"""
        task = await self.get_task(task_id)
        for key, value in data.items():
            if value is not None and hasattr(task, key):
                setattr(task, key, value)
        await self._db.flush()
        logger.info("Monitor task updated: id=%s", task_id)
        return task

    async def delete_task(self, task_id: int) -> bool:
        """删除监测任务（级联删除结果和告警）"""
        task = await self.get_task(task_id)
        # Cascade delete associated results and alerts
        await self._db.execute(sa_delete(MonitorResult).where(MonitorResult.task_id == task_id))
        await self._db.execute(sa_delete(Alert).where(Alert.task_id == task_id))
        await self._db.delete(task)
        await self._db.flush()
        logger.info("Monitor task deleted: id=%s", task_id)
        return True

    async def toggle_task(self, task_id: int) -> MonitorTask:
        """切换任务启用/禁用状态"""
        task = await self.get_task(task_id)
        task.is_active = not task.is_active
        await self._db.flush()
        logger.info("Monitor task toggled: id=%s active=%s", task_id, task.is_active)
        return task

    # ---- Results retrieval ----------------------------------------------------

    async def get_results(
        self,
        task_id: int,
        page: int = 1,
        page_size: int = 20,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict[str, Any]:
        """分页获取任务的监测结果，可选日期范围过滤"""
        filters = [MonitorResult.task_id == task_id]
        if start_date:
            filters.append(MonitorResult.created_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc))
        if end_date:
            filters.append(MonitorResult.created_at <= datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc))

        count_query = select(func.count(MonitorResult.id)).where(and_(*filters))
        total = (await self._db.execute(count_query)).scalar() or 0

        query = (
            select(MonitorResult)
            .where(and_(*filters))
            .order_by(MonitorResult.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._db.execute(query)
        items = list(result.scalars().all())
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    # ---- Manual trigger execution (SSE streaming) -----------------------------

    async def run_task_stream(
        self,
        task_id: int,
        provider_configs: dict[str, str],
        temperature: float = 0.7,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        手动触发监测任务执行（SSE 流式）。
        遍历每个平台和查询词组合，调用 LLM 验证，保存结果，生成告警。
        """
        task = await self.get_task(task_id)
        queries = _parse_queries(task.queries)
        platforms = _parse_platforms(task.platforms)
        brand = task.brand or ""

        if not queries:
            yield {"event": "error", "data": {"message": "任务未配置查询词"}}
            return

        # Filter to platforms that have valid API keys
        active_platforms = [(p, k) for p, k in provider_configs.items() if k]
        if not active_platforms:
            yield {"event": "error", "data": {"message": "没有可用的平台 API Key 配置"}}
            return

        # Filter platforms by task's platform list
        task_platform_set = set(platforms)
        if task_platform_set:
            active_platforms = [
                (p, k) for p, k in active_platforms
                if p in task_platform_set
            ]

        if not active_platforms:
            yield {"event": "error", "data": {"message": "任务指定的平台均未配置 API Key"}}
            return

        batch_id = uuid.uuid4().hex[:12]
        total_steps = len(active_platforms) * len(queries)
        current_step = 0
        batch_results: list[MonitorResult] = []

        yield {"event": "start", "data": {
            "task_id": task_id,
            "batch_id": batch_id,
            "total": total_steps,
            "message": f"开始执行监测任务「{task.name}」，共 {total_steps} 项检查",
        }}

        for provider, api_key in active_platforms:
            model = get_default_model(provider)
            cfg = LLMConfig(provider=provider, api_key=api_key, model=model, temperature=temperature)

            for query in queries:
                current_step += 1
                yield {"event": "progress", "data": {
                    "step": current_step,
                    "total": total_steps,
                    "platform": provider,
                    "query": query,
                    "message": f"正在 {provider} 验证：{query}",
                }}

                try:
                    prompt = VERIFY_BRAND_PROMPT.format(query=query, brand=brand)
                    response_chunks: list[str] = []
                    # 使用信号量限制并发 LLM 调用数，防止多任务并行时压垮上游模型 API
                    async with _LLM_CONCURRENCY_SEMAPHORE:
                        async for chunk in self._llm.stream(prompt, cfg):
                            response_chunks.append(chunk)

                    full_response = "".join(response_chunks)
                    parsed = _parse_monitor_result(full_response, brand, provider, query)

                    # Determine if this individual result triggers an alert
                    is_alert_flag = False
                    if parsed["sentiment"] == "negative":
                        is_alert_flag = True
                    if parsed["is_competitor_dominant"]:
                        is_alert_flag = True

                    mr = MonitorResult(
                        task_id=task_id,
                        query=query,
                        platform=provider,
                        is_mentioned=parsed["is_mentioned"],
                        mention_position=parsed["mention_position"],
                        mention_count=parsed["mention_count"],
                        sentiment=parsed["sentiment"],
                        content_snippet=parsed["content_snippet"],
                        competitor_mentions=parsed["competitor_mentions"],
                        is_alert=is_alert_flag,
                        run_batch=batch_id,
                    )
                    self._db.add(mr)
                    await self._db.flush()
                    batch_results.append(mr)

                    # Generate individual result alerts
                    if parsed["sentiment"] == "negative":
                        await self._create_alert(
                            alert_type="negative_mention",
                            level="warning",
                            title=f"品牌负面提及 - {provider}",
                            message=f"在 {provider} 平台查询「{query}」时检测到品牌负面提及",
                            task_id=task_id,
                            result_id=mr.id,
                            metadata={
                                "platform": provider,
                                "query": query,
                                "snippet": parsed["content_snippet"][:100],
                                "batch_id": batch_id,
                            },
                        )

                    if parsed["is_competitor_dominant"]:
                        comp_data = json.loads(parsed["competitor_mentions"]) if parsed["competitor_mentions"] else {}
                        found = comp_data.get("competitors_found", [])
                        await self._create_alert(
                            alert_type="competitor_dominance",
                            level="warning",
                            title=f"竞品主导推荐 - {provider}",
                            message=f"在 {provider} 平台查询「{query}」时竞品被优先推荐：{'、'.join(found[:3])}",
                            task_id=task_id,
                            result_id=mr.id,
                            metadata={
                                "platform": provider,
                                "query": query,
                                "competitors_found": found,
                                "batch_id": batch_id,
                            },
                        )

                    yield {"event": "result", "data": {
                        "step": current_step,
                        "total": total_steps,
                        "platform": provider,
                        "query": query,
                        "result_id": mr.id,
                        "is_mentioned": parsed["is_mentioned"],
                        "mention_position": parsed["mention_position"],
                        "sentiment": parsed["sentiment"],
                        "is_alert": is_alert_flag,
                    }}

                except Exception as e:
                    logger.error("Monitor run failed for platform=%s query=%s: %s", provider, query, e)
                    yield {"event": "item_error", "data": {
                        "step": current_step,
                        "total": total_steps,
                        "platform": provider,
                        "query": query,
                        "error": str(e),
                    }}

        # Post-batch analysis: check overall mention rate against threshold
        if batch_results:
            mentioned_count = sum(1 for r in batch_results if r.is_mentioned)
            total_checks = len(batch_results)
            mention_rate = mentioned_count / total_checks if total_checks > 0 else 0.0

            if mention_rate < task.alert_threshold:
                await self._create_alert(
                    alert_type="low_mention_rate",
                    level="critical" if mention_rate < task.alert_threshold * 0.5 else "warning",
                    title="品牌提及率过低告警",
                    message=(
                        f"批次 {batch_id} 提及率为 {mention_rate:.0%}，"
                        f"低于阈值 {task.alert_threshold:.0%}（{mentioned_count}/{total_checks}）"
                    ),
                    task_id=task_id,
                    result_id=None,
                    metadata={
                        "batch_id": batch_id,
                        "mention_rate": mention_rate,
                        "threshold": task.alert_threshold,
                        "mentioned_count": mentioned_count,
                        "total_checks": total_checks,
                    },
                )
                yield {"event": "alert", "data": {
                    "type": "low_mention_rate",
                    "mention_rate": mention_rate,
                    "threshold": task.alert_threshold,
                    "message": f"提及率 {mention_rate:.0%} 低于阈值 {task.alert_threshold:.0%}",
                }}

        # Update task last_run_at
        task.last_run_at = datetime.now(timezone.utc)
        await self._db.flush()

        yield {"event": "complete", "data": {
            "task_id": task_id,
            "batch_id": batch_id,
            "total_checks": len(batch_results),
            "message": f"监测任务执行完成，批次 {batch_id}",
        }}

    # ---- Alert generation helpers ---------------------------------------------

    async def _create_alert(
        self,
        alert_type: str,
        level: str,
        title: str,
        message: str,
        task_id: Optional[int] = None,
        result_id: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Alert:
        """创建告警记录"""
        alert = Alert(
            alert_type=alert_type,
            level=level,
            title=title,
            message=message,
            task_id=task_id,
            result_id=result_id,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
        self._db.add(alert)
        await self._db.flush()
        logger.warning("Alert created: type=%s level=%s title=%s", alert_type, level, title)
        return alert

    # ---- Alerts ---------------------------------------------------------------

    async def list_alerts(
        self,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """分页列出告警，可仅看未读"""
        filters = []
        if unread_only:
            filters.append(Alert.is_read == False)  # noqa: E712

        count_query = select(func.count(Alert.id)).where(and_(*filters)) if filters else select(func.count(Alert.id))
        total = (await self._db.execute(count_query)).scalar() or 0

        query = (
            select(Alert)
            .where(and_(*filters)) if filters else select(Alert)
        )
        query = (
            query
            .order_by(Alert.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._db.execute(query)
        items = list(result.scalars().all())
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    async def mark_alert_read(self, alert_id: int) -> Alert:
        """标记告警为已读"""
        alert = await self._db.get(Alert, alert_id)
        if alert is None:
            raise NotFoundError(f"告警不存在: id={alert_id}")
        alert.is_read = True
        await self._db.flush()
        logger.info("Alert marked as read: id=%s", alert_id)
        return alert

    # ---- Trend data -----------------------------------------------------------

    async def get_trends(
        self,
        task_id: Optional[int] = None,
        platform: Optional[str] = None,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """
        查询趋势数据：按日期+平台聚合提及率。
        返回 [{date, platform, mention_rate, total_checks, mentioned_count}, ...]
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        filters = [MonitorResult.created_at >= start_date]
        if task_id is not None:
            filters.append(MonitorResult.task_id == task_id)
        if platform:
            filters.append(MonitorResult.platform == platform)

        # Group by date (cast to DATE) and platform
        date_col = func.date(MonitorResult.created_at).label("d")
        query = (
            select(
                date_col,
                MonitorResult.platform,
                func.count(MonitorResult.id).label("total_checks"),
                func.sum(case((MonitorResult.is_mentioned == True, 1), else_=0)).label("mentioned_count"),  # noqa: E712
            )
            .where(and_(*filters))
            .group_by(date_col, MonitorResult.platform)
            .order_by(date_col.asc(), MonitorResult.platform)
        )
        result = await self._db.execute(query)
        rows = result.all()

        trends: list[dict[str, Any]] = []
        for row in rows:
            d, plat, total, mentioned = row
            mention_rate = round(mentioned / total, 4) if total > 0 else 0.0
            trends.append({
                "date": d.isoformat() if hasattr(d, "isoformat") else str(d),
                "platform": plat,
                "mention_rate": mention_rate,
                "total_checks": total or 0,
                "mentioned_count": mentioned or 0,
            })
        return trends
