"""APScheduler 定时任务调度器"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Coroutine

from apscheduler.schedulers.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.core.logging import get_logger
from app.models.monitor import MonitorTask
from app.services.config_service import ConfigService
from app.services.data_service import DataService
from app.services.monitor_service import MonitorService

logger = get_logger(__name__)

scheduler: AsyncIOScheduler | None = None

# 自动备份相关配置
BACKUP_DIR = os.path.join(os.getcwd(), "data", "backups")
BACKUP_RETENTION_DAYS = 7
BACKUP_JOB_ID = "daily_db_backup"


def _safe_remove_job(sched: AsyncIOScheduler, job_id: str) -> None:
    """安全移除调度任务，避免 JobLookupError"""
    try:
        sched.remove_job(job_id)
    except JobLookupError:
        logger.debug("Job %s not found for removal", job_id)
    except Exception:
        logger.warning("Failed to remove job %s", job_id, exc_info=True)


async def _run_monitor_task(task_id: int) -> None:
    """后台执行监测任务（非SSE模式，静默运行）"""
    async with AsyncSessionFactory() as db:
        try:
            monitor_svc = MonitorService(db)
            config_svc = ConfigService(db)
            cfg = await config_svc.get_config()

            # 构建 provider -> api_key 映射
            provider_configs: dict[str, str] = {}
            gen_provider = cfg.get("gen_provider", "DeepSeek")
            gen_api_key = cfg.get("gen_api_key", "")
            verify_keys = cfg.get("verify_keys") or {}
            for p, k in verify_keys.items():
                if k:
                    provider_configs[p.lower()] = k
            if gen_api_key:
                provider_configs[gen_provider.lower()] = gen_api_key

            temperature = float(cfg.get("temperature", 0.7) or 0.7)

            task = await monitor_svc.get_task(task_id)
            if task is None:
                logger.warning("Scheduled task %d not found, skipping", task_id)
                return
            if not task.is_active:
                logger.info("Task %d is inactive, skipping", task_id)
                return

            results_count = 0
            async for event in monitor_svc.run_task_stream(task_id, provider_configs, temperature):
                if event.get("event") == "result":
                    results_count += 1
                elif event.get("event") == "error":
                    logger.warning("Monitor task %d error: %s", task_id, event.get("data", {}))

            task.last_run_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("Scheduled monitor task %d completed: %d results", task_id, results_count)
        except Exception as e:
            logger.error("Scheduled monitor task %d failed: %s", task_id, e, exc_info=True)
            await db.rollback()


def _cleanup_old_backups(backup_dir: str, retention_days: int) -> None:
    """清理超过保留天数的备份文件。

    Args:
        backup_dir: 备份目录路径。
        retention_days: 保留天数，早于该天数的备份将被删除。
    """
    if not os.path.isdir(backup_dir):
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    removed = 0
    for filename in os.listdir(backup_dir):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(backup_dir, filename)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath), tz=timezone.utc)
            if mtime < cutoff:
                os.remove(filepath)
                removed += 1
        except OSError as e:
            logger.warning("无法清理备份文件 %s: %s", filepath, e)
    if removed:
        logger.info("已清理 %d 个过期备份文件（超过 %d 天）", removed, retention_days)


async def _run_daily_backup() -> None:
    """每日自动数据库备份任务。

    调用 DataService.export_all() 导出全量业务数据为 JSON，
    保存到 data/backups/ 目录，并清理超过保留期的旧备份。
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"geo_backup_{timestamp}.json")

    try:
        async with AsyncSessionFactory() as db:
            data_svc = DataService(db)
            export_data: dict[str, Any] = await data_svc.export_all()
            await db.commit()

        content = json.dumps(export_data, ensure_ascii=False, indent=2, default=str)
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("每日数据库备份完成: %s (%d bytes)", backup_path, os.path.getsize(backup_path))

        # 清理过期备份
        _cleanup_old_backups(BACKUP_DIR, BACKUP_RETENTION_DAYS)
    except Exception as e:
        logger.error("每日数据库备份失败: %s", e, exc_info=True)
        # 备份失败时清理可能产生的不完整文件
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except OSError:
                pass


