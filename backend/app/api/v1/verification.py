"""AI 搜索验证 API"""
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_verify_service, get_config_service, require_api_key
from app.api.sse import create_sse_response
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.verify import (
    VerifyResultResponse, VerifyRequest, CompetitorVerifyRequest,
)
from app.services.verify_service import VerifyService
from app.services.config_service import ConfigService
from app.utils.prompt_guard import detect_injection

logger = get_logger(__name__)
router = APIRouter(prefix="/verification", tags=["多模型验证"])


def _collect_injection_warnings(query: str, brand: str = "", competitors: list[str] | None = None) -> list[str]:
    """对进入 LLM 提示词的用户文本字段运行 Prompt 注入检测，收集所有警告（非阻塞）。"""
    warnings: list[str] = []
    if query:
        warnings.extend(f"[查询词] {w}" for w in detect_injection(query))
    if brand:
        warnings.extend(f"[品牌] {w}" for w in detect_injection(brand))
    for c in competitors or []:
        if c:
            warnings.extend(f"[竞品] {w}" for w in detect_injection(c))
    if warnings:
        logger.warning("Verification prompt-injection warnings: %s", warnings)
    return warnings


async def _resolve_provider_configs(providers: list[str], verify_keys: dict | None, config_svc: ConfigService) -> dict[str, str]:
    cfg = await config_svc.get_config()
    result: dict[str, str] = {}
    all_providers = providers or cfg.get("verify_providers", [])
    saved_keys = cfg.get("verify_keys", {})
    for p in all_providers:
        key = ""
        if verify_keys and p in verify_keys:
            key = verify_keys[p]
        elif p in saved_keys:
            key = saved_keys[p]
        elif p == cfg.get("gen_provider"):
            key = cfg.get("gen_api_key", "")
        if key:
            result[p] = key
    return result


@router.get("/results", response_model=ApiResponse[PageResponse[VerifyResultResponse]])
async def list_results(
    brand: str = "", page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    svc: VerifyService = Depends(get_verify_service),
    _auth: None = Depends(require_api_key),
):
    result = await svc.get_results(brand=brand, page=page, page_size=page_size)
    return ApiResponse(data=PageResponse(**result))


@router.delete("/results/{rid}", response_model=ApiResponse[dict])
async def delete_result(
    rid: int, svc: VerifyService = Depends(get_verify_service),
    _auth: None = Depends(require_api_key),
):
    ok = await svc.delete_result(rid)
    if not ok:
        raise NotFoundError("验证结果不存在")
    return ApiResponse(data={"ok": ok})


@router.post("/verify")
async def verify_brand(
    req: VerifyRequest,
    svc: VerifyService = Depends(get_verify_service),
    config_svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    """多模型品牌验证（SSE 流式）"""
    gcfg = await config_svc.get_config()
    brand = req.brand or gcfg.get("brand", "")
    prov_cfgs = await _resolve_provider_configs(req.providers, req.verify_keys, config_svc)
    if not prov_cfgs:
        raise ValidationError("请至少选择一个验证模型")

    # Prompt 注入检测（非阻塞，仅警告）
    warnings = _collect_injection_warnings(query=req.query, brand=brand)

    async def _stream():
        if warnings:
            yield {"event": "injection_warnings", "data": {"warnings": warnings}}
        async for event in svc.verify_brand_stream(
            query=req.query, brand=brand,
            provider_configs=prov_cfgs, temperature=req.temperature,
            mode=req.mode,
        ):
            yield event

    return create_sse_response(_stream())


@router.post("/competitor")
async def verify_competitor(
    req: CompetitorVerifyRequest,
    svc: VerifyService = Depends(get_verify_service),
    config_svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    """竞品对比验证（SSE 流式）"""
    gcfg = await config_svc.get_config()
    brand = req.brand or gcfg.get("brand", "")
    competitors = req.competitors or [
        c.strip() for c in gcfg.get("competitors", "").split("\n") if c.strip()
    ]
    prov_cfgs = await _resolve_provider_configs(req.providers, req.verify_keys, config_svc)
    if not prov_cfgs:
        raise ValidationError("请至少选择一个验证模型")

    # Prompt 注入检测（非阻塞，仅警告）
    warnings = _collect_injection_warnings(query=req.query, brand=brand, competitors=competitors)

    async def _stream():
        if warnings:
            yield {"event": "injection_warnings", "data": {"warnings": warnings}}
        async for event in svc.verify_competitor_stream(
            query=req.query, brand=brand, competitors=competitors,
            provider_configs=prov_cfgs, temperature=req.temperature,
        ):
            yield event

    return create_sse_response(_stream())
