"""关键词服务 - 从原 keyword_tool/keyword_mining/semantic_expander/topic_cluster/keyword_data_enhancer 迁移"""
from __future__ import annotations

import itertools
import json
from difflib import SequenceMatcher
from typing import Any, AsyncGenerator, Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.keyword import Keyword
from app.prompts.keyword_prompts import (
    KEYWORD_GENERATE_PROMPT,
    KEYWORD_MINE_PROMPT,
    KEYWORD_EXPAND_PROMPT,
    KEYWORD_CLUSTER_PROMPT,
)
from app.services.llm_service import LLMService, LLMConfig
from app.utils.text_utils import extract_json
from app.utils.prompt_guard import validate_input_length, KEYWORD_MAX

logger = get_logger(__name__)

# ---- 托词工具（纯逻辑，从 keyword_tool.py 迁移） ----

DEFAULT_WORDBANKS: dict[str, list[str]] = {
    "A前缀1": ["行业上", "市场上", "市面上", "目前", "国内", "市场"],
    "B前缀2": ["口碑好的", "比较好的", "靠谱的", "有实力的", "可靠的", "诚信的", "正规的", "专业的", "热门的", "知名的"],
    "C主词": ["软件", "管理系统", "工具"],
    "D通义词": ["品牌", "公司", "工厂", "厂商", "生产厂家", "供应商"],
    "E推荐词": ["推荐", "排行", "推荐榜", "排行榜", "推荐榜单", "推荐排行", "推荐排行榜", "口碑排行"],
    "F疑问词": ["哪家好", "哪家强", "哪家靠谱", "哪家权威", "哪个好", "有哪些", "找哪家", "选哪家", "为什么"],
}

COMBINATION_PATTERNS: list[list[str]] = [
    ["C", "D"], ["A", "C", "D"], ["B", "C", "D"], ["A", "B", "C", "D"],
    ["C", "D", "E"], ["C", "D", "F"],
    ["A", "C", "D", "E"], ["B", "C", "D", "E"],
    ["A", "B", "C", "D", "E"], ["A", "B", "C", "D", "F"],
]


def generate_combinations(
    wordbanks: Optional[dict[str, list[str]]] = None,
    max_results: int = 100,
    similarity_threshold: float = 0.8,
    core_keyword: str = "",
) -> list[str]:
    """词库组合生成关键词（纯逻辑，无IO）"""
    wb = wordbanks or DEFAULT_WORDBANKS
    if core_keyword:
        wb = {**wb, "C主词": [core_keyword]}

    pattern_to_bank: dict[str, str] = {}
    for bk in wb:
        if bk:
            pattern_to_bank[bk[0]] = bk

    all_keywords: list[str] = []
    seen: set[str] = set()

    for pattern in COMBINATION_PATTERNS:
        required_banks = [pattern_to_bank[pl] for pl in pattern if pl in pattern_to_bank and pattern_to_bank[pl] in wb and wb[pattern_to_bank[pl]]]
        if not required_banks:
            continue
        word_lists = [wb[b] for b in required_banks]
        for combo in itertools.product(*word_lists):
            kw = "".join(combo)
            kw_lower = kw.lower()
            if kw_lower in seen:
                continue
            is_similar = any(
                SequenceMatcher(None, kw_lower, ex).ratio() >= similarity_threshold
                for ex in seen
            )
            if not is_similar:
                seen.add(kw_lower)
                all_keywords.append(kw)
                if len(all_keywords) >= max_results:
                    return all_keywords
    return all_keywords[:max_results]


# ---- 关键词服务（含 LLM 调用） ----