def _build_trigger(schedule_type: str | None, schedule_time: str) -> Any:
    """根据 schedule_type 和 schedule_time 构建 APScheduler trigger"""
    try:
        hour, minute = (schedule_time or "09:00").split(":")
        hour = int(hour)
        minute = int(minute)
    except (ValueError, AttributeError):
        hour, minute = 9, 0

    if schedule_type == "daily":
        return CronTrigger(hour=hour, minute=minute)
    elif schedule_type == "weekly":
        return CronTrigger(day_of_week="mon", hour=hour, minute=minute)
    # manual/None: 不自动调度
    return None


async def _schedule_active_tasks() -> None:
    """从数据库加载所有活跃任务并添加到调度器"""
    if scheduler is None:
        return
    async with AsyncSessionFactory() as db:
        result = await db.execute(
            select(MonitorTask).where(MonitorTask.is_active.is_(True))
        )
        tasks = result.scalars().all()

    for task in tasks:
        job_id = f"monitor_task_{task.id}"
        _safe_remove_job(scheduler, job_id)
        trigger = _build_trigger(task.schedule_type, task.schedule_time or "09:00")
        if trigger is not None:
            scheduler.add_job(
                _run_monitor_task,
                trigger=trigger,
                args=[task.id],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=3600,
            )
            logger.info("Scheduled monitor task %d (%s) at %s", task.id, task.schedule_type, task.schedule_time)


async def reschedule_task(task_id: int) -> None:
    """外部调用：任务更新后重新调度"""
    if scheduler is None:
        return
    job_id = f"monitor_task_{task_id}"
    _safe_remove_job(scheduler, job_id)
    async with AsyncSessionFactory() as db:
        result = await db.execute(select(MonitorTask).where(MonitorTask.id == task_id))
        task = result.scalar_one_or_none()
    if task and task.is_active:
        trigger = _build_trigger(task.schedule_type, task.schedule_time or "09:00")
        if trigger is not None:
            scheduler.add_job(
                _run_monitor_task,
                trigger=trigger,
                args=[task_id],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=3600,
            )
            logger.info("Rescheduled monitor task %d", task_id)


async def remove_scheduled_task(task_id: int) -> None:
    """外部调用：删除任务时移除调度"""
    if scheduler is None:
        return
    job_id = f"monitor_task_{task_id}"
    _safe_remove_job(scheduler, job_id)
    logger.info("Removed scheduled job for task %d", task_id)


def _run_async_in_loop(coro: Coroutine[Any, Any, Any]) -> None:
    """在当前事件循环中安全调度协程，捕获异常"""
    loop = asyncio.get_running_loop()
    task = asyncio.ensure_future(coro)

    def _on_done(t: asyncio.Task) -> None:
        try:
            exc = t.exception()
            if exc is not None:
                logger.error("Scheduled task bootstrap failed: %s", exc)
        except asyncio.CancelledError:
            pass

    task.add_done_callback(_on_done)


def start_scheduler() -> None:
    """启动 APScheduler（在事件循环中调用）"""
    global scheduler
    if scheduler is not None:
        return
    scheduler = AsyncIOScheduler()
    scheduler.start()
    logger.info("APScheduler started")

    # 注册每日数据库备份任务（每天凌晨 03:00 执行）
    scheduler.add_job(
        _run_daily_backup,
        trigger=CronTrigger(hour=3, minute=0),
        id=BACKUP_JOB_ID,
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Registered daily DB backup job (03:00 UTC)")

    # 延迟调度任务（确保应用完全启动）
    loop = asyncio.get_running_loop()
    loop.call_later(2, lambda: _run_async_in_loop(_schedule_active_tasks()))


def shutdown_scheduler() -> None:
    """关闭调度器"""
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("APScheduler stopped")
