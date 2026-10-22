"""工作流自动化服务 - 从 workflow_automation.py 迁移"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import WorkflowError
from app.core.logging import get_logger
from app.models.workflow import Workflow, WorkflowExecution, WorkflowTemplate
from app.prompts.article_prompts import ARTICLE_GENERATE_PROMPT
from app.services.article_service import ArticleService, get_platform_style, KNOWLEDGE_CONTEXT_INSTRUCTION
from app.services.keyword_service import KeywordService, generate_combinations
from app.services.llm_service import LLMConfig, LLMService
from app.services.optimization_service import OptimizationService
from app.services.verify_service import VerifyService
from app.services.config_service import ConfigService

logger = get_logger(__name__)

# 内置工作流模板
BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "full-pipeline",
        "name": "完整 GEO 工作流",
        "description": "关键词生成→内容创作→优化→验证的完整闭环",
        "steps": [
            {"step_type": "generate_keywords", "name": "关键词生成", "config": {"count": 10}},
            {"step_type": "generate_content", "name": "内容创作", "config": {"platforms": ["知乎", "CSDN"]}},
            {"step_type": "optimize", "name": "E-E-A-T增强", "config": {"type": "eeat"}},
            {"step_type": "verify", "name": "多模型验证", "config": {"providers": ["DeepSeek"]}},
        ],
    },
    {
        "id": "content-only",
        "name": "快速内容生成",
        "description": "基于已有关键词快速生成多平台内容",
        "steps": [
            {"step_type": "generate_content", "name": "批量内容生成", "config": {"platforms": ["知乎", "小红书", "CSDN"]}},
        ],
    },
    {
        "id": "verify-only",
        "name": "品牌验证",
        "description": "对关键词进行多模型品牌提及验证",
        "steps": [
            {"step_type": "verify", "name": "多模型验证", "config": {"providers": ["DeepSeek"]}},
        ],
    },
]


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def _ensure_templates(self) -> None:
        for tpl in BUILTIN_TEMPLATES:
            existing = await self._db.get(WorkflowTemplate, tpl["id"])
            if not existing:
                self._db.add(WorkflowTemplate(
                    id=tpl["id"], name=tpl["name"],
                    description=tpl["description"],
                    steps=json.dumps(tpl["steps"], ensure_ascii=False),
                ))
        await self._db.flush()

    async def get_templates(self) -> list[dict[str, Any]]:
        await self._ensure_templates()
        result = await self._db.execute(select(WorkflowTemplate))
        return [
            {
                "id": t.id, "name": t.name, "description": t.description,
                "steps": json.loads(t.steps) if t.steps else [],
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in result.scalars().all()
        ]

    async def create_workflow(self, name: str, steps: list[dict], brand: str = "",
                              schedule: Optional[str] = None,
                              conditions: Optional[dict] = None) -> Workflow:
        wf_id = str(uuid.uuid4())[:8]
        wf = Workflow(
            id=wf_id, name=name,
            steps=json.dumps(steps, ensure_ascii=False),
            schedule=schedule,
            conditions=json.dumps(conditions, ensure_ascii=False) if conditions else None,
            brand=brand, enabled=True,
        )
        self._db.add(wf)
        await self._db.flush()
        return wf

    async def get_workflows(self, brand: str = "") -> list[Workflow]:
        query = select(Workflow)
        if brand:
            query = query.where(Workflow.brand == brand)
        result = await self._db.execute(query.order_by(Workflow.created_at.desc()))
        return list(result.scalars().all())

    async def get_workflow(self, wf_id: str) -> Optional[Workflow]:
        return await self._db.get(Workflow, wf_id)

    async def update_workflow(self, wf_id: str, **kwargs: Any) -> Optional[Workflow]:
        wf = await self._db.get(Workflow, wf_id)
        if not wf:
            return None
        if "steps" in kwargs and kwargs["steps"] is not None:
            kwargs["steps"] = json.dumps(kwargs["steps"], ensure_ascii=False)
        if "conditions" in kwargs and kwargs["conditions"] is not None:
            kwargs["conditions"] = json.dumps(kwargs["conditions"], ensure_ascii=False)
        for k, v in kwargs.items():
            if hasattr(wf, k) and v is not None:
                setattr(wf, k, v)
        await self._db.flush()
        return wf

    async def delete_workflow(self, wf_id: str) -> bool:
        wf = await self._db.get(Workflow, wf_id)
        if wf:
            await self._db.delete(wf)
            await self._db.flush()
            return True
        return False

    async def get_executions(self, wf_id: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        query = select(WorkflowExecution).where(WorkflowExecution.workflow_id == wf_id)
        count_query = select(func.count(WorkflowExecution.id)).where(WorkflowExecution.workflow_id == wf_id)
        total = (await self._db.execute(count_query)).scalar() or 0
        query = query.order_by(WorkflowExecution.started_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._db.execute(query)
        items = list(result.scalars().all())
        return {
            "items": items, "total": total, "page": page, "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    async def execute_stream(
        self, wf_id: str, brand: str, advantages: str,
        keywords: Optional[list[str]] = None,
        platforms: Optional[list[str]] = None,
        temperature: float = 0.7,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """执行工作流（流式进度通知）"""
        wf = await self.get_workflow(wf_id)
        if not wf:
            raise WorkflowError(f"工作流不存在: {wf_id}")

        steps = json.loads(wf.steps) if wf.steps else []
        total_steps = len(steps)

        # 创建执行记录
        execution = WorkflowExecution(
            workflow_id=wf_id, status="running",
            started_at=datetime.now(timezone.utc),
            progress=0.0, logs=json.dumps([], ensure_ascii=False),
        )
        self._db.add(execution)
        await self._db.flush()
        exec_id = execution.id

        logs: list[str] = []
        results: dict[str, Any] = {}
        had_error = False
        error_messages: list[str] = []

        yield {"event": "start", "data": {"execution_id": exec_id, "total_steps": total_steps, "workflow": wf.name}}

        kw_svc = KeywordService(self._db)
        art_svc = ArticleService(self._db)
        llm_svc = LLMService(self._db)
        cfg = LLMConfig(provider=provider, api_key=api_key, temperature=temperature)

        for step_idx, step in enumerate(steps):
            step_type = step.get("step_type", "")
            step_name = step.get("name", step_type)
            config = step.get("config", {})
            progress = (step_idx / total_steps) * 100 if total_steps > 0 else 0

            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 开始执行: {step_name}")
            yield {"event": "progress", "data": {
                "progress": round(progress, 1),
                "step": step_idx + 1, "total_steps": total_steps,
                "step_name": step_name, "message": f"正在执行: {step_name}"
            }}

            try:
                if step_type == "generate_keywords":
                    count = config.get("count", 10)
                    core_kw = (keywords[0] if keywords else brand) or "工具"
                    combo_kws = generate_combinations(
                        core_keyword=core_kw, max_results=count
                    )
                    saved = await kw_svc.save_keywords(combo_kws, brand)
                    results["keywords"] = [k.keyword for k in saved]
                    logs.append(f"生成了 {len(saved)} 个关键词")

                elif step_type == "generate_content":
                    plats = platforms or config.get("platforms", ["知乎"])
                    kws = keywords or results.get("keywords", [brand])
                    articles_created = 0
                    created_article_ids: list[int] = []
                    knowledge_ctx = config.get("knowledge_context", "")
                    knowledge_instr = KNOWLEDGE_CONTEXT_INSTRUCTION.format(knowledge_content=knowledge_ctx) if knowledge_ctx else ""
                    for kw in kws[:5]:
                        for plat in plats:
                            try:
                                prompt = ARTICLE_GENERATE_PROMPT.format(
                                    brand=brand, advantages=advantages,
                                    keyword=kw, platform=plat,
                                    knowledge_context=knowledge_instr,
                                    word_count=1000,
                                    style_instruction=get_platform_style(plat),
                                )
                                chunks: list[str] = []
                                async for chunk in llm_svc.stream(prompt, cfg):
                                    chunks.append(chunk)
                                content = "".join(chunks)
                                article = await art_svc.save_article(kw, plat, content, brand=brand)
                                if article and article.id:
                                    created_article_ids.append(article.id)
                                articles_created += 1
                            except Exception as e:
                                logs.append(f"生成 {plat}/{kw} 失败: {e}")
                    results["articles_created"] = articles_created
                    results["article_ids"] = created_article_ids
                    logs.append(f"生成了 {articles_created} 篇内容")

                elif step_type == "optimize":
                    opt_type = config.get("type", "eeat")
                    opt_svc = OptimizationService(self._db)
                    # 获取本次工作流生成的文章（或数据库中最新的文章）
                    art_ids = results.get("article_ids", [])
                    if not art_ids:
                        from app.models.article import Article
                        recent = await self._db.execute(
                            select(Article).where(Article.brand == brand).order_by(Article.created_at.desc()).limit(3)
                        )
                        recent_articles = list(recent.scalars().all())
                    else:
                        from app.models.article import Article
                        recent = await self._db.execute(select(Article).where(Article.id.in_(art_ids)))
                        recent_articles = list(recent.scalars().all())
                    optimized_count = 0
                    for art in recent_articles[:3]:
                        try:
                            chunks_opt: list[str] = []
                            gen = opt_svc.enhance_eeat(
                                content=art.content, brand=brand, advantages=advantages,
                                platform=art.platform or "", cfg=cfg, article_id=art.id,
                            )
                            async for chunk in gen:
                                chunks_opt.append(chunk)
                            optimized_count += 1
                            logs.append(f"E-E-A-T 优化完成: {art.keyword} ({art.platform})")
                        except Exception as e:
                            logs.append(f"优化 {art.keyword} 失败: {e}")
                    results["optimized"] = optimized_count
                    results["optimization_count"] = optimized_count
                    logs.append(f"完成 {optimized_count} 篇文章 E-E-A-T 优化")

                elif step_type == "verify":
                    kws = keywords or results.get("keywords", [brand])
                    # 构建 provider_configs
                    cfg_svc = ConfigService(self._db)
                    saved_cfg = await cfg_svc.get_config()
                    prov_cfgs: dict[str, str] = {}
                    verify_providers = config.get("providers", saved_cfg.get("verify_providers", [provider or "DeepSeek"]))
                    saved_keys = saved_cfg.get("verify_keys", {})
                    for vp in verify_providers:
                        key = saved_keys.get(vp, "")
                        if vp == provider and api_key:
                            key = api_key
                        if key:
                            prov_cfgs[vp] = key
                    verify_svc = VerifyService(self._db)
                    verified = 0
                    verification_results: list[dict[str, Any]] = []
                    for kw in kws[:3]:
                        try:
                            gen = verify_svc.verify_brand_stream(
                                query=kw, brand=brand, provider_configs=prov_cfgs,
                                temperature=temperature,
                            )
                            async for evt in gen:
                                evt_type = evt.get("event")
                                evt_data = evt.get("data", {}) or {}
                                if evt_type == "model_complete":
                                    verified += 1
                                    # 收集结构化验证结果摘要（仅保留可序列化的标量/简单字段）
                                    parsed = evt_data.get("result", {}) or {}
                                    verification_results.append({
                                        "keyword": kw,
                                        "provider": evt_data.get("provider"),
                                        "model": evt_data.get("model"),
                                        "is_mentioned": parsed.get("is_mentioned"),
                                        "mention_count": parsed.get("mention_count", 0),
                                        "sentiment": parsed.get("sentiment"),
                                        "mention_position": parsed.get("mention_position"),
                                    })
                                elif evt_type == "model_error":
                                    verification_results.append({
                                        "keyword": kw,
                                        "provider": evt_data.get("provider"),
                                        "model": evt_data.get("model"),
                                        "error": evt_data.get("error"),
                                        "error_type": evt_data.get("error_type"),
                                    })
                            logs.append(f"验证关键词: {kw} 完成")
                        except Exception as e:
                            logs.append(f"验证 {kw} 失败: {e}")
                    results["verified"] = verified
                    results["verification_count"] = verified
                    results["verification_results"] = verification_results
                    logs.append(f"完成 {verified} 次品牌提及验证")

                else:
                    logs.append(f"未知步骤类型: {step_type}，跳过")

                logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 完成: {step_name}")

            except Exception as e:
                err_msg = f"步骤 {step_name} 执行失败: {e}"
                logger.error(err_msg)
                logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 错误: {err_msg}")
                had_error = True
                error_messages.append(err_msg)
                yield {"event": "step_error", "data": {"step": step_name, "error": str(e)}}

            # 每个主要步骤后持久化中间结果（execution.result/logs/progress），
            # 既防止单 session 跨多步长事务的 session 污染（M6），
            # 也实现步骤间中间结果持久化（L5）。
            try:
                execution.progress = round(((step_idx + 1) / total_steps) * 100, 1) if total_steps > 0 else 100.0
                execution.result = json.dumps(results, ensure_ascii=False)
                execution.logs = json.dumps(logs, ensure_ascii=False)
                await self._db.flush()
            except Exception as flush_err:
                logger.warning("Failed to persist intermediate workflow result: %s", flush_err)

        # 完成
        # 将 errors 和 logs 注入 results，使 complete 事件返回结构化 JSON
        # （logs 同步保留在 data 顶层以兼容已有消费端）
        results["errors"] = list(error_messages)
        results["logs"] = list(logs)

        execution.status = "failed" if had_error else "completed"
        execution.progress = 100.0
        execution.completed_at = datetime.now(timezone.utc)
        execution.result = json.dumps(results, ensure_ascii=False)
        execution.logs = json.dumps(logs, ensure_ascii=False)
        if had_error:
            execution.error = "; ".join(error_messages)
        await self._db.flush()

        yield {"event": "complete", "data": {
            "execution_id": exec_id, "progress": 100.0,
            "results": results, "logs": logs,
            "status": execution.status,
        }}
