"""内容评分 API"""
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_scoring_service, get_config_service, require_api_key
from app.api.sse import create_sse_response, llm_stream_to_sse
from app.schemas.common import ApiResponse
from app.schemas.roi import (
    ScoreRequest, MetricsRequest, MetricsResponse, QuickScoreResponse,
)
from app.services.scoring_service import ScoringService, quick_assessment, analyze_metrics
from app.services.config_service import ConfigService
from app.services.llm_service import LLMConfig
from app.services.llm_factory import get_default_model
from app.utils.text_utils import extract_json

router = APIRouter(prefix="/scoring", tags=["内容评分"])


async def _resolve_cfg(req: Any, config_svc: ConfigService) -> LLMConfig:
    cfg = await config_svc.get_config()
    provider = getattr(req, "provider", None) or cfg.get("gen_provider", "DeepSeek")
    api_key = getattr(req, "api_key", None) or cfg.get("gen_api_key", "")
    model = getattr(req, "model", None) or get_default_model(provider)
    temp = getattr(req, "temperature", 0.7) or cfg.get("temperature", 0.7)
    return LLMConfig(provider=provider, api_key=api_key, model=model, temperature=temp)


@router.post("/score")
async def score_content(
    req: ScoreRequest,
    svc: ScoringService = Depends(get_scoring_service),
    config_svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    """LLM 4维度评分（SSE 流式）"""
    cfg = await _resolve_cfg(req, config_svc)
    gcfg = await config_svc.get_config()
    brand = req.brand or gcfg.get("brand", "")
    advantages = req.advantages or gcfg.get("advantages", "")

    async def _stream():
        yield {"event": "start", "data": {"message": "开始评分..."}}
        full = []
        async for chunk in svc.score_content_stream(req.content, brand, advantages, req.platform, cfg):
            full.append(chunk)
            yield {"event": "chunk", "data": {"content": chunk}}
        result_text = "".join(full)
        parsed = extract_json(result_text)
        yield {"event": "complete", "data": {"result": parsed if isinstance(parsed, dict) else {"raw": result_text}}}

    return create_sse_response(_stream())


@router.post("/metrics", response_model=ApiResponse[MetricsResponse])
async def content_metrics(req: MetricsRequest, _auth: None = Depends(require_api_key)):
    """规则指标分析（同步）"""
    result = analyze_metrics(req.content, req.brand)
    return ApiResponse(data=MetricsResponse(**result))


@router.post("/quick", response_model=ApiResponse[QuickScoreResponse])
async def quick_score(req: ScoreRequest, _auth: None = Depends(require_api_key)):
    """快速规则评估"""
    result = quick_assessment(req.content, req.brand)
    return ApiResponse(data=QuickScoreResponse(**result))
