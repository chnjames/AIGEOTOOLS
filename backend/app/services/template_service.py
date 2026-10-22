"""平台模板管理服务 - 支持默认模板种子、CRUD、分组、导入导出"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.platform_template import PlatformTemplate

logger = get_logger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# 默认平台模板（与 PLATFORM_CONFIG 保持一致，用于首次种子和重置）
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_TEMPLATES: list[dict[str, Any]] = [
    # 推荐
    {"name": "知乎", "style": "专业深度分析，数据支撑，逻辑严谨，3000字以上", "filename_suffix": "_知乎专栏.md", "group_name": "推荐"},
    {"name": "知乎问答", "style": "问答体，直接回答问题，逻辑清晰，专业可信", "filename_suffix": "_知乎回答.md", "group_name": "推荐"},
    {"name": "小红书", "style": "种草笔记风格，emoji丰富，分点列述，800字以内", "filename_suffix": "_小红书.md", "group_name": "推荐"},
    {"name": "微信公众号", "style": "公众号风格，标题吸睛，段落短小，金句频出", "filename_suffix": "_公众号.md", "group_name": "推荐"},
    {"name": "B站", "style": "视频脚本风格，口语化，有画面感，分段清晰", "filename_suffix": "_B站文案.md", "group_name": "推荐"},
    {"name": "GitHub", "style": "技术README风格，结构化，英文Markdown规范", "filename_suffix": "_README.md", "group_name": "推荐"},
    # 技术社区
    {"name": "CSDN", "style": "技术博客风格，代码示例，详细步骤，解决方案", "filename_suffix": "_CSDN博客.md", "group_name": "技术社区"},
    {"name": "掘金", "style": "技术文章风格，干货输出，有实践案例", "filename_suffix": "_掘金.md", "group_name": "技术社区"},
    {"name": "博客园", "style": "技术博客风格，原创深度，代码示例", "filename_suffix": "_博客园.md", "group_name": "技术社区"},
    {"name": "思否", "style": "技术问答风格，问题导向，解决方案清晰", "filename_suffix": "_思否.md", "group_name": "技术社区"},
    # 社交媒体
    {"name": "简书", "style": "随笔风格，个人化表达，故事性强", "filename_suffix": "_简书.md", "group_name": "社交媒体"},
    {"name": "豆瓣", "style": "评论/书评风格，有独立观点，文艺气息", "filename_suffix": "_豆瓣.md", "group_name": "社交媒体"},
    {"name": "企鹅号", "style": "年轻化表达，贴近热点，互动引导", "filename_suffix": "_企鹅号.md", "group_name": "社交媒体"},
    # 资讯平台
    {"name": "头条号", "style": "资讯风格，标题醒目，信息密度高，快速阅读", "filename_suffix": "_头条号.md", "group_name": "资讯平台"},
    {"name": "百家号", "style": "科普风格，通俗易懂，适合大众阅读", "filename_suffix": "_百家号.md", "group_name": "资讯平台"},
    {"name": "搜狐号", "style": "新闻稿风格，客观陈述，信息全面", "filename_suffix": "_搜狐号.md", "group_name": "资讯平台"},
    {"name": "网易号", "style": "观点评论风格，有态度有分析", "filename_suffix": "_网易号.md", "group_name": "资讯平台"},
    {"name": "大鱼号", "style": "视频/图文结合，娱乐性强", "filename_suffix": "_大鱼号.md", "group_name": "资讯平台"},
    {"name": "趣头条", "style": "信息流风格，通俗易懂，接地气", "filename_suffix": "_趣头条.md", "group_name": "资讯平台"},
    {"name": "一点资讯", "style": "深度解读风格，有独立分析", "filename_suffix": "_一点资讯.md", "group_name": "资讯平台"},
    {"name": "新浪看点", "style": "热点追踪风格，时效性强", "filename_suffix": "_新浪看点.md", "group_name": "资讯平台"},
    {"name": "凤凰号", "style": "深度评论风格，宏观视角", "filename_suffix": "_凤凰号.md", "group_name": "资讯平台"},
]

# 默认字数（与模型列默认值保持一致）
_DEFAULT_WORD_COUNT = 1500


def _build_default_lookup() -> dict[str, dict[str, Any]]:
    """将 DEFAULT_TEMPLATES 转为以 name 为键的查找表，方便 reset_default 使用。"""
    return {t["name"]: t for t in DEFAULT_TEMPLATES}


class TemplateService:
    """平台模板管理服务

    负责内置模板的初始化、CRUD 操作、分组查询以及导入导出功能。
    内置模板（is_default=True）不可物理删除，只可禁用；通过 reset_default 可恢复原始配置。
    """

    def __init__(self, db: AsyncSession):
        self._db = db
        self._defaults_lookup = _build_default_lookup()

    # ──────────────────────────────────────────────────────────────────────────
    # 种子初始化
    # ──────────────────────────────────────────────────────────────────────────

    async def seed_defaults(self) -> None:
        """启动时调用，确保所有内置默认模板存在于数据库中。

        若数据库中已存在同名模板（包括被用户修改或禁用的），则不做任何改动，
        仅补充缺失的默认模板记录。
        """
        result = await self._db.execute(select(PlatformTemplate.name))
        existing_names = {row[0] for row in result.all()}

        added = 0
        for tpl in DEFAULT_TEMPLATES:
            if tpl["name"] not in existing_names:
                self._db.add(PlatformTemplate(
                    name=tpl["name"],
                    style_instruction=tpl["style"],
                    filename_suffix=tpl["filename_suffix"],
                    group_name=tpl["group_name"],
                    word_count_default=tpl.get("word_count_default", _DEFAULT_WORD_COUNT),
                    is_default=True,
                    is_active=True,
                ))
                added += 1

        if added:
            await self._db.flush()
            logger.info(f"seed_defaults: 添加了 {added} 条缺失的默认模板")
        else:
            logger.debug("seed_defaults: 所有默认模板均已存在，无需补充")

    # ──────────────────────────────────────────────────────────────────────────
    # 查询
    # ──────────────────────────────────────────────────────────────────────────

    async def list_templates(self, active_only: bool = True) -> list[PlatformTemplate]:
        """返回模板列表，可选择只返回已启用的模板。

        Args:
            active_only: 若为 True 则仅返回 is_active=True 的模板。

        Returns:
            模板列表，按 group_name、name 排序。
        """
        stmt = select(PlatformTemplate)
        if active_only:
            stmt = stmt.where(PlatformTemplate.is_active.is_(True))
        stmt = stmt.order_by(PlatformTemplate.group_name, PlatformTemplate.name)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_template(self, template_id: int) -> Optional[PlatformTemplate]:
        """根据主键 ID 获取单个模板。"""
        return await self._db.get(PlatformTemplate, template_id)

    async def get_template_by_name(self, name: str) -> Optional[PlatformTemplate]:
        """根据平台名称（唯一）获取模板。"""
        result = await self._db.execute(
            select(PlatformTemplate).where(PlatformTemplate.name == name)
        )
        return result.scalar_one_or_none()

    # ──────────────────────────────────────────────────────────────────────────
    # 创建 / 更新 / 删除
    # ──────────────────────────────────────────────────────────────────────────

    async def create_template(
        self,
        name: str,
        style_instruction: str,
        filename_suffix: str,
        group_name: str,
        word_count_default: int = _DEFAULT_WORD_COUNT,
    ) -> PlatformTemplate:
        """创建自定义模板（is_default=False）。

        Args:
            name: 平台名称（唯一）。
            style_instruction: 内容风格指令。
            filename_suffix: 导出文件名后缀。
            group_name: 分组名称。
            word_count_default: 默认字数，默认 1500。

        Returns:
            新创建的 PlatformTemplate 实例。
        """
        tpl = PlatformTemplate(
            name=name,
            style_instruction=style_instruction,
            filename_suffix=filename_suffix,
            group_name=group_name,
            word_count_default=word_count_default,
            is_default=False,
            is_active=True,
        )
        self._db.add(tpl)
        await self._db.flush()
        await self._db.refresh(tpl)
        logger.info(f"create_template: 创建自定义模板 '{name}' (id={tpl.id})")
        return tpl

    async def update_template(
        self, template_id: int, **kwargs: Any
    ) -> Optional[PlatformTemplate]:
        """更新模板字段。

        允许更新默认模板的任何字段（包括 name 和 style_instruction）；
        不允许通过此方法修改 is_default 标记。

        Args:
            template_id: 模板 ID。
            **kwargs: 要更新的字段（is_default 将被忽略）。

        Returns:
            更新后的模板实例，若 ID 不存在则返回 None。
        """
        tpl = await self.get_template(template_id)
        if tpl is None:
            logger.warning(f"update_template: 模板 id={template_id} 不存在")
            return None

        # 禁止直接修改 is_default
        kwargs.pop("is_default", None)

        allowed_fields = {
            "name", "style_instruction", "filename_suffix",
            "group_name", "word_count_default", "is_active", "extra_config",
        }
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(tpl, field, value)

        await self._db.flush()
        await self._db.refresh(tpl)
        logger.info(f"update_template: 更新模板 '{tpl.name}' (id={tpl.id})")
        return tpl

    async def delete_template(self, template_id: int) -> bool:
        """删除模板。

        内置模板（is_default=True）不允许物理删除，仅将其 is_active 置为 False（软禁用）。
        自定义模板（is_default=False）将被物理删除。

        Args:
            template_id: 模板 ID。

        Returns:
            True 表示删除/禁用成功；False 表示模板不存在。
        """
        tpl = await self.get_template(template_id)
        if tpl is None:
            logger.warning(f"delete_template: 模板 id={template_id} 不存在")
            return False

        if tpl.is_default:
            # 内置模板：软禁用
            tpl.is_active = False
            await self._db.flush()
            logger.info(f"delete_template: 禁用内置模板 '{tpl.name}' (id={tpl.id})")
        else:
            # 自定义模板：物理删除
            await self._db.delete(tpl)
            await self._db.flush()
            logger.info(f"delete_template: 删除自定义模板 '{tpl.name}' (id={tpl.id})")

        return True

    async def reset_default(self, template_id: int) -> bool:
        """将内置默认模板重置为原始配置。

        恢复 style_instruction、filename_suffix、group_name、word_count_default 为种子值，
        并重新启用（is_active=True）。对非默认模板调用此方法无效。

        Args:
            template_id: 模板 ID（必须是 is_default=True 的内置模板）。

        Returns:
            True 表示重置成功；False 表示模板不存在或非内置模板。
        """
        tpl = await self.get_template(template_id)
        if tpl is None:
            logger.warning(f"reset_default: 模板 id={template_id} 不存在")
            return False

        if not tpl.is_default:
            logger.warning(f"reset_default: 模板 '{tpl.name}' (id={template_id}) 不是内置模板，无法重置")
            return False

        original = self._defaults_lookup.get(tpl.name)
        if original is None:
            # 理论上不会发生：is_default 模板的 name 必然存在于 DEFAULT_TEMPLATES
            logger.error(f"reset_default: 内置模板 '{tpl.name}' 在 DEFAULT_TEMPLATES 中找不到原始配置")
            return False

        tpl.style_instruction = original["style"]
        tpl.filename_suffix = original["filename_suffix"]
        tpl.group_name = original["group_name"]
        tpl.word_count_default = original.get("word_count_default", _DEFAULT_WORD_COUNT)
        tpl.is_active = True

        await self._db.flush()
        logger.info(f"reset_default: 重置内置模板 '{tpl.name}' (id={tpl.id}) 为原始配置")
        return True

    # ──────────────────────────────────────────────────────────────────────────
    # 兼容层（向后兼容 PLATFORM_CONFIG 格式）
    # ──────────────────────────────────────────────────────────────────────────

    async def get_platform_config(self) -> dict[str, dict[str, Any]]:
        """返回与 article_service.PLATFORM_CONFIG 兼容的字典格式。

        合并策略：数据库中所有 active 模板（含自定义和已修改的默认模板）优先；
        代码中定义但数据库中缺失的默认模板作为回退补充，保证向后兼容。

        Returns:
            格式为 ``{平台名: {"style": ..., "filename_suffix": ..., "group": ...}}`` 的字典。
        """
        # 从代码默认值构建基础字典（作为回退）
        config: dict[str, dict[str, Any]] = {}
        for tpl in DEFAULT_TEMPLATES:
            config[tpl["name"]] = {
                "style": tpl["style"],
                "filename_suffix": tpl["filename_suffix"],
                "group": tpl["group_name"],
            }

        # 用数据库中 active 的模板覆盖（包括自定义模板和被修改的默认模板）
        db_templates = await self.list_templates(active_only=True)
        for tpl in db_templates:
            config[tpl.name] = {
                "style": tpl.style_instruction,
                "filename_suffix": tpl.filename_suffix,
                "group": tpl.group_name,
            }

        return config

    async def get_platform_groups(self) -> list[dict[str, Any]]:
        """返回按 group_name 分组的平台列表。

        Returns:
            格式为 ``[{"group": 分组名, "platforms": [平台名, ...]}, ...]`` 的列表，
            分组按 DEFAULT_TEMPLATES 中首次出现的顺序排列，自定义分组追加在最后。
        """
        db_templates = await self.list_templates(active_only=True)

        # 用 OrderedDict 风格保持分组顺序
        group_order: list[str] = []
        group_map: dict[str, list[str]] = {}

        # 先按 DEFAULT_TEMPLATES 的分组顺序建立骨架
        seen_groups: set[str] = set()
        for tpl in DEFAULT_TEMPLATES:
            g = tpl["group_name"]
            if g not in seen_groups:
                seen_groups.add(g)
                group_order.append(g)
                group_map[g] = []

        # 填充数据库模板
        for tpl in db_templates:
            g = tpl.group_name
            if g not in group_map:
                group_order.append(g)
                group_map[g] = []
            group_map[g].append(tpl.name)

        return [
            {"group": g, "platforms": sorted(group_map[g])}
            for g in group_order
            if group_map[g]  # 跳过空分组
        ]

    # ──────────────────────────────────────────────────────────────────────────
    # 导入 / 导出
    # ──────────────────────────────────────────────────────────────────────────

    async def export_templates(self) -> list[dict[str, Any]]:
        """导出所有模板（含禁用的）为字典列表，可用于备份或迁移。

        Returns:
            每个字典包含 name、style_instruction、filename_suffix、group_name、
            word_count_default、is_default、is_active、extra_config 字段。
        """
        result = await self._db.execute(
            select(PlatformTemplate).order_by(PlatformTemplate.group_name, PlatformTemplate.name)
        )
        templates = result.scalars().all()
        return [
            {
                "name": t.name,
                "style_instruction": t.style_instruction,
                "filename_suffix": t.filename_suffix,
                "group_name": t.group_name,
                "word_count_default": t.word_count_default,
                "is_default": t.is_default,
                "is_active": t.is_active,
                "extra_config": t.extra_config,
            }
            for t in templates
        ]

    async def import_templates(
        self, templates_data: list[dict[str, Any]], strategy: str = "skip"
    ) -> dict[str, Any]:
        """导入模板数据。

        Args:
            templates_data: 模板字典列表，字段同 export_templates 输出。
            strategy: 导入策略：
                - ``"skip"``: 同名模板已存在则跳过（默认）。
                - ``"overwrite"``: 同名模板已存在则更新其内容（不改变 is_default 状态）。
                - ``"append"``: 总是追加；同名冲突时自动添加数字后缀（如 "知乎 (1)"）。

        Returns:
            统计字典 ``{"imported": int, "skipped": int, "updated": int, "failed": int}``。
        """
        stats = {"imported": 0, "skipped": 0, "updated": 0, "failed": 0}

        if strategy not in {"skip", "overwrite", "append"}:
            logger.warning(f"import_templates: 未知策略 '{strategy}'，回退为 'skip'")
            strategy = "skip"

        for data in templates_data:
            try:
                name = data.get("name", "").strip()
                if not name:
                    stats["failed"] += 1
                    continue

                # 查询是否已存在同名模板
                existing = await self.get_template_by_name(name)

                if existing is not None:
                    if strategy == "skip":
                        stats["skipped"] += 1
                        continue

                    elif strategy == "overwrite":
                        # 更新已有模板，但保留其 is_default 标记
                        update_data = {
                            k: v for k, v in data.items()
                            if k in {
                                "style_instruction", "filename_suffix",
                                "group_name", "word_count_default",
                                "is_active", "extra_config",
                            } and v is not None
                        }
                        for field, value in update_data.items():
                            setattr(existing, field, value)
                        await self._db.flush()
                        stats["updated"] += 1
                        continue

                    elif strategy == "append":
                        # 同名则生成唯一名称
                        unique_name = await self._make_unique_name(name)
                        await self._create_from_import(data, unique_name)
                        stats["imported"] += 1
                        continue
                else:
                    # 不存在同名模板，直接创建
                    # 导入的模板一律设为非内置（is_default=False），避免覆盖内置标记
                    await self._create_from_import(data, name)
                    stats["imported"] += 1

            except Exception:
                logger.exception(f"import_templates: 导入模板失败: {data.get('name', '?')}")
                stats["failed"] += 1

        await self._db.flush()
        logger.info(
            f"import_templates(strategy={strategy}): "
            f"导入 {stats['imported']}，更新 {stats['updated']}，"
            f"跳过 {stats['skipped']}，失败 {stats['failed']}"
        )
        return stats

    # ──────────────────────────────────────────────────────────────────────────
    # 内部辅助
    # ──────────────────────────────────────────────────────────────────────────

    async def _create_from_import(self, data: dict[str, Any], name: str) -> PlatformTemplate:
        """根据导入数据创建一条模板记录（is_default 强制为 False）。"""
        tpl = PlatformTemplate(
            name=name,
            style_instruction=data.get("style_instruction", ""),
            filename_suffix=data.get("filename_suffix", ".md"),
            group_name=data.get("group_name", "其他"),
            word_count_default=data.get("word_count_default", _DEFAULT_WORD_COUNT),
            is_default=False,
            is_active=data.get("is_active", True),
            extra_config=data.get("extra_config"),
        )
        self._db.add(tpl)
        await self._db.flush()
        await self._db.refresh(tpl)
        return tpl

    async def _make_unique_name(self, base_name: str) -> str:
        """为 append 策略生成不重复的模板名称，格式如 "知乎 (1)"、"知乎 (2)"。"""
        # 收集所有现有名称
        result = await self._db.execute(select(PlatformTemplate.name))
        existing_names = {row[0] for row in result.all()}

        if base_name not in existing_names:
            return base_name

        counter = 1
        while f"{base_name} ({counter})" in existing_names:
            counter += 1
        return f"{base_name} ({counter})"
