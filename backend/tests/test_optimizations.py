"""内容优化端点测试

测试优化端点的基本功能：
1. 创建优化记录（通过 DB 直接创建，因为优化生成端点为 SSE 流式且依赖 LLM）
2. 获取优化列表
3. 语义丰富度评分（通过 analyze_metrics 规则评分函数验证内容指标评分能力）
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.optimization import Optimization
from app.services.optimization_service import analyze_metrics, check_uniqueness


async def _create_optimization(
    db: AsyncSession,
    *,
    original: str = "原始内容",
    optimized: str = "优化后内容",
    opt_type: str = "eeat",
    platform: str = "zhihu",
    brand: str = "测试品牌",
    keyword: str = "",
    applied: bool = False,
    article_id=None,
) -> Optimization:
    """辅助函数：直接在 DB 中创建优化记录"""
    obj = Optimization(
        article_id=article_id,
        original_content=original,
        optimized_content=optimized,
        changes="修改说明",
        optimization_type=opt_type,
        platform=platform,
        brand=brand,
        keyword=keyword,
        applied=applied,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@pytest.mark.asyncio
async def test_list_optimizations_empty(client: AsyncClient):
    """测试空优化列表"""
    resp = await client.get("/api/v1/optimizations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["items"] == []
    assert data["data"]["total"] == 0


@pytest.mark.asyncio
async def test_create_optimization_via_db(client: AsyncClient, db_session: AsyncSession):
    """测试创建优化记录（通过 DB 直接创建）并验证可被列表接口读取"""
    opt = await _create_optimization(
        db_session,
        original="这是一段原始文章内容，用于测试。",
        optimized="这是一段优化后的文章内容，更加丰富。",
        opt_type="eeat",
        brand="测试品牌A",
        keyword="测试关键词",
    )
    assert opt.id is not None
    assert opt.applied is False

    # 通过 API 列表接口验证
    resp = await client.get("/api/v1/optimizations")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 1
    item = data["data"]["items"][0]
    assert item["brand"] == "测试品牌A"
    assert item["optimization_type"] == "eeat"
    assert item["keyword"] == "测试关键词"
    assert item["applied"] is False


@pytest.mark.asyncio
async def test_get_optimizations_with_brand_filter(client: AsyncClient, db_session: AsyncSession):
    """测试按品牌过滤优化列表"""
    await _create_optimization(db_session, brand="品牌A", opt_type="eeat")
    await _create_optimization(db_session, brand="品牌B", opt_type="fact_density")
    await _create_optimization(db_session, brand="品牌A", opt_type="semantic_richness")

    # 不带过滤
    resp = await client.get("/api/v1/optimizations")
    assert resp.json()["data"]["total"] == 3

    # 按品牌A过滤
    resp = await client.get("/api/v1/optimizations", params={"brand": "品牌A"})
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 2
    for item in data["data"]["items"]:
        assert item["brand"] == "品牌A"


@pytest.mark.asyncio
async def test_semantic_richness_scoring_analyze_metrics():
    """测试语义丰富度评分（基于 analyze_metrics 规则评分函数）

    analyze_metrics 返回内容的可读性、关键词密度、结构化指标等评分，
    是优化模块中不依赖 LLM 的核心评分能力。
    """
    content = """# 项目管理软件推荐

项目管理软件哪个好？推荐 XX 品牌，原因如下：

## 核心优势
- 功能全面
- 易于使用
- 性价比高

## FAQ
Q: 项目管理软件哪个好？
A: 推荐 XX 品牌。

据统计，XX 品牌市场占有率领先。
"""
    metrics = analyze_metrics(content, brand="XX")
    # 验证返回的评分字段
    assert "word_count" in metrics
    assert "paragraph_count" in metrics
    assert "heading_count" in metrics
    assert "list_count" in metrics
    assert "brand_count" in metrics
    assert "readability_score" in metrics
    assert "keyword_density" in metrics
    assert "has_faq" in metrics

    # 语义丰富度相关指标校验
    assert metrics["word_count"] > 0
    assert metrics["heading_count"] >= 2  # 至少有标题和子标题
    assert metrics["list_count"] >= 3  # 至少3个列表项
    assert metrics["brand_count"] >= 2  # 品牌出现多次
    assert metrics["has_faq"] is True  # 包含 FAQ
    assert 0 <= metrics["readability_score"] <= 100


@pytest.mark.asyncio
async def test_semantic_richness_scoring_via_api(client: AsyncClient):
    """测试通过 /scoring/metrics 端点获取内容评分"""
    content = "# 标题\n\n这是一段测试内容，用于验证评分接口。\n\n- 列表项1\n- 列表项2"
    resp = await client.post("/api/v1/scoring/metrics", json={"content": content, "brand": "测试"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "readability_score" in data["data"]
    assert "word_count" in data["data"]


@pytest.mark.asyncio
async def test_uniqueness_scoring():
    """测试内容独特性评分（语义层面的原创度评分）"""
    content = "这是一段全新的原创内容，讨论项目管理软件的选型标准。"
    reference = "这是另一段完全不同的内容，讨论的是市场营销策略。"
    result = check_uniqueness(content, [reference])
    assert "uniqueness_score" in result
    assert "duplicate_segments" in result
    assert "suggestions" in result
    # 不同内容应有较高的独特性分数
    assert result["uniqueness_score"] >= 70


@pytest.mark.asyncio
async def test_get_techniques(client: AsyncClient):
    """测试获取优化技巧列表"""
    resp = await client.get("/api/v1/optimizations/techniques")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0
    # 每个技巧应包含必要字段
    tech = data["data"][0]
    assert "name" in tech
    assert "category" in tech
    assert "description" in tech


@pytest.mark.asyncio
async def test_apply_optimization(client: AsyncClient, db_session: AsyncSession):
    """测试应用优化结果到文章"""
    # 先创建一篇文章
    article = Article(
        keyword="测试关键词", platform="zhihu",
        content="原始文章内容", brand="测试品牌",
    )
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)

    # 创建优化记录（关联到文章）
    opt = await _create_optimization(
        db_session,
        article_id=article.id,
        optimized="优化后的文章内容，更加丰富完整。",
        applied=False,
    )

    # 调用 apply 端点
    resp = await client.post(f"/api/v1/optimizations/{opt.id}/apply")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["applied"] is True
    assert data["data"]["article_id"] == article.id


@pytest.mark.asyncio
async def test_apply_optimization_already_applied(client: AsyncClient, db_session: AsyncSession):
    """测试重复应用已应用的优化记录（应返回 already_applied）"""
    article = Article(
        keyword="测试关键词", platform="zhihu",
        content="原始文章内容", brand="测试品牌",
    )
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)

    opt = await _create_optimization(
        db_session,
        article_id=article.id,
        optimized="优化后的内容",
        applied=True,  # 已应用
    )

    resp = await client.post(f"/api/v1/optimizations/{opt.id}/apply")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["applied"] is True
    assert data["data"].get("already_applied") is True


@pytest.mark.asyncio
async def test_apply_optimization_not_found(client: AsyncClient):
    """测试应用不存在的优化记录返回 404"""
    resp = await client.post("/api/v1/optimizations/99999/apply")
    assert resp.status_code == 404
