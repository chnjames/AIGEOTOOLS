"""工作流 API"""
from fastapi import APIRouter, Depends, Query, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_workflow_service, get_config_service, require_api_key
from app.api.sse import create_sse_response
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.workflow import (
    WorkflowResponse, WorkflowCreateRequest, WorkflowUpdateRequest,
    WorkflowExecutionResponse, WorkflowTemplateResponse, WorkflowExecuteRequest,
)
from app.services.workflow_service import WorkflowService
from app.services.config_service import ConfigService
from app.services.audit_service import log_audit, get_operator_from_request

router = APIRouter(prefix="/workflows", tags=["工作流自动化"])


@router.get("", response_model=ApiResponse[list[WorkflowResponse]])
async def list_workflows(
    brand: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: WorkflowService = Depends(get_workflow_service),
    _auth: None = Depends(require_api_key),
):
    all_wfs = await svc.get_workflows(brand)
    start = (page - 1) * page_size
    end = start + page_size
    wfs = all_wfs[start:end]
    return ApiResponse(data=[WorkflowResponse.model_validate(w) for w in wfs])


@router.post("", response_model=ApiResponse[WorkflowResponse])
async def create_workflow(
    req: WorkflowCreateRequest,
    svc: WorkflowService = Depends(get_workflow_service),
    _auth: None = Depends(require_api_key),
):
    wf = await svc.create_workflow(
        name=req.name, steps=[s.model_dump() for s in req.steps],
        brand=req.brand, schedule=req.schedule, conditions=req.conditions,
    )
    return ApiResponse(data=WorkflowResponse.model_validate(wf))


@router.get("/templates/list", response_model=ApiResponse[list])
async def list_templates(
    svc: WorkflowService = Depends(get_workflow_service),
    _auth: None = Depends(require_api_key),
):
    templates = await svc.get_templates()
    return ApiResponse(data=templates)


@router.put("/{wf_id}", response_model=ApiResponse[WorkflowResponse])
async def update_workflow(
    wf_id: str = Path(..., max_length=64),
    req: WorkflowUpdateRequest = ...,
    svc: WorkflowService = Depends(get_workflow_service),
    _auth: None = Depends(require_api_key),
):
    data = req.model_dump(exclude_unset=True)
    if "steps" in data and data["steps"] is not None:
        data["steps"] = [s.model_dump() if hasattr(s, 'model_dump') else s for s in data["steps"]]
    wf = await svc.update_workflow(wf_id, **data)
    if wf is None:
        raise NotFoundError("工作流不存在")
    return ApiResponse(data=WorkflowResponse.model_validate(wf))


@router.delete("/{wf_id}", response_model=ApiResponse[dict])
async def delete_workflow(
    wf_id: str = Path(..., max_length=64),
    svc: WorkflowService = Depends(get_workflow_service),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _auth: None = Depends(require_api_key),
):
    ok = await svc.delete_workflow(wf_id)
    if not ok:
        raise NotFoundError("工作流不存在")
    await log_audit(
        db=db, action="workflow_delete", resource_type="workflow", resource_id=wf_id,
        operator=get_operator_from_request(request),
    )
    return ApiResponse(data={"ok": ok})


@router.post("/{wf_id}/toggle", response_model=ApiResponse[WorkflowResponse])
async def toggle_workflow(
    wf_id: str = Path(..., max_length=64),
    data: dict = ...,
    svc: WorkflowService = Depends(get_workflow_service),
    _auth: None = Depends(require_api_key),
):
    wf = await svc.update_workflow(wf_id, enabled=data.get("enabled", True))
    if wf is None:
        raise NotFoundError("工作流不存在")
    return ApiResponse(data=WorkflowResponse.model_validate(wf))


@router.post("/{wf_id}/execute")
async def execute_workflow(
    wf_id: str = Path(..., max_length=64),
    req: WorkflowExecuteRequest = ...,
    svc: WorkflowService = Depends(get_workflow_service),
    config_svc: ConfigService = Depends(get_config_service),
    _auth: None = Depends(require_api_key),
):
    """执行工作流（SSE 进度流）"""
    cfg = await config_svc.get_config()
    brand = req.brand or cfg.get("brand", "")
    advantages = req.advantages or cfg.get("advantages", "")
    provider = req.provider or cfg.get("gen_provider", "DeepSeek")
    api_key = req.api_key or cfg.get("gen_api_key", "")

    async def _stream():
        async for event in svc.execute_stream(
            wf_id=wf_id, brand=brand, advantages=advantages,
            keywords=req.keywords, platforms=req.platforms,
            temperature=req.temperature, provider=provider, api_key=api_key,
        ):
            yield event

    return create_sse_response(_stream())


@router.get("/{wf_id}/executions", response_model=ApiResponse[PageResponse[WorkflowExecutionResponse]])
async def list_executions(
    wf_id: str = Path(..., max_length=64),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: WorkflowService = Depends(get_workflow_service),
    _auth: None = Depends(require_api_key),
):
    result = await svc.get_executions(wf_id, page, page_size)
    return ApiResponse(data=PageResponse(**result))
