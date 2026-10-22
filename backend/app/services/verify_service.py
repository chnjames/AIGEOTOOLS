"""AI 搜索验证服务 - 从 ai_search_verifier.py/negative_monitor.py 迁移"""
from __future__ import annotations

import json
import re
from typing import Any, AsyncGenerator, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.verify_result import VerifyResult
from app.prompts.verify_prompts import (
    VERIFY_BRAND_PROMPT, NATURAL_VERIFY_PROMPT, DIAGNOSIS_PROMPT, COMPETITOR_VERIFY_PROMPT,
)
from app.services.llm_factory import get_default_model
from app.services.llm_service import LLMService, LLMConfig
from app.utils.llm_errors import classify_llm_error, enforce_rate_limit
from app.utils.text_utils import extract_json

logger = get_logger(__name__)

# 验证调用的单模型超时时间（秒）
VERIFY_TIMEOUT = 90
# 模型间速率限制间隔（秒）
MODEL_CALL_INTERVAL = 1.0


def _extract_int(text: str, pattern: str, default: int = 0) -> int:
    """从文本中提取数字，返回整数"""
    m = re.search(pattern, text)
    if m:
        try:
            return int(m.group(1))
        except (ValueError, IndexError):
            pass
    return default


def _extract_field(text: str, label: str) -> str:
    """从分析文本中提取指定字段的值，支持中文冒号和英文冒号"""
    pattern = rf"-\s*{re.escape(label)}[：:]\s*(.+)"
    m = re.search(pattern, text)
    if m:
        val = m.group(1).strip()
        # 去掉行尾可能的注释
        val = re.split(r"\s+（", val)[0].strip()
        return val
    return ""


def _generate_brand_variants(brand: str) -> list[str]:
    """生成品牌名称的常见变体，用于提高 AI 搜索验证的召回率

    处理的变体类型：
    - 去除公司后缀（有限公司/股份/科技/集团/Inc/Ltd/Corp 等）
    - 英文名大小写变体（全小写/首字母大写）
    - 去除首尾空格
    """
    if not brand:
        return []

    variants: set[str] = {brand}
    b = brand.strip()

    # 中文公司后缀
    cn_suffixes = [
        "股份有限公司", "有限责任公司", "有限公司", "科技有限公司",
        "股份公司", "集团有限公司", "科技集团", "科技",
        "集团", "公司", "互联", "网络", "信息", "软件",
    ]
    # 英文公司后缀
    en_suffixes = [
        "Inc.", "Inc", "LLC", "Ltd.", "Ltd", "Corp.", "Corp",
        "Co., Ltd.", "Co.,Ltd", "Co.", "Co", "Group",
    ]

    # 去除中文后缀
    for suffix in cn_suffixes:
        if b.endswith(suffix) and len(b) > len(suffix):
            variants.add(b[:-len(suffix)].strip())

    # 去除英文后缀（大小写不敏感）
    for suffix in en_suffixes:
        if b.lower().endswith(suffix.lower()) and len(b) > len(suffix) + 1:
            stripped = b[:-len(suffix)].strip().rstrip(",. ")
            if stripped:
                variants.add(stripped)

    # 英文品牌的大小写变体
    if any(c.isascii() and c.isalpha() for c in b):
        ascii_part = b.strip()
        variants.add(ascii_part.lower())
        variants.add(ascii_part.upper())
        # 驼峰/首字母大写
        if len(ascii_part) > 1:
            variants.add(ascii_part[0].upper() + ascii_part[1:].lower())

    # 过滤空串和过短的变体（避免单字误匹配）
    return sorted([v for v in variants if len(v) >= 2], key=len, reverse=True)


