"""API 集成测试"""
import os
from pathlib import Path

import pytest
from httpx import AsyncClient


def test_alembic_migrations_exist():
    """校验 Alembic 迁移文件存在性。

    背景：conftest.py 中的 ``setup_db`` fixture 使用 ``Base.metadata.create_all()``
    直接建表，绕过了 Alembic 迁移脚本。这意味着迁移脚本本身可能存在缺陷
    （遗漏字段、索引、类型错误）却无法被现有测试发现。

    此测试作为最低限度的护栏：确认 ``alembic/versions/`` 目录存在且至少包含一个
    形如 ``NNN_*.py`` 的迁移脚本文件，提醒维护者保持迁移脚本与 ORM 模型同步。

    注意：此测试仅校验文件存在性，无法替代迁移脚本与 ORM 模型的一致性校验
    （理想情况下应通过 ``alembic upgrade head`` + ``alembic downgrade base``
    在临时数据库中完整跑一遍迁移来验证）。
    """
    # backend/ 为本测试文件的上级目录
    backend_dir = Path(__file__).resolve().parent.parent
    versions_dir = backend_dir / "alembic" / "versions"
    assert versions_dir.is_dir(), f"Alembic 迁移目录不存在: {versions_dir}"

    migration_files = [
        f for f in os.listdir(versions_dir)
        if f.endswith(".py") and not f.startswith("__")
    ]
    assert len(migration_files) > 0, (
        f"Alembic 迁移目录 {versions_dir} 中未找到任何迁移脚本文件（.py），"
        "请确保 ORM 模型变更同步体现在 Alembic 迁移脚本中"
    )


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    """测试健康检查端点"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_get_config(client: AsyncClient):
    """测试获取配置"""
    resp = await client.get("/api/v1/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0


@pytest.mark.asyncio
async def test_list_keywords_empty(client: AsyncClient):
    """测试空关键词列表"""
    resp = await client.get("/api/v1/keywords")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["items"] == []
    assert data["data"]["total"] == 0


@pytest.mark.asyncio
async def test_create_keywords(client: AsyncClient):
    """测试创建关键词"""
    kws = ["测试关键词1", "测试关键词2", "项目管理软件哪个好"]
    resp = await client.post("/api/v1/keywords", json={
        "keywords": kws,
        "brand": "测试品牌",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert len(data["data"]) == 3


@pytest.mark.asyncio
async def test_list_keywords_after_create(client: AsyncClient):
    """创建后关键词列表不为空"""
    kws = ["SEO优化"]
    await client.post("/api/v1/keywords", json={"keywords": kws, "brand": "测试"})
    resp = await client.get("/api/v1/keywords")
    data = resp.json()
    assert data["data"]["total"] == 1
    assert data["data"]["items"][0]["keyword"] == "SEO优化"


@pytest.mark.asyncio
async def test_combinations(client: AsyncClient):
    """测试词库组合生成（不依赖 LLM）"""
    resp = await client.post("/api/v1/keywords/combinations", params={
        "core_keyword": "项目管理",
        "max_results": 10,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0


@pytest.mark.asyncio
async def test_list_articles_empty(client: AsyncClient):
    """测试空文章列表"""
    resp = await client.get("/api/v1/articles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["items"] == []


@pytest.mark.asyncio
async def test_platforms_meta(client: AsyncClient):
    """测试平台元数据"""
    resp = await client.get("/api/v1/articles/meta/platforms")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0


@pytest.mark.asyncio
async def test_techniques(client: AsyncClient):
    """测试技术列表"""
    resp = await client.get("/api/v1/optimizations/techniques")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_resources(client: AsyncClient):
    """测试资源列表"""
    resp = await client.get("/api/v1/resources")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_resource_categories(client: AsyncClient):
    """测试资源分类"""
    resp = await client.get("/api/v1/resources/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_kpi(client: AsyncClient):
    """测试 KPI 端点"""
    resp = await client.get("/api/v1/reports/kpi")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "total_keywords" in data["data"]


@pytest.mark.asyncio
async def test_costs(client: AsyncClient):
    """测试费用报表"""
    resp = await client.get("/api/v1/reports/costs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "total_cost_cny" in data["data"]


@pytest.mark.asyncio
async def test_mentions(client: AsyncClient):
    """测试提及报表"""
    resp = await client.get("/api/v1/reports/mentions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0


@pytest.mark.asyncio
async def test_platforms_supported(client: AsyncClient):
    """测试支持的平台列表"""
    resp = await client.get("/api/v1/platforms/supported")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_delete_keyword(client: AsyncClient):
    """测试删除关键词"""
    # 先创建
    await client.post("/api/v1/keywords", json={"keywords": ["待删除"], "brand": "test"})
    resp = await client.get("/api/v1/keywords")
    kw_id = resp.json()["data"]["items"][0]["id"]
    # 删除
    del_resp = await client.delete(f"/api/v1/keywords/{kw_id}")
    assert del_resp.status_code == 200
    # 验证删除
    resp2 = await client.get("/api/v1/keywords")
    assert resp2.json()["data"]["total"] == 0
