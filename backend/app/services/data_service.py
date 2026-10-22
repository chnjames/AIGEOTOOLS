"""数据管理服务 - 提供数据导出、导入、清理、统计与审计日志功能"""
from __future__ import annotations

import csv
import io
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import (
    Alert,
    ApiCall,
    Article,
    ArticleVersion,
    AuditLog,
    DDSScore,
    Keyword,
    KnowledgeDoc,
    MarketingReport,
    MonitorResult,
    MonitorTask,
    Optimization,
    OptimizationAction,
    PlatformAccount,
    PublishRecord,
    VerifyResult,
    Workflow,
    WorkflowExecution,
    WorkflowTemplate,
)
from app.utils.text_utils import mask_api_key

logger = get_logger(__name__)

# 需要在导出时掩码的敏感字段（PlatformAccount 中的密钥类字段）
_SENSITIVE_FIELDS = {"api_key", "api_secret", "access_token", "refresh_token"}

# knowledge_docs 仅导出元数据时排除的字段
_KD_METADATA_EXCLUDE = {"content"}

# 全量导出时包含的模型及其在导出 JSON 中使用的键名
_EXPORT_MODELS: list[tuple[type, str]] = [
    (Keyword, "keywords"),
    (Article, "articles"),
    (ArticleVersion, "article_versions"),
    (Optimization, "optimizations"),
    (VerifyResult, "verify_results"),
    (Workflow, "workflows"),
    (WorkflowTemplate, "workflow_templates"),
    (PlatformAccount, "platform_accounts"),
    (MonitorTask, "monitor_tasks"),
]

# 导入时 JSON 键名到模型类的映射
_IMPORT_MODEL_MAP: dict[str, type] = {
    "keywords": Keyword,
    "articles": Article,
    "article_versions": ArticleVersion,
    "optimizations": Optimization,
    "verify_results": VerifyResult,
    "workflows": Workflow,
    "workflow_templates": WorkflowTemplate,
    "platform_accounts": PlatformAccount,
    "monitor_tasks": MonitorTask,
}

# 数据清理支持的表名到模型的映射
_CLEANUP_TABLE_MAP: dict[str, type] = {
    "api_calls": ApiCall,
    "verify_results": VerifyResult,
    "workflow_executions": WorkflowExecution,
    "monitor_results": MonitorResult,
}

# CSV 导出配置：模块名 -> (模型类, 字段列表)
_CSV_CONFIG: dict[str, tuple[type, list[str]]] = {
    "keywords": (Keyword, ["keyword", "brand", "is_favorite", "tags", "created_at"]),
    "articles": (Article, ["keyword", "platform", "brand", "created_at"]),
    "verify_results": (
        VerifyResult,
        ["query", "brand", "verify_model", "is_mentioned", "sentiment", "created_at"],
    ),
    "api_calls": (
        ApiCall,
        ["operation_type", "provider", "model", "total_tokens", "cost_cny", "created_at"],
    ),
}

# 整数主键、自增的表（用于导入时判断是否需要清除 id 以实现追加模式）
_AUTOINCREMENT_PK_TABLES = {
    "keywords",
    "articles",
    "article_versions",
    "optimizations",
    "verify_results",
    "platform_accounts",
    "monitor_tasks",
    "workflow_executions",
    "monitor_results",
    "api_calls",
}

# 用户数据删除/导出：直接拥有 brand 字段的业务表（模型类, 键名）
# 这些表可以通过 brand 字段直接过滤删除/导出
_USER_DATA_BRAND_MODELS: list[tuple[type, str]] = [
    (Keyword, "keywords"),
    (Article, "articles"),
    (Optimization, "optimizations"),
    (VerifyResult, "verify_results"),
    (MonitorTask, "monitor_tasks"),
    (PlatformAccount, "platform_accounts"),
    (Workflow, "workflows"),
    (KnowledgeDoc, "knowledge_docs"),
    (ApiCall, "api_calls"),
    (DDSScore, "dds_scores"),
    (OptimizationAction, "optimization_actions"),
    (MarketingReport, "marketing_reports"),
]