def _find_brand_mention(text: str, brand: str) -> tuple[bool, int, str]:
    """在文本中查找品牌名（含变体），返回 (是否提及, 最早出现位置, 匹配到的变体)"""
    if not brand:
        return False, -1, ""

    variants = _generate_brand_variants(brand)
    earliest_idx = len(text)
    matched_variant = ""

    for variant in variants:
        if len(variant) < 2:
            continue
        # 英文用大小写不敏感匹配，中文直接匹配
        if all(ord(c) < 128 for c in variant):
            pattern = re.compile(re.escape(variant), re.IGNORECASE)
            m = pattern.search(text)
            if m and m.start() < earliest_idx:
                earliest_idx = m.start()
                matched_variant = variant
        else:
            idx = text.find(variant)
            if idx != -1 and idx < earliest_idx:
                earliest_idx = idx
                matched_variant = variant

    if earliest_idx < len(text):
        return True, earliest_idx, matched_variant
    return False, -1, ""


def parse_verify_result(response_text: str, brand: str, model: str, query: str) -> dict[str, Any]:
    """解析 LLM 验证响应，提取品牌分析（支持品牌名变体检测）"""
    # 使用变体检测查找品牌提及
    is_mentioned, earliest_idx, matched_variant = _find_brand_mention(response_text, brand)

    # 统计所有变体的提及次数
    mention_count = 0
    if brand:
        variants = _generate_brand_variants(brand)
        for v in variants:
            if len(v) < 2:
                continue
            if all(ord(c) < 128 for c in v):
                mention_count += len(re.findall(re.escape(v), response_text, re.IGNORECASE))
            else:
                mention_count += response_text.count(v)

    # 基于最早提及位置判断位置区域
    position = "未提及"
    if is_mentioned and earliest_idx >= 0:
        ratio = earliest_idx / len(response_text) if response_text else 1
        if ratio < 0.33:
            position = "开头前1/3"
        elif ratio < 0.66:
            position = "中间1/3"
        else:
            position = "末尾1/3"

    # 默认值
    sentiment: Optional[str] = None
    positive_mentions = 0
    negative_mentions = 0
    recommended_brands_str: Optional[str] = None

    # 提取---品牌分析---部分（兼容 "品牌分析：" 和 "品牌分析---" 两种分隔格式）
    analysis = ""
    analysis_match = re.search(r"---\s*品牌分析\s*[-—：:\s]*\n([\s\S]*)", response_text)
    if analysis_match:
        analysis = analysis_match.group(1).strip()

        # 从分析中解析是否提及（LLM 的明确判断优先于字符串匹配）
        mentioned_match = re.search(r"是否提及[【\[][^】\]]+[】\]]?[：:]\s*(是|否)", analysis)
        if mentioned_match:
            is_mentioned = (mentioned_match.group(1) == "是")

        # 提取提及次数（从分析中优先）
        mention_count_analysis = _extract_int(analysis, r"提及次数[：:]\s*(\d+)", mention_count)
        if mention_count_analysis > 0:
            mention_count = mention_count_analysis

        # 提取正面/负面提及次数
        positive_mentions = _extract_int(analysis, r"正面提及次数[：:]\s*(\d+)", 0)
        negative_mentions = _extract_int(analysis, r"负面提及次数[：:]\s*(\d+)", 0)

        # 提取提及位置
        pos_val = _extract_field(analysis, "提及位置")
        if pos_val and pos_val != "未提及":
            position = pos_val
        elif pos_val == "未提及":
            position = "未提及"

        # 提取情感倾向
        sent_val = _extract_field(analysis, "整体情感倾向")
        if sent_val:
            sent_map = {"正面": "positive", "中性": "neutral", "负面": "negative", "未提及": None}
            sentiment = sent_map.get(sent_val, sent_val if sent_val not in ("未提及",) else None)

        # 提取被推荐的品牌列表
        rec_val = _extract_field(analysis, "被推荐的品牌列表")
        if rec_val:
            # 清理无推荐的情况
            if rec_val in ("无", "暂无", "未提及", "<品牌名1, 品牌名2, ...>"):
                recommended_brands_str = None
            else:
                recommended_brands_str = rec_val

    # 提取包含品牌（或变体）的片段
    snippet = ""
    search_target = matched_variant or brand
    if search_target:
        for line in response_text.split("\n"):
            if all(ord(c) < 128 for c in search_target):
                if re.search(re.escape(search_target), line, re.IGNORECASE):
                    snippet = line.strip()[:200]
                    break
            elif search_target in line:
                snippet = line.strip()[:200]
                break

    return {
        "query": query,
        "brand": brand,
        "verify_model": model,
        "mention_count": mention_count,
        "positive_mentions": positive_mentions,
        "negative_mentions": negative_mentions,
        "mention_position": position,
        "content_snippet": snippet or response_text[:200],
        "is_mentioned": is_mentioned,
        "sentiment": sentiment,
        "recommended_brands": recommended_brands_str,
        "matched_variant": matched_variant if matched_variant and matched_variant != brand else None,
        "full_response": response_text,
    }


