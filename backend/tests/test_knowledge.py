"""知识库端点测试

测试知识库端点的基本功能：
1. 列表（空列表、带数据、品牌过滤）
2. 搜索（关键词搜索）
3. 删除（删除存在的、删除不存在的）

注意：上传端点涉及文件写入磁盘和向量索引，此处通过实际上传 .txt 文件进行端到端验证。
"""
import io

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_doc import KnowledgeDoc


async def _create_knowledge_doc(
    db: AsyncSession,
    *,
    filename: str = "test.txt",
    brand: str = "测试品牌",
    content: str = "这是一段知识库测试内容，用于验证搜索功能。",
) -> KnowledgeDoc:
    """辅助函数：直接在 DB 中创建知识库文档记录（不写入磁盘，仅供列表/删除测试）"""
    import hashlib
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    obj = KnowledgeDoc(
        filename=filename,
        file_path=f"/tmp/test_{content_hash[:8]}.txt",
        content=content,
        content_hash=content_hash,
        file_type="txt",
        brand=brand,
        chunk_count=1,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@pytest.mark.asyncio
async def test_list_docs_empty(client: AsyncClient):
    """测试空知识库列表"""
    resp = await client.get("/api/v1/knowledge")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["items"] == []
    assert data["data"]["total"] == 0


@pytest.mark.asyncio
async def test_list_docs_with_data(client: AsyncClient, db_session: AsyncSession):
    """测试获取知识库列表（带数据）"""
    await _create_knowledge_doc(db_session, filename="doc1.txt", brand="品牌A")
    await _create_knowledge_doc(db_session, filename="doc2.txt", brand="品牌B")

    resp = await client.get("/api/v1/knowledge")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 2
    items = data["data"]["items"]
    assert len(items) == 2
    # 验证字段
    item = items[0]
    assert "id" in item
    assert "filename" in item
    assert "file_type" in item
    assert "brand" in item
    assert "chunk_count" in item


@pytest.mark.asyncio
async def test_list_docs_with_brand_filter(client: AsyncClient, db_session: AsyncSession):
    """测试按品牌过滤知识库列表"""
    await _create_knowledge_doc(db_session, brand="品牌A")
    await _create_knowledge_doc(db_session, brand="品牌B")
    await _create_knowledge_doc(db_session, brand="品牌A")

    resp = await client.get("/api/v1/knowledge", params={"brand": "品牌A"})
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 2
    for item in data["data"]["items"]:
        assert item["brand"] == "品牌A"


@pytest.mark.asyncio
async def test_search_knowledge(client: AsyncClient, db_session: AsyncSession):
    """测试知识库搜索"""
    await _create_knowledge_doc(
        db_session,
        brand="搜索品牌",
        content="项目管理软件的选择标准包括功能、易用性和性价比。推荐使用专业工具。",
    )
    await _create_knowledge_doc(
        db_session,
        brand="搜索品牌",
        content="市场营销策略需要关注目标用户、渠道选择和内容创作。",
    )

    resp = await client.post("/api/v1/knowledge/search", json={
        "query": "项目管理软件",
        "brand": "搜索品牌",
        "top_k": 5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)
    # 关键词搜索应能匹配到包含"项目管理软件"的内容
    assert len(data["data"]) > 0
    result = data["data"][0]
    assert "doc_id" in result
    assert "filename" in result
    assert "content" in result
    assert "score" in result


@pytest.mark.asyncio
async def test_search_knowledge_no_results(client: AsyncClient, db_session: AsyncSession):
    """测试知识库搜索无结果"""
    await _create_knowledge_doc(
        db_session,
        content="这是一段关于市场营销的内容。",
    )

    resp = await client.post("/api/v1/knowledge/search", json={
        "query": "完全不匹配的查询词xyz123",
        "top_k": 5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_delete_doc(client: AsyncClient, db_session: AsyncSession):
    """测试删除知识库文档"""
    doc = await _create_knowledge_doc(db_session, filename="待删除.txt", brand="删除品牌")
    doc_id = doc.id

    resp = await client.delete(f"/api/v1/knowledge/{doc_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["ok"] is True

    # 验证已删除
    resp = await client.get("/api/v1/knowledge")
    assert resp.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_delete_doc_not_found(client: AsyncClient):
    """测试删除不存在的知识库文档返回 404"""
    resp = await client.delete("/api/v1/knowledge/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_txt_file(client: AsyncClient):
    """测试上传 .txt 文件到知识库（端到端）"""
    content = "这是一段用于测试上传的知识库内容。包含项目管理相关信息。"
    files = {
        "file": ("upload_test.txt", io.BytesIO(content.encode("utf-8")), "text/plain"),
    }
    resp = await client.post(
        "/api/v1/knowledge/upload",
        files=files,
        data={"brand": "上传测试品牌"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    doc = data["data"]
    assert doc["filename"] == "upload_test.txt"
    assert doc["brand"] == "上传测试品牌"
    assert doc["file_type"] == "txt"
    assert doc["id"] is not None

    # 验证可通过列表接口获取
    resp = await client.get("/api/v1/knowledge", params={"brand": "上传测试品牌"})
    assert resp.json()["data"]["total"] == 1


@pytest.mark.asyncio
async def test_upload_unsupported_file_type(client: AsyncClient):
    """测试上传不支持的文件类型"""
    files = {
        "file": ("test.exe", io.BytesIO(b"\x4d\x5a" + b"\x00" * 100), "application/octet-stream"),
    }
    resp = await client.post(
        "/api/v1/knowledge/upload",
        files=files,
        data={"brand": "测试品牌"},
    )
    # 不支持的文件类型应返回错误
    assert resp.status_code in (400, 422)