# 用户数据删除：子表（通过父表 ID 关联，无直接 brand 字段）
# 格式: (子模型类, 键名, 外键字段, 父模型类)
_USER_DATA_CHILD_MODELS: list[tuple[type, str, str, type]] = [
    (ArticleVersion, "article_versions", "article_id", Article),
    (PublishRecord, "publish_records", "article_id", Article),
    (MonitorResult, "monitor_results", "task_id", MonitorTask),
    (Alert, "alerts", "task_id", MonitorTask),
    (WorkflowExecution, "workflow_executions", "workflow_id", Workflow),
]


def get_db_path(database_url: str) -> Optional[str]:
    """从 DATABASE_URL 中提取 SQLite 数据库文件路径。

    支持的格式：
    - sqlite+aiosqlite:///./data/app.db
    - sqlite:///absolute/path/to/app.db
    - sqlite:///relative/path.db

    非 SQLite 数据库（如 PostgreSQL、MySQL）返回 None。

    Args:
        database_url: 数据库连接 URL 字符串。

    Returns:
        数据库文件的绝对路径，非 SQLite 时返回 None。
    """
    if not database_url:
        return None

    # sqlite:/// 或 sqlite+aiosqlite:/// 等变体
    sqlite_prefixes = ("sqlite:///", "sqlite+aiosqlite:///", "sqlite+pysqlite:///")
    for prefix in sqlite_prefixes:
        if database_url.startswith(prefix):
            raw_path = database_url[len(prefix):]
            # 处理相对路径：以 ./ 开头或不以 / 开头
            if raw_path.startswith("./"):
                raw_path = raw_path[2:]
            abs_path = os.path.abspath(raw_path)
            return abs_path

    return None


def _is_sensitive_field(col_name: str, model_cls: type) -> bool:
    """判断指定字段是否为需要掩码的敏感字段。"""
    return model_cls is PlatformAccount and col_name in _SENSITIVE_FIELDS


def _serialize_value(value: Any) -> Any:
    """将 ORM 字段值序列化为 JSON 可接受的类型。

    datetime 对象转为 ISO 8601 格式字符串，其他类型原样返回。
    """
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _model_to_dict(
    obj: Any,
    exclude: Optional[set[str]] = None,
    mask_sensitive: bool = False,
    model_cls: Optional[type] = None,
) -> dict[str, Any]:
    """将 ORM 实例转换为字典。

    Args:
        obj: SQLAlchemy ORM 实例。
        exclude: 需要排除的字段名集合。
        mask_sensitive: 是否对敏感字段进行掩码处理。
        model_cls: 模型类，用于判断敏感字段归属。

    Returns:
        序列化后的字典。
    """
    exclude = exclude or set()
    cls = model_cls or type(obj)
    result: dict[str, Any] = {}
    for col in cls.__table__.columns:
        col_name = col.name
        if col_name in exclude:
            continue
        value = getattr(obj, col_name, None)
        if mask_sensitive and _is_sensitive_field(col_name, cls):
            result[col_name] = mask_api_key(value) if value else None
        else:
            result[col_name] = _serialize_value(value)
    return result


def _deserialize_value(value: Any, col_type: Any) -> Any:
    """将 JSON 值反序列化为适合 ORM 字段的 Python 类型。

    主要处理 datetime 字段的 ISO 字符串还原。
    """
    if value is None:
        return None

    python_type = getattr(col_type, "python_type", None)

    if python_type is datetime and isinstance(value, str):
        # 尝试解析 ISO 格式时间字符串
        try:
            # 处理末尾 Z（UTC 标识）
            val = value.replace("Z", "+00:00") if value.endswith("Z") else value
            return datetime.fromisoformat(val)
        except (ValueError, TypeError):
            logger.warning("无法解析 datetime 字符串: %s，保留原值", value)
            return value

    if python_type is bool:
        return bool(value)

    return value


def _get_directory_size(path: str) -> int:
    """递归计算目录的总大小（字节）。

    Args:
        path: 目录路径。

    Returns:
        总大小（字节），目录不存在时返回 0。
    """
    total = 0
    if not os.path.isdir(path):
        return 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for filename in filenames:
            fp = os.path.join(dirpath, filename)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


