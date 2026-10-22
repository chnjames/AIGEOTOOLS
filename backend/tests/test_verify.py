"""验证端点测试

测试 AI 搜索验证端点的基本功能：
1. 获取验证结果列表（空列表、带数据、品牌过滤）
2. 删除验证结果
3. 验证结果解析逻辑（parse_verify_result）

注意：验证端点（/verification/verify、/verification/competitor）为 SSE 流式接口，
依赖 LLM 调用，此处不进行端到端测试，仅测试结果管理和解析逻辑。
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.verify_result import VerifyResult
from app.services.verify_service import parse_verify_result, _generate_brand_variants


async def _create_verify_result(
    db: AsyncSession,
    *,
    query: str = "项目管理软件哪个好",
    brand: str = "测试品牌",
    verify_model: str = "DeepSeek",
    is_mentioned: bool = True,
    mention_count: int = 1,
    sentiment: str = "positive",
) -> VerifyResult:
    """辅助函数：直接在 DB 中创建验证结果"""
    obj = VerifyResult(
        query=query,
        brand=brand,
        verify_model=verify_model,
        mention_count=mention_count,
        mention_position="开头前1/3",
        content_snippet=f"推荐 {brand}，因为...",
        full_response=f"推荐 {brand}，因为功能全面。",
        is_mentioned=is_mentioned,
        sentiment=sentiment,
        positive_mentions=1 if sentiment == "positive" else 0,
        negative_mentions=1 if sentiment == "negative" else 0,
        verification_mode="prompted",
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@pytest.mark.asyncio
async def test_list_results_empty(client: AsyncClient):
    """测试空验证结果列表"""
    resp = await client.get("/api/v1/verification/results")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["items"] == []
    assert data["data"]["total"] == 0


@pytest.mark.asyncio
async def test_list_results_with_data(client: AsyncClient, db_session: AsyncSession):
    """测试获取验证结果列表（带数据）"""
    await _create_verify_result(db_session, brand="品牌A", is_mentioned=True)
    await _create_verify_result(db_session, brand="品牌B", is_mentioned=False)

    resp = await client.get("/api/v1/verification/results")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 2
    items = data["data"]["items"]
    assert len(items) == 2
    # 验证结果字段
    item = items[0]
    assert "query" in item
    assert "brand" in item
    assert "verify_model" in item
    assert "is_mentioned" in item
    assert "mention_count" in item


@pytest.mark.asyncio
async def test_list_results_with_brand_filter(client: AsyncClient, db_session: AsyncSession):
    """测试按品牌过滤验证结果"""
    await _create_verify_result(db_session, brand="品牌A")
    await _create_verify_result(db_session, brand="品牌B")
    await _create_verify_result(db_session, brand="品牌A")

    resp = await client.get("/api/v1/verification/results", params={"brand": "品牌A"})
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] == 2
    for item in data["data"]["items"]:
        assert item["brand"] == "品牌A"


@pytest.mark.asyncio
async def test_list_results_pagination(client: AsyncClient, db_session: AsyncSession):
    """测试验证结果分页"""
    for i in range(5):
        await _create_verify_result(db_session, brand=f"品牌{i}")

    # 第一页，每页2条
    resp = await client.get(
        "/api/v1/verification/results", params={"page": 1, "page_size": 2}
    )
    data = resp.json()
    assert data["data"]["total"] == 5
    assert len(data["data"]["items"]) == 2
    assert data["data"]["page"] == 1
    assert data["data"]["page_size"] == 2

    # 第二页
    resp = await client.get(
        "/api/v1/verification/results", params={"page": 2, "page_size": 2}
    )
    data = resp.json()
    assert len(data["data"]["items"]) == 2


@pytest.mark.asyncio
async def test_delete_result(client: AsyncClient, db_session: AsyncSession):
    """测试删除验证结果"""
    vr = await _create_verify_result(db_session, brand="待删除品牌")
    rid = vr.id

    resp = await client.delete(f"/api/v1/verification/results/{rid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["ok"] is True

    # 验证已删除
    resp = await client.get("/api/v1/verification/results")
    assert resp.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_delete_result_not_found(client: AsyncClient):
    """测试删除不存在的验证结果返回 404"""
    resp = await client.delete("/api/v1/verification/results/99999")
    assert resp.status_code == 404


def test_parse_verify_result_mentioned():
    """测试验证结果解析：品牌被提及时"""
    response_text = """推荐测试品牌，因为它功能全面、性价比高。

---品牌分析---
- 是否提及：【是】
- 提及次数：3
- 提及位置：开头前1/3
- 正面提及次数：2
- 负面提及次数：0
- 整体情感倾向：正面
- 被推荐的品牌列表：测试品牌
"""
    result = parse_verify_result(response_text, brand="测试品牌", model="DeepSeek", query="哪个好")
    assert result["is_mentioned"] is True
    assert result["mention_count"] >= 1
    assert result["brand"] == "测试品牌"
    assert result["verify_model"] == "DeepSeek"
    assert result["query"] == "哪个好"
    assert result["sentiment"] == "positive"


def test_parse_verify_result_not_mentioned():
    """测试验证结果解析：品牌未被提及时"""
    response_text = """目前市面上有很多选择，推荐品牌A和品牌B。

---品牌分析---
- 是否提及：【否】
- 提及次数：0
- 提及位置：未提及
- 正面提及次数：0
- 负面提及次数：0
- 整体情感倾向：未提及
- 被推荐的品牌列表：品牌A、品牌B
"""
    result = parse_verify_result(response_text, brand="测试品牌", model="DeepSeek", query="哪个好")
    assert result["is_mentioned"] is False


def test_generate_brand_variants_chinese():
    """测试品牌名变体生成（中文公司后缀处理）"""
    variants = _generate_brand_variants("测试科技有限公司")
    assert "测试科技有限公司" in variants
    # 去除"科技有限公司"后缀的变体应存在
    assert "测试" in variants


def test_generate_brand_variants_english():
    """测试品牌名变体生成（英文大小写）"""
    variants = _generate_brand_variants("OpenAI")
    assert "OpenAI" in variants
    assert "openai" in variants
    assert "OPENAI" in variants