class VerifyService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._llm = LLMService(db)

    async def get_results(self, brand: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
        query = select(VerifyResult)
        count_query = select(func.count(VerifyResult.id))
        if brand:
            query = query.where(VerifyResult.brand == brand)
            count_query = count_query.where(VerifyResult.brand == brand)
        total = (await self._db.execute(count_query)).scalar() or 0
        query = query.order_by(VerifyResult.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._db.execute(query)
        items = list(result.scalars().all())
        return {
            "items": items, "total": total, "page": page, "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    async def delete_result(self, rid: int) -> bool:
        obj = await self._db.get(VerifyResult, rid)
        if obj:
            await self._db.delete(obj)
            await self._db.flush()
            return True
        return False

    async def verify_brand_stream(
        self,
        query: str,
        brand: str,
        provider_configs: dict[str, str],  # {provider: api_key}
        temperature: float = 0.7,
        mode: str = "natural",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """多模型品牌验证（流式，逐个模型输出结果）

        mode: "natural" - 自然模式，问题中不提及品牌，只在分析指令中检查
              "prompted" - 提示模式，问题中提示关注品牌（传统模式）

        Yields events: start, model_start, chunk, model_complete, model_error, complete
        """
        # 过滤掉无 API Key 的提供商
        valid_configs = {p: k for p, k in provider_configs.items() if k}
        total_models = len(valid_configs)

        yield {"event": "start", "data": {
            "query": query, "brand": brand, "mode": mode, "total": total_models,
        }}

        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        success_count = 0
        failed_count = 0

        for idx, (provider, api_key) in enumerate(valid_configs.items()):
            model = get_default_model(provider)
            cfg = LLMConfig(
                provider=provider, api_key=api_key, model=model,
                temperature=temperature, timeout=VERIFY_TIMEOUT,
            )

            # 根据模式选择 prompt
            if mode == "natural":
                prompt = NATURAL_VERIFY_PROMPT.format(query=query, brand=brand)
            else:
                prompt = VERIFY_BRAND_PROMPT.format(query=query, brand=brand)

            # 速率限制：避免在连续调用时触发 429
            await enforce_rate_limit(provider, MODEL_CALL_INTERVAL)

            yield {"event": "model_start", "data": {
                "step": idx + 1, "total": total_models,
                "provider": provider, "model": model,
                "message": f"正在使用 {provider} 验证...",
            }}

            response_chunks: list[str] = []
            stream_completed = False
            diagnosis_text: Optional[str] = None

            try:
                # ---- 流式调用主 LLM ----
                async for chunk in self._llm.stream(prompt, cfg):
                    response_chunks.append(chunk)
                    yield {"event": "chunk", "data": {
                        "provider": provider, "model": model, "content": chunk,
                    }}

                full_response = "".join(response_chunks)
                stream_completed = True

                if not full_response.strip():
                    raise ValueError(f"{provider} 返回了空响应")

                parsed = parse_verify_result(full_response, brand, model, query)

                # ---- 品牌未提及时，调用诊断 prompt ----
                if not parsed["is_mentioned"]:
                    try:
                        yield {"event": "model_start", "data": {
                            "step": idx + 1, "total": total_models,
                            "provider": provider, "model": model,
                            "message": f"正在分析 {provider} 未提及原因...",
                        }}
                        diag_prompt = DIAGNOSIS_PROMPT.format(
                            query=query, brand=brand, response=full_response,
                        )
                        diag_raw = await self._llm.invoke(diag_prompt, cfg, use_cache=False, record_cost=True, operation_type="verify_diag", brand=brand)
                        diagnosis_json = extract_json(diag_raw)
                        if diagnosis_json:
                            diagnosis_text = json.dumps(diagnosis_json, ensure_ascii=False)
                        else:
                            diagnosis_text = diag_raw
                    except Exception as diag_err:
                        logger.warning("Diagnosis failed for %s: %s", provider, diag_err)
                        diagnosis_text = None

                # ---- 保存到数据库（含 full_response）----
                vr = VerifyResult(
                    query=query, brand=brand, verify_model=provider,
                    mention_count=parsed["mention_count"],
                    positive_mentions=parsed["positive_mentions"],
                    negative_mentions=parsed["negative_mentions"],
                    mention_position=parsed["mention_position"],
                    content_snippet=parsed["content_snippet"],
                    full_response=parsed["full_response"],
                    is_mentioned=parsed["is_mentioned"],
                    sentiment=parsed["sentiment"],
                    verification_mode=mode,
                    diagnosis=diagnosis_text,
                    recommended_brands=parsed["recommended_brands"],
                )
                self._db.add(vr)
                await self._db.flush()

                # ---- 汇总结果 ----
                result_entry = {
                    "provider": provider,
                    "model": model,
                    "result": {k: v for k, v in parsed.items() if k != "full_response"},
                }
                if diagnosis_text:
                    result_entry["diagnosis"] = diagnosis_text
                results.append(result_entry)
                success_count += 1

                yield {"event": "model_complete", "data": result_entry}

            except Exception as e:
                # 错误分类：将原始异常转换为用户友好的标准错误
                classified = classify_llm_error(
                    e, provider=provider, model=model, timeout=VERIFY_TIMEOUT,
                )
                error_msg = classified.message
                logger.error("Verify failed for %s: %s", provider, error_msg)

                error_entry = {
                    "provider": provider,
                    "model": model,
                    "error": error_msg,
                    "error_type": classified.error_type,
                }
                errors.append(error_entry)
                failed_count += 1

                # 如果流中途失败，记录已有的部分响应（如有）
                partial_response = "".join(response_chunks) if response_chunks else ""
                if partial_response.strip() and not stream_completed:
                    try:
                        vr = VerifyResult(
                            query=query, brand=brand, verify_model=provider,
                            mention_count=0, positive_mentions=0, negative_mentions=0,
                            mention_position="未提及",
                            content_snippet=partial_response[:200],
                            full_response=partial_response,
                            is_mentioned=False, sentiment=None,
                            verification_mode=mode,
                            diagnosis=json.dumps({"error": error_msg}, ensure_ascii=False),
                            recommended_brands=None,
                        )
                        self._db.add(vr)
                        await self._db.flush()
                    except Exception as save_err:
                        logger.warning("Failed to save partial response for %s: %s", provider, save_err)

                yield {"event": "model_error", "data": error_entry}

        yield {"event": "complete", "data": {
            "query": query,
            "brand": brand,
            "mode": mode,
            "total": total_models,
            "success": success_count,
            "failed": failed_count,
            "results": results,
            "errors": errors,
        }}

    async def verify_competitor_stream(
        self,
        query: str,
        brand: str,
        competitors: list[str],
        provider_configs: dict[str, str],
        temperature: float = 0.7,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """竞品对比验证（流式）

        Yields events: start, model_start, chunk, model_complete, model_error, complete
        """
        valid_configs = {p: k for p, k in provider_configs.items() if k}
        total_models = len(valid_configs)
        comp_str = "、".join(competitors) if competitors else "无"

        yield {"event": "start", "data": {
            "query": query, "brand": brand, "competitors": competitors, "total": total_models,
        }}

        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        success_count = 0
        failed_count = 0

        for idx, (provider, api_key) in enumerate(valid_configs.items()):
            model = get_default_model(provider)
            cfg = LLMConfig(
                provider=provider, api_key=api_key, model=model,
                temperature=temperature, timeout=VERIFY_TIMEOUT,
            )
            prompt = COMPETITOR_VERIFY_PROMPT.format(
                query=query, brand=brand, competitors=comp_str,
            )

            # 速率限制
            await enforce_rate_limit(provider, MODEL_CALL_INTERVAL)

            yield {"event": "model_start", "data": {
                "step": idx + 1, "total": total_models,
                "provider": provider, "model": model,
                "message": f"正在使用 {provider} 验证竞品...",
            }}

            chunks: list[str] = []
            stream_completed = False
            try:
                async for chunk in self._llm.stream(prompt, cfg):
                    chunks.append(chunk)
                    yield {"event": "chunk", "data": {
                        "provider": provider, "model": model, "content": chunk,
                    }}

                full = "".join(chunks)
                stream_completed = True
                if not full.strip():
                    raise ValueError(f"{provider} 返回了空响应")

                parsed = parse_verify_result(full, brand, model, query)

                # ---- 持久化到数据库 ----
                try:
                    vr = VerifyResult(
                        query=query, brand=brand, verify_model=provider,
                        mention_count=parsed["mention_count"],
                        positive_mentions=parsed["positive_mentions"],
                        negative_mentions=parsed["negative_mentions"],
                        mention_position=parsed["mention_position"],
                        content_snippet=parsed["content_snippet"],
                        full_response=parsed["full_response"],
                        is_mentioned=parsed["is_mentioned"],
                        sentiment=parsed["sentiment"],
                        verification_mode="competitor",
                        recommended_brands=parsed["recommended_brands"],
                    )
                    self._db.add(vr)
                    await self._db.flush()
                except Exception as save_err:
                    logger.warning(
                        "Failed to persist competitor verify result for %s: %s",
                        provider, save_err,
                    )

                result_entry = {
                    "provider": provider,
                    "model": model,
                    "result": {k: v for k, v in parsed.items() if k != "full_response"},
                    "full_response": full,
                }
                results.append(result_entry)
                success_count += 1

                yield {"event": "model_complete", "data": result_entry}

            except Exception as e:
                classified = classify_llm_error(
                    e, provider=provider, model=model, timeout=VERIFY_TIMEOUT,
                )
                error_msg = classified.message
                logger.error("Competitor verify failed for %s: %s", provider, error_msg)

                error_entry = {
                    "provider": provider,
                    "model": model,
                    "error": error_msg,
                    "error_type": classified.error_type,
                }
                errors.append(error_entry)
                failed_count += 1

                # 保存部分响应（如有）
                partial_response = "".join(chunks) if chunks else ""
                if partial_response.strip() and not stream_completed:
                    try:
                        vr = VerifyResult(
                            query=query, brand=brand, verify_model=provider,
                            mention_count=0, positive_mentions=0, negative_mentions=0,
                            mention_position="未提及",
                            content_snippet=partial_response[:200],
                            full_response=partial_response,
                            is_mentioned=False, sentiment=None,
                            verification_mode="competitor",
                            diagnosis=json.dumps({"error": error_msg}, ensure_ascii=False),
                            recommended_brands=None,
                        )
                        self._db.add(vr)
                        await self._db.flush()
                    except Exception as save_err:
                        logger.warning(
                            "Failed to save partial competitor response for %s: %s",
                            provider, save_err,
                        )

                yield {"event": "model_error", "data": error_entry}

        yield {"event": "complete", "data": {
            "query": query,
            "brand": brand,
            "total": total_models,
            "success": success_count,
            "failed": failed_count,
            "results": results,
            "errors": errors,
        }}

    async def get_negative_mentions(self, brand: str = "") -> list[dict[str, Any]]:
        """负面提及监控（简单规则+LLM结果分析）"""
        query = select(VerifyResult).where(
            (VerifyResult.is_mentioned == False) |
            (VerifyResult.sentiment == "negative")
        )
        if brand:
            query = query.where(VerifyResult.brand == brand)
        result = await self._db.execute(query.order_by(VerifyResult.created_at.desc()).limit(50))
        items = result.scalars().all()
        return [
            {
                "id": r.id, "query": r.query, "brand": r.brand,
                "verify_model": r.verify_model, "snippet": r.content_snippet,
                "is_negative": (r.sentiment == "negative") if r.sentiment else (not r.is_mentioned),
                "sentiment": r.sentiment,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in items
        ]