class DataService:
    """数据管理服务类。

    提供完整数据导出、模块 CSV 导出、数据导入（含冲突策略）、
    历史数据清理、存储统计和审计日志记录等功能。
    """

    def __init__(self, db: AsyncSession):
        """初始化 DataService。

        Args:
            db: 异步数据库会话（AsyncSession）。
        """
        self._db = db

    # ------------------------------------------------------------------
    # 1. 全量导出
    # ------------------------------------------------------------------

    async def export_all(self) -> dict[str, Any]:
        """导出全部业务数据为 JSON 可序列化字典。

        导出范围包括：keywords、articles、article_versions、optimizations、
        verify_results、workflows（含 workflow_templates）、platform_accounts、
        monitor_tasks、knowledge_docs 元数据（不含正文内容）。

        PlatformAccount 中的 API 密钥类字段会被掩码处理，不会以明文导出。
        datetime 字段统一转换为 ISO 8601 格式字符串。

        Returns:
            包含所有导出数据的字典，顶层附带 export_version 和 exported_at 元信息。
        """
        logger.info("开始执行全量数据导出")

        export_data: dict[str, Any] = {
            "export_version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

        for model_cls, key in _EXPORT_MODELS:
            result = await self._db.execute(select(model_cls))
            rows = result.scalars().all()
            mask = model_cls is PlatformAccount
            export_data[key] = [
                _model_to_dict(row, mask_sensitive=mask, model_cls=model_cls)
                for row in rows
            ]
            logger.debug("导出 %s: %d 条记录", key, len(export_data[key]))

        # knowledge_docs 仅导出元数据，排除 content 字段
        kd_result = await self._db.execute(select(KnowledgeDoc))
        kd_rows = kd_result.scalars().all()
        export_data["knowledge_docs"] = [
            _model_to_dict(
                row,
                exclude=_KD_METADATA_EXCLUDE,
                mask_sensitive=False,
                model_cls=KnowledgeDoc,
            )
            for row in kd_rows
        ]
        logger.debug("导出 knowledge_docs 元数据: %d 条记录", len(export_data["knowledge_docs"]))

        logger.info("全量数据导出完成")
        await self._add_audit_log(
            action="export",
            resource_type="data",
            detail=json.dumps({"modules": list(export_data.keys())}, ensure_ascii=False),
        )
        return export_data

    # ------------------------------------------------------------------
    # 2. 模块 CSV 导出
    # ------------------------------------------------------------------

    async def export_csv(self, module: str) -> bytes:
        """按模块导出数据为 CSV 格式字节流。

        支持的模块：
        - keywords：keyword, brand, is_favorite, tags, created_at
        - articles：keyword, platform, brand, created_at
        - verify_results：query, brand, verify_model, is_mentioned, sentiment, created_at
        - api_calls：operation_type, provider, model, total_tokens, cost_cny, created_at

        Args:
            module: 模块名称，必须是 _CSV_CONFIG 中定义的键。

        Returns:
            UTF-8 编码的 CSV 字节数据（含 BOM 头，兼容 Excel 打开）。

        Raises:
            ValueError: 不支持的模块名。
        """
        if module not in _CSV_CONFIG:
            raise ValueError(f"不支持的 CSV 导出模块: {module}，支持的模块: {list(_CSV_CONFIG.keys())}")

        model_cls, fields = _CSV_CONFIG[module]
        logger.info("开始导出 CSV: module=%s", module)

        result = await self._db.execute(select(model_cls).order_by(model_cls.id))
        rows = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(fields)

        for row in rows:
            row_data = []
            for field in fields:
                value = getattr(row, field, None)
                if isinstance(value, datetime):
                    value = value.isoformat()
                elif value is None:
                    value = ""
                elif isinstance(value, bool):
                    value = "true" if value else "false"
                row_data.append(value)
            writer.writerow(row_data)

        csv_str = output.getvalue()
        output.close()

        # 添加 UTF-8 BOM 以便 Excel 正确识别中文
        csv_bytes = ("\ufeff" + csv_str).encode("utf-8")

        logger.info("CSV 导出完成: module=%s, rows=%d", module, len(rows))
        return csv_bytes

    # ------------------------------------------------------------------
    # 3. 数据导入
    # ------------------------------------------------------------------

    async def import_data(
        self,
        data: dict[str, Any],
        strategy: str = "skip",
    ) -> dict[str, dict[str, int]]:
        """从此前导出的 JSON 字典导入数据。

        通过主键 ID 检测冲突，支持三种冲突处理策略：
        - "skip"：跳过已存在的 ID（默认）
        - "overwrite"：覆盖已存在的记录
        - "append"：始终作为新记录插入（自增 ID 表忽略导入的 ID，字符串 ID 表生成新 ID）

        Args:
            data: 通过 export_all() 导出的字典数据。
            strategy: 冲突处理策略，可选 "skip"、"overwrite"、"append"。

        Returns:
            各模块的导入统计字典，格式为::

                {
                    "keywords": {"inserted": n, "updated": n, "skipped": n},
                    ...
                }
        """
        if strategy not in ("skip", "overwrite", "append"):
            raise ValueError(f"无效的导入策略: {strategy}，可选值: skip, overwrite, append")

        logger.info("开始导入数据, strategy=%s", strategy)

        stats: dict[str, dict[str, int]] = {}

        for key, model_cls in _IMPORT_MODEL_MAP.items():
            records = data.get(key, [])
            if not isinstance(records, list):
                logger.warning("模块 %s 的数据格式不是列表，跳过", key)
                stats[key] = {"inserted": 0, "updated": 0, "skipped": 0}
                continue

            inserted = 0
            updated = 0
            skipped = 0

            # 确定主键列
            pk_cols = list(model_cls.__table__.primary_key.columns)
            pk_col = pk_cols[0] if len(pk_cols) == 1 else None
            pk_name = pk_col.name if pk_col is not None else "id"
            is_autoincrement = key in _AUTOINCREMENT_PK_TABLES

            for record in records:
                if not isinstance(record, dict):
                    skipped += 1
                    continue

                record_data = self._build_import_data(model_cls, record)

                existing_id = record.get(pk_name)

                if strategy == "append":
                    # append 模式：始终插入新记录
                    if is_autoincrement:
                        # 自增主键：去除导入的 ID，由数据库分配新 ID
                        record_data.pop(pk_name, None)
                    else:
                        # 字符串主键（如 workflows）：生成新的唯一 ID
                        new_id = self._generate_unique_id(existing_id)
                        record_data[pk_name] = new_id
                    new_obj = model_cls(**record_data)
                    self._db.add(new_obj)
                    inserted += 1
                    continue

                # skip / overwrite 模式：先检查是否存在
                existing_obj = None
                if existing_id is not None and pk_col is not None:
                    existing_result = await self._db.execute(
                        select(model_cls).where(pk_col == existing_id)
                    )
                    existing_obj = existing_result.scalar_one_or_none()

                if existing_obj is not None:
                    if strategy == "skip":
                        skipped += 1
                        continue
                    elif strategy == "overwrite":
                        # 跳过 created_at 字段避免覆盖创建时间？此处按需求全字段覆盖
                        for col_name, value in record_data.items():
                            setattr(existing_obj, col_name, value)
                        updated += 1
                        continue

                # 不存在则插入
                new_obj = model_cls(**record_data)
                self._db.add(new_obj)
                inserted += 1

            stats[key] = {"inserted": inserted, "updated": updated, "skipped": skipped}
            logger.info(
                "模块 %s 导入完成: inserted=%d, updated=%d, skipped=%d",
                key, inserted, updated, skipped,
            )

        await self._db.flush()

        total_inserted = sum(s["inserted"] for s in stats.values())
        total_updated = sum(s["updated"] for s in stats.values())
        total_skipped = sum(s["skipped"] for s in stats.values())
        logger.info(
            "数据导入全部完成: inserted=%d, updated=%d, skipped=%d",
            total_inserted, total_updated, total_skipped,
        )

        await self._add_audit_log(
            action="import",
            resource_type="data",
            detail=json.dumps(
                {
                    "strategy": strategy,
                    "stats": stats,
                },
                ensure_ascii=False,
            ),
        )

        return stats

    def _build_import_data(self, model_cls: type, record: dict[str, Any]) -> dict[str, Any]:
        """将导入记录字典转换为适合构造 ORM 对象的 kwargs 字典。

        对 datetime 字段尝试将 ISO 字符串还原为 datetime 对象。
        仅包含模型中真实存在的列名。
        """
        col_names = {col.name for col in model_cls.__table__.columns}
        data: dict[str, Any] = {}
        for col in model_cls.__table__.columns:
            col_name = col.name
            if col_name not in record:
                continue
            raw_value = record[col_name]
            data[col_name] = _deserialize_value(raw_value, col.type)
        return data

    @staticmethod
    def _generate_unique_id(original_id: Any) -> str:
        """为字符串主键在 append 模式下生成新的唯一 ID。

        Args:
            original_id: 原始 ID 值。

        Returns:
            追加了短 UUID 后缀的新 ID 字符串。
        """
        short_uuid = uuid.uuid4().hex[:8]
        base = str(original_id) if original_id else "imported"
        return f"{base}_{short_uuid}"

    # ------------------------------------------------------------------
    # 4. 数据清理
    # ------------------------------------------------------------------

    async def cleanup_old_data(
        self,
        days: int,
        tables: Optional[List[str]] = None,
    ) -> dict[str, int]:
        """删除指定表中早于 N 天的历史记录。

        Args:
            days: 保留天数，早于（当前时间 - N 天）的记录将被删除。
            tables: 需要清理的表名列表，支持 "api_calls"、"verify_results"、
                "workflow_executions"、"monitor_results"。为 None 时清理所有支持的表。

        Returns:
            各表实际删除的行数统计。

        Raises:
            ValueError: 包含不支持的表名时抛出。
        """
        if days < 0:
            raise ValueError("days 必须是非负整数")

        if tables is None:
            tables = list(_CLEANUP_TABLE_MAP.keys())

        # 验证表名合法性
        invalid = [t for t in tables if t not in _CLEANUP_TABLE_MAP]
        if invalid:
            raise ValueError(f"不支持清理的表: {invalid}，支持的表: {list(_CLEANUP_TABLE_MAP.keys())}")

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        logger.info("开始数据清理, cutoff=%s, tables=%s", cutoff.isoformat(), tables)

        deleted_counts: dict[str, int] = {}

        for table_name in tables:
            model_cls = _CLEANUP_TABLE_MAP[table_name]

            # 确定时间字段
            time_col = self._get_time_column(model_cls)
            if time_col is None:
                logger.warning("表 %s 无合适的时间字段，跳过", table_name)
                deleted_counts[table_name] = 0
                continue

            # 先查询要删除的数量
            count_result = await self._db.execute(
                select(func.count()).select_from(model_cls).where(time_col < cutoff)
            )
            count = count_result.scalar() or 0

            if count > 0:
                await self._db.execute(delete(model_cls).where(time_col < cutoff))
                await self._db.flush()

            deleted_counts[table_name] = count
            logger.info("清理 %s: 删除 %d 条记录", table_name, count)

        await self._add_audit_log(
            action="cleanup",
            resource_type="data",
            detail=json.dumps({"days": days, "tables": tables, "deleted": deleted_counts}, ensure_ascii=False),
        )

        return deleted_counts

    @staticmethod
    def _get_time_column(model_cls: type):
        """获取模型的时间过滤列，优先使用 created_at，其次使用专用时间字段。"""
        columns = model_cls.__table__.columns

        # WorkflowExecution 使用 started_at / completed_at，没有 created_at
        if hasattr(columns, "created_at"):
            return columns.created_at
        if hasattr(columns, "started_at"):
            return columns.started_at
        # 通过列名查找
        for col in columns:
            if col.name == "created_at":
                return col
        for col in columns:
            if col.name in ("started_at", "completed_at", "executed_at"):
                return col
        return None

    # ------------------------------------------------------------------
    # 5. 用户数据管理（GDPR 被遗忘权 / 数据可携带权）
    # ------------------------------------------------------------------

    async def delete_all_user_data(self, brand: str) -> dict[str, Any]:
        """删除指定品牌的所有相关数据（GDPR「被遗忘权」实现）。

        删除范围包括：
        - 直接拥有 brand 字段的表：keywords、articles、optimizations、
          verify_results、monitor_tasks、platform_accounts、workflows、
          knowledge_docs（含磁盘文件和向量索引）、api_calls、dds_scores、
          optimization_actions、marketing_reports
        - 通过外键关联的子表：article_versions、publish_records、
          monitor_results、alerts、workflow_executions

        审计日志（audit_logs）不会被删除，以保留合规审计痕迹。

        Args:
            brand: 品牌名称，不能为空字符串。

        Returns:
            各类数据的删除计数字典，格式为::

                {
                    "keywords": n,
                    "articles": n,
                    "article_versions": n,
                    ...
                    "brand": "xxx",
                    "total_deleted": N,
                }

        Raises:
            ValueError: brand 为空或仅含空白字符时抛出。
        """
        if not brand or not brand.strip():
            raise ValueError("brand 不能为空")
        brand = brand.strip()

        logger.info("开始删除品牌 '%s' 的所有用户数据", brand)

        deleted_counts: dict[str, int] = {}

        # 1. 先收集父表 ID，用于删除依赖的子表数据
        parent_ids: dict[type, list[Any]] = {}
        for _child_cls, _child_key, fk_field, parent_cls in _USER_DATA_CHILD_MODELS:
            if parent_cls not in parent_ids:
                parent_brand_col = getattr(parent_cls, "brand", None)
                if parent_brand_col is None:
                    parent_ids[parent_cls] = []
                    continue
                pk_col = list(parent_cls.__table__.primary_key.columns)[0]
                ids_result = await self._db.execute(
                    select(pk_col).where(parent_brand_col == brand)
                )
                parent_ids[parent_cls] = [row[0] for row in ids_result.all()]

        # 2. 删除子表数据（通过父表 ID 关联）
        for child_cls, child_key, fk_field, parent_cls in _USER_DATA_CHILD_MODELS:
            ids = parent_ids.get(parent_cls, [])
            fk_col = getattr(child_cls, fk_field, None)
            if not ids or fk_col is None:
                deleted_counts[child_key] = 0
                continue

            count_result = await self._db.execute(
                select(func.count()).select_from(child_cls).where(fk_col.in_(ids))
            )
            count = count_result.scalar() or 0
            if count > 0:
                await self._db.execute(
                    delete(child_cls).where(fk_col.in_(ids))
                )
                await self._db.flush()
            deleted_counts[child_key] = count
            logger.debug("删除 %s (brand=%s): %d 条记录", child_key, brand, count)

        # 3. 删除 knowledge_docs（需要同时删除磁盘文件和向量索引）
        kd_result = await self._db.execute(
            select(KnowledgeDoc).where(KnowledgeDoc.brand == brand)
        )
        kd_docs = list(kd_result.scalars().all())
        kd_count = len(kd_docs)
        if kd_docs:
            # 延迟导入避免循环依赖
            from app.services.knowledge_service import KnowledgeService
            kd_svc = KnowledgeService(self._db)
            for doc in kd_docs:
                # 删除磁盘文件
                try:
                    if doc.file_path and os.path.exists(doc.file_path):
                        os.remove(doc.file_path)
                except OSError as e:
                    logger.warning("无法删除知识库文件 %s: %s", doc.file_path, e)
                # 删除向量索引
                kd_svc._delete_from_vector_store(doc.id)
            # 批量删除数据库记录
            await self._db.execute(
                delete(KnowledgeDoc).where(KnowledgeDoc.brand == brand)
            )
            await self._db.flush()
        deleted_counts["knowledge_docs"] = kd_count
        logger.debug("删除 knowledge_docs (brand=%s): %d 条记录", brand, kd_count)

        # 4. 删除其他有 brand 字段的父表
        for model_cls, key in _USER_DATA_BRAND_MODELS:
            if model_cls is KnowledgeDoc:
                # 已在步骤 3 中处理
                continue
            brand_col = getattr(model_cls, "brand", None)
            if brand_col is None:
                deleted_counts[key] = 0
                continue
            count_result = await self._db.execute(
                select(func.count()).select_from(model_cls).where(brand_col == brand)
            )
            count = count_result.scalar() or 0
            if count > 0:
                await self._db.execute(
                    delete(model_cls).where(brand_col == brand)
                )
                await self._db.flush()
            deleted_counts[key] = count
            logger.debug("删除 %s (brand=%s): %d 条记录", key, brand, count)

        # 5. 计算总数
        total_deleted = sum(deleted_counts.values())
        deleted_counts["brand"] = brand
        deleted_counts["total_deleted"] = total_deleted

        logger.info("品牌 '%s' 用户数据删除完成: 共删除 %d 条记录", brand, total_deleted)

        # 6. 记录审计日志（审计日志本身不会被删除，保留合规痕迹）
        await self._add_audit_log(
            action="delete",
            resource_type="user_data",
            detail=json.dumps(
                {"brand": brand, "deleted": deleted_counts},
                ensure_ascii=False,
                default=str,
            ),
        )

        return deleted_counts

    async def export_user_data(self, brand: str) -> dict[str, Any]:
        """导出指定品牌的全部用户数据（GDPR「数据可携带权」实现）。

        导出范围与 :meth:`delete_all_user_data` 的删除范围一致，但为只读操作。
        PlatformAccount 中的 API 密钥类字段会被掩码处理，不会以明文导出。
        datetime 字段统一转换为 ISO 8601 格式字符串。

        Args:
            brand: 品牌名称，不能为空字符串。

        Returns:
            包含该品牌所有导出数据的字典，顶层附带 export_version、
            exported_at、brand 元信息。

        Raises:
            ValueError: brand 为空或仅含空白字符时抛出。
        """
        if not brand or not brand.strip():
            raise ValueError("brand 不能为空")
        brand = brand.strip()

        logger.info("开始导出品牌 '%s' 的用户数据", brand)

        export_data: dict[str, Any] = {
            "export_version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "brand": brand,
        }

        # 导出直接拥有 brand 字段的表
        for model_cls, key in _USER_DATA_BRAND_MODELS:
            brand_col = getattr(model_cls, "brand", None)
            if brand_col is None:
                export_data[key] = []
                continue
            result = await self._db.execute(
                select(model_cls).where(brand_col == brand)
            )
            rows = result.scalars().all()
            mask = model_cls is PlatformAccount
            exclude = _KD_METADATA_EXCLUDE if model_cls is KnowledgeDoc else None
            export_data[key] = [
                _model_to_dict(
                    row,
                    exclude=exclude,
                    mask_sensitive=mask,
                    model_cls=model_cls,
                )
                for row in rows
            ]
            logger.debug("导出 %s (brand=%s): %d 条记录", key, brand, len(export_data[key]))

        # 导出子表数据（通过父表 ID 关联）
        for child_cls, child_key, fk_field, parent_cls in _USER_DATA_CHILD_MODELS:
            parent_brand_col = getattr(parent_cls, "brand", None)
            pk_col = list(parent_cls.__table__.primary_key.columns)[0]
            if parent_brand_col is None:
                export_data[child_key] = []
                continue
            ids_result = await self._db.execute(
                select(pk_col).where(parent_brand_col == brand)
            )
            parent_ids = [row[0] for row in ids_result.all()]
            if not parent_ids:
                export_data[child_key] = []
                continue
            fk_col = getattr(child_cls, fk_field, None)
            if fk_col is None:
                export_data[child_key] = []
                continue
            result = await self._db.execute(
                select(child_cls).where(fk_col.in_(parent_ids))
            )
            rows = result.scalars().all()
            export_data[child_key] = [
                _model_to_dict(row, mask_sensitive=False, model_cls=child_cls)
                for row in rows
            ]
            logger.debug("导出 %s (brand=%s): %d 条记录", child_key, brand, len(export_data[child_key]))

        logger.info("品牌 '%s' 用户数据导出完成", brand)

        await self._add_audit_log(
            action="export",
            resource_type="user_data",
            resource_id=brand,
            detail=json.dumps({"brand": brand, "modules": list(export_data.keys())}, ensure_ascii=False),
        )

        return export_data

    # ------------------------------------------------------------------
    # 6. 存储统计
    # ------------------------------------------------------------------

    async def get_storage_stats(self) -> dict[str, Any]:
        """获取存储相关统计信息。

        返回内容：
        - db_file_size_bytes：SQLite 数据库文件大小（字节），非 SQLite 时为 None
        - db_file_path：数据库文件路径
        - knowledge_dir_size_bytes：知识库目录总大小（字节）
        - table_counts：各数据表的行数统计

        Returns:
            包含上述统计信息的字典。
        """
        settings = get_settings()
        db_path = get_db_path(settings.DATABASE_URL)

        # 数据库文件大小
        db_file_size: Optional[int] = None
        if db_path and os.path.isfile(db_path):
            try:
                db_file_size = os.path.getsize(db_path)
            except OSError as e:
                logger.warning("无法获取数据库文件大小: %s", e)

        # 知识库目录大小
        knowledge_dir = os.path.abspath(settings.KNOWLEDGE_DIR)
        knowledge_dir_size = _get_directory_size(knowledge_dir)

        # 各表行数
        all_models: list[tuple[type, str]] = [
            (Keyword, "keywords"),
            (Article, "articles"),
            (ArticleVersion, "article_versions"),
            (Optimization, "optimizations"),
            (VerifyResult, "verify_results"),
            (ApiCall, "api_calls"),
            (Workflow, "workflows"),
            (WorkflowExecution, "workflow_executions"),
            (WorkflowTemplate, "workflow_templates"),
            (PlatformAccount, "platform_accounts"),
            (KnowledgeDoc, "knowledge_docs"),
            (MonitorTask, "monitor_tasks"),
            (MonitorResult, "monitor_results"),
            (AuditLog, "audit_logs"),
        ]

        table_counts: dict[str, int] = {}
        for model_cls, name in all_models:
            try:
                pk_col = list(model_cls.__table__.primary_key.columns)[0]
                count_result = await self._db.execute(
                    select(func.count(pk_col))
                )
                table_counts[name] = count_result.scalar() or 0
            except Exception as e:
                logger.warning("统计表 %s 行数失败: %s", name, e)
                table_counts[name] = 0

        return {
            "db_file_size_bytes": db_file_size,
            "db_file_path": db_path,
            "knowledge_dir_size_bytes": knowledge_dir_size,
            "knowledge_dir_path": knowledge_dir,
            "table_counts": table_counts,
        }

    # ------------------------------------------------------------------
    # 7. 审计日志
    # ------------------------------------------------------------------

    async def _add_audit_log(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        detail: Optional[str] = None,
        result: str = "success",
        error_message: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> None:
        """记录审计日志（内部辅助方法）。

        Args:
            action: 操作类型，如 "export"、"import"、"cleanup"、"delete" 等。
            resource_type: 资源类型，如 "data"、"keyword"、"article" 等。
            resource_id: 操作对象 ID，批量操作时为 None。
            detail: 操作详情 JSON 字符串。
            result: 操作结果，"success" 或 "failed"。
            error_message: 失败原因（result 为 failed 时填写）。
            operator: 操作者标识（系统或 API Key 标识）。
        """
        try:
            log_entry = AuditLog(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                detail=detail,
                result=result,
                error_message=error_message,
                operator=operator or "system",
            )
            self._db.add(log_entry)
            await self._db.flush()
        except Exception as e:
            # 审计日志写入失败不影响主业务流程
            logger.error("写入审计日志失败: %s", e)