class KeywordService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._llm = LLMService(db)

    async def save_keywords(self, keywords: list[str], brand: str = "") -> list[Keyword]:
        # 预处理：去空白、过滤空串、批次内去重
        seen_in_batch: set[str] = set()
        cleaned: list[str] = []
        for raw_kw in keywords:
            kw = raw_kw.strip() if isinstance(raw_kw, str) else ""
            if not kw:
                continue
            kw_lower = kw.lower()
            if kw_lower not in seen_in_batch:
                seen_in_batch.add(kw_lower)
                cleaned.append(kw)

        if not cleaned:
            return []

        # 查询数据库中已存在的关键词（空品牌时同时匹配 "" 和 NULL）
        if brand:
            existing_query = select(Keyword.keyword).where(Keyword.brand == brand)
        else:
            existing_query = select(Keyword.keyword).where(
                or_(Keyword.brand == "", Keyword.brand.is_(None))
            )
        existing_result = await self._db.execute(existing_query)
        existing_keywords = {(row[0] or "").strip().lower() for row in existing_result.all()}

        to_save: list[str] = []
        for kw in cleaned:
            kw_lower = kw.lower()
            if kw_lower not in existing_keywords:
                to_save.append(kw)
                existing_keywords.add(kw_lower)

        objs = [Keyword(keyword=kw, brand=brand) for kw in to_save]
        if objs:
            self._db.add_all(objs)
            await self._db.flush()
        return objs

    async def create_keywords(self, keywords: list[str], brand: str = "") -> dict[str, Any]:
        """
        批量创建关键词，自动去重（同品牌下大小写不敏感、去除首尾空白），
        校验长度，返回保存结果、跳过的重复数和错误列表。
        """
        # 预处理：去除空白、过滤空字符串
        cleaned: list[str] = []
        seen_in_batch: set[str] = set()
        errors: list[str] = []

        for raw_kw in keywords:
            kw = raw_kw.strip() if isinstance(raw_kw, str) else ""
            if not kw:
                continue
            # 长度校验
            err = validate_input_length(kw, "关键词", KEYWORD_MAX)
            if err:
                errors.append(f"'{kw}': {err}")
                continue
            kw_lower = kw.lower()
            if kw_lower not in seen_in_batch:
                seen_in_batch.add(kw_lower)
                cleaned.append(kw)

        if not cleaned:
            return {"saved": [], "duplicates_skipped": 0, "errors": errors}

        # 查询该品牌下已存在的关键词（大小写不敏感）；空品牌时需同时匹配 "" 和 NULL
        if brand:
            existing_query = select(Keyword.keyword).where(Keyword.brand == brand)
        else:
            existing_query = select(Keyword.keyword).where(
                or_(Keyword.brand == "", Keyword.brand.is_(None))
            )
        existing_result = await self._db.execute(existing_query)
        existing_keywords = {(row[0] or "").strip().lower() for row in existing_result.all()}

        to_save: list[str] = []
        duplicates_skipped = 0

        for kw in cleaned:
            kw_lower = kw.lower()
            if kw_lower in existing_keywords:
                duplicates_skipped += 1
            else:
                to_save.append(kw)
                existing_keywords.add(kw_lower)  # 防止同一批次内重复

        saved_objs: list[Keyword] = []
        if to_save:
            objs = [Keyword(keyword=kw, brand=brand) for kw in to_save]
            self._db.add_all(objs)
            await self._db.flush()
            saved_objs = objs

        return {
            "saved": saved_objs,
            "duplicates_skipped": duplicates_skipped,
            "errors": errors,
        }

    async def get_keywords(
        self,
        brand: str = "",
        page: int = 1,
        page_size: int = 20,
        is_favorite: Optional[bool] = None,
        tag: str = "",
        search: str = "",
    ) -> dict[str, Any]:
        query = select(Keyword)
        count_query = select(func.count(Keyword.id))

        if brand:
            query = query.where(Keyword.brand == brand)
            count_query = count_query.where(Keyword.brand == brand)

        if is_favorite is not None:
            query = query.where(Keyword.is_favorite == is_favorite)
            count_query = count_query.where(Keyword.is_favorite == is_favorite)

        if tag:
            tag_lower = tag.strip().lower()
            # 逗号分隔标签匹配：匹配独立标签（前后为逗号或开头/结尾）
            tag_patterns = [
                Keyword.tags == tag,
                Keyword.tags.like(f"{tag},%"),
                Keyword.tags.like(f"%,{tag},%"),
                Keyword.tags.like(f"%,{tag}"),
            ]
            query = query.where(or_(*tag_patterns))
            count_query = count_query.where(or_(*tag_patterns))

        if search:
            search_term = f"%{search}%"
            query = query.where(Keyword.keyword.like(search_term))
            count_query = count_query.where(Keyword.keyword.like(search_term))

        total = (await self._db.execute(count_query)).scalar() or 0
        query = (
            query.order_by(Keyword.created_at.desc())
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

    async def toggle_favorite(self, keyword_id: int) -> Optional[Keyword]:
        """切换关键词的收藏状态，返回更新后的关键词对象；若不存在则返回 None。"""
        obj = await self._db.get(Keyword, keyword_id)
        if obj is None:
            return None
        obj.is_favorite = not obj.is_favorite
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def set_tags(self, keyword_id: int, tags: list[str]) -> Optional[Keyword]:
        """
        设置关键词的标签列表（以逗号分隔存储，总长度不超过 500 字符）。
        返回更新后的关键词对象；若不存在则返回 None。
        """
        obj = await self._db.get(Keyword, keyword_id)
        if obj is None:
            return None

        # 清理每个标签：去除空白、过滤空标签、去重（保持顺序）
        cleaned_tags: list[str] = []
        seen_tags: set[str] = set()
        for t in tags:
            t_clean = t.strip() if isinstance(t, str) else ""
            if t_clean and t_clean.lower() not in seen_tags:
                seen_tags.add(t_clean.lower())
                cleaned_tags.append(t_clean)

        tags_str = ",".join(cleaned_tags)

        # 确保总长度不超过 500 字符：若超长则逐次移除最后一个标签直到符合限制
        while len(tags_str) > 500 and cleaned_tags:
            cleaned_tags.pop()
            tags_str = ",".join(cleaned_tags)

        obj.tags = tags_str if tags_str else None
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def search_keywords(
        self, query: str, brand: str = "", limit: int = 20
    ) -> list[Keyword]:
        """
        关键词搜索（用于自动补全/选择器）。
        按关键词文本 LIKE 匹配，可按品牌过滤，返回最多 limit 条结果。
        """
        stmt = select(Keyword)
        if brand:
            stmt = stmt.where(Keyword.brand == brand)
        search_term = f"%{query.strip()}%"
        stmt = stmt.where(Keyword.keyword.like(search_term))
        stmt = stmt.order_by(Keyword.created_at.desc()).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def import_keywords(self, keyword_ids: list[int], target_brand: str) -> dict[str, Any]:
        """
        将指定 ID 的关键词复制到目标品牌。
        若目标品牌下已存在相同关键词（大小写不敏感、去除空白），则跳过。
        返回导入数量、跳过数量统计。
        """
        if not keyword_ids:
            return {"imported": 0, "skipped": 0, "errors": ["未提供关键词ID"]}

        # 获取源关键词
        source_query = select(Keyword).where(Keyword.id.in_(keyword_ids))
        source_result = await self._db.execute(source_query)
        source_keywords = list(source_result.scalars().all())

        if not source_keywords:
            return {"imported": 0, "skipped": 0, "errors": ["未找到指定的关键词"]}

        # 查询目标品牌已有关键词（去重基准）
        existing_query = select(Keyword.keyword).where(Keyword.brand == target_brand)
        existing_result = await self._db.execute(existing_query)
        existing_set = {row[0].strip().lower() for row in existing_result.all()}

        imported_count = 0
        skipped_count = 0
        new_objs: list[Keyword] = []

        for src in source_keywords:
            kw_text = src.keyword.strip()
            kw_lower = kw_text.lower()
            if kw_lower in existing_set:
                skipped_count += 1
                continue
            new_obj = Keyword(
                keyword=src.keyword,
                brand=target_brand,
                is_favorite=False,
                tags=None,
            )
            new_objs.append(new_obj)
            existing_set.add(kw_lower)
            imported_count += 1

        if new_objs:
            self._db.add_all(new_objs)
            await self._db.flush()

        return {
            "imported": imported_count,
            "skipped": skipped_count,
            "errors": [],
        }

    async def delete_keyword(self, kw_id: int) -> bool:
        obj = await self._db.get(Keyword, kw_id)
        if obj:
            await self._db.delete(obj)
            await self._db.flush()
            return True
        return False

    async def delete_all(self, brand: str = "") -> int:
        if not brand:
            raise ValueError("brand 参数不能为空")
        query = select(Keyword).where(Keyword.brand == brand)
        result = await self._db.execute(query)
        objs = result.scalars().all()
        for o in objs:
            await self._db.delete(o)
        await self._db.flush()
        return len(objs)

    # ---- LLM 驱动的关键词操作 ----

    async def generate_llm_keywords(
        self,
        core_keyword: str,
        brand: str,
        advantages: str,
        cfg: LLMConfig,
        max_count: int = 30,
        polish: bool = True,
    ) -> AsyncGenerator[str, None]:
        """LLM 生成关键词（流式）"""
        prompt = KEYWORD_GENERATE_PROMPT.format(
            brand=brand, advantages=advantages,
            core_keyword=core_keyword, max_count=max_count,
        )
        full_response: list[str] = []
        async for chunk in self._llm.stream(prompt, cfg):
            full_response.append(chunk)
            yield chunk

        # 解析并保存
        result_text = "".join(full_response)
        kws = extract_json(result_text)
        if isinstance(kws, list):
            await self.save_keywords([str(k) for k in kws if k], brand)

    async def mine_keywords(
        self, keyword: str, brand: str, cfg: LLMConfig
    ) -> AsyncGenerator[str, None]:
        """竞品关键词挖掘（流式）"""
        prompt = KEYWORD_MINE_PROMPT.format(keyword=keyword, brand=brand)
        async for chunk in self._llm.stream(prompt, cfg):
            yield chunk

    async def expand_keywords(
        self, keywords: list[str], brand: str, cfg: LLMConfig
    ) -> AsyncGenerator[str, None]:
        """语义扩展（流式）"""
        prompt = KEYWORD_EXPAND_PROMPT.format(
            keywords_json=json.dumps(keywords, ensure_ascii=False), brand=brand
        )
        async for chunk in self._llm.stream(prompt, cfg):
            yield chunk

    async def cluster_keywords(
        self, keywords: list[str], brand: str, cfg: LLMConfig
    ) -> dict[str, Any]:
        """话题聚类（同步返回完整结果）"""
        prompt = KEYWORD_CLUSTER_PROMPT.format(
            keywords_json=json.dumps(keywords, ensure_ascii=False), brand=brand
        )
        result = await self._llm.invoke(prompt, cfg, use_cache=True, operation_type="cluster", brand=brand)
        parsed = extract_json(result)
        if isinstance(parsed, dict):
            return parsed
        return {"clusters": [], "summary": result}
