"""知识库 API"""
import os

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_knowledge_service, require_api_key, get_db
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.knowledge import (
    KnowledgeDocResponse, KnowledgeSearchRequest, KnowledgeChunkResponse,
)
from app.services.knowledge_service import KnowledgeService
from app.services.audit_service import log_audit, get_operator_from_request
from app.core.exceptions import FileError, NotFoundError

router = APIRouter(prefix="/knowledge", tags=["品牌知识库"])

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB

# 扩展名 -> 允许的 MIME 类型白名单（包含常见合法值与浏览器可能发送的通用类型）
_ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    ".txt": {"text/plain", "application/octet-stream", ""},
    ".md": {"text/markdown", "text/x-markdown", "text/plain", "application/octet-stream", ""},
    ".pdf": {"application/pdf", "application/octet-stream", ""},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
        "application/zip",
        "",
    },
}

# 扩展名 -> 文件头魔数（bytes 前缀）；文本类文件无固定魔数，单独处理
_FILE_MAGIC: dict[str, bytes] = {
    ".pdf": b"%PDF-",
    ".docx": b"PK\x03\x04",  # ZIP archive header（docx 基于 ZIP）
}


def _normalize_mime(content_type: str | None) -> str:
    """归一化 MIME 类型：取分号前部分并小写。"""
    if not content_type:
        return ""
    return content_type.split(";")[0].strip().lower()


def _validate_file_content(ext: str, content_type: str | None, data: bytes) -> None:
    """校验上传文件的内容类型与文件头魔数，防止扩展名伪造。

    - MIME 类型校验：若浏览器提供了 content_type，则必须命中扩展名对应的白名单。
    - 魔数校验：对有固定文件头的类型（pdf/docx）校验首字节；对文本类（txt/md）
      检测首 1KB 是否含二进制空字节，命中则视为伪造。
    """
    # 1. MIME 类型校验
    allowed_mimes = _ALLOWED_MIME_TYPES.get(ext)
    ct = _normalize_mime(content_type)
    if allowed_mimes is not None and ct and ct not in allowed_mimes:
        raise FileError(
            f"文件 MIME 类型不匹配：{content_type}，扩展名 {ext} 不允许该类型"
        )

    # 2. 文件头魔数校验
    expected_magic = _FILE_MAGIC.get(ext)
    if expected_magic is not None:
        if len(data) < len(expected_magic) or not data.startswith(expected_magic):
            raise FileError(
                f"文件内容与扩展名 {ext} 不匹配（文件头魔数校验失败），疑似伪造文件"
            )
    else:
        # 文本类文件（txt/md）：检测首 1KB 是否含二进制空字节
        if b"\x00" in data[:1024]:
            raise FileError(
                f"文件内容与扩展名 {ext} 不匹配（检测到二进制内容），疑似伪造文件"
            )


@router.get("", response_model=ApiResponse[PageResponse[KnowledgeDocResponse]])
async def list_docs(
    brand: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: KnowledgeService = Depends(get_knowledge_service),
    _auth: None = Depends(require_api_key),
):
    result = await svc.get_documents(brand=brand, page=page, page_size=page_size)
    return ApiResponse(data=PageResponse(**result))


@router.post("/upload", response_model=ApiResponse[KnowledgeDocResponse])
async def upload_doc(
    file: UploadFile = File(...),
    brand: str = Form(""),
    svc: KnowledgeService = Depends(get_knowledge_service),
    _auth: None = Depends(require_api_key),
):
    if not file.filename:
        raise FileError("文件名不能为空")

    # Early extension check before reading content
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FileError(f"不支持的文件类型：{ext}，支持：{ALLOWED_EXTENSIONS}")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise FileError(f"文件过大，最大支持 {MAX_UPLOAD_BYTES // 1024 // 1024}MB")

    # 内容校验：MIME 类型白名单 + 文件头魔数校验，防止扩展名伪造
    _validate_file_content(ext, file.content_type, content)

    doc = await svc.upload_document(file.filename, content, brand)
    return ApiResponse(data=KnowledgeDocResponse.model_validate(doc))


@router.post("/search", response_model=ApiResponse[list[KnowledgeChunkResponse]])
async def search_knowledge(
    req: KnowledgeSearchRequest,
    svc: KnowledgeService = Depends(get_knowledge_service),
    _auth: None = Depends(require_api_key),
):
    results = await svc.search(req.query, req.brand, req.top_k)
    return ApiResponse(data=[KnowledgeChunkResponse(**r) for r in results])


@router.delete("/{doc_id}", response_model=ApiResponse[dict])
async def delete_doc(
    doc_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    svc: KnowledgeService = Depends(get_knowledge_service),
    _auth: None = Depends(require_api_key),
):
    ok = await svc.delete_document(doc_id)
    if not ok:
        raise NotFoundError(f"文档（ID: {doc_id}）不存在")
    # 审计日志：记录知识库文档删除
    await log_audit(
        db=db,
        action="knowledge_delete",
        resource_type="knowledge_doc",
        resource_id=str(doc_id),
        operator=get_operator_from_request(request),
        details={"doc_id": doc_id},
    )
    return ApiResponse(data={"ok": True})
