"""认证逻辑测试

测试 API Key 认证逻辑：
1. 无 API Key 时请求受保护端点返回 401
2. 错误 API Key 时返回 401
3. 正确 API Key 时请求成功

注意：此测试使用 conftest.py 中的 ``auth_client`` fixture，该 fixture **不覆盖**
``require_api_key`` 依赖，因此会执行真实的 API Key 校验逻辑。
"""
import pytest
from httpx import AsyncClient

from app.api.deps import settings as deps_settings


# 测试用的 API Key
TEST_API_KEY = "test-secret-api-key-for-auth-testing"


@pytest.fixture
def configured_api_key():
    """配置测试用 API Key，测试后恢复原值。

    ``app.api.deps.settings`` 与 ``get_settings()`` 返回的是同一个单例对象
    （lru_cache），直接修改其 ``API_KEY`` 属性即可影响 ``require_api_key`` 依赖
    的校验逻辑。
    """
    original_key = deps_settings.API_KEY
    deps_settings.API_KEY = TEST_API_KEY
    yield deps_settings.API_KEY
    deps_settings.API_KEY = original_key


@pytest.mark.asyncio
async def test_no_api_key_returns_401(auth_client: AsyncClient, configured_api_key):
    """测试无 API Key 时请求受保护端点返回 401"""
    # 不携带 X-API-Key 头
    resp = await auth_client.get("/api/v1/keywords")
    assert resp.status_code == 401
    data = resp.json()
    assert data["code"] == "AUTH_ERROR"


@pytest.mark.asyncio
async def test_wrong_api_key_returns_401(auth_client: AsyncClient, configured_api_key):
    """测试错误 API Key 时返回 401"""
    resp = await auth_client.get(
        "/api/v1/keywords",
        headers={"X-API-Key": "wrong-key-12345"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert data["code"] == "AUTH_ERROR"


@pytest.mark.asyncio
async def test_correct_api_key_succeeds(auth_client: AsyncClient, configured_api_key):
    """测试正确 API Key 时请求成功"""
    resp = await auth_client.get(
        "/api/v1/keywords",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0


@pytest.mark.asyncio
async def test_correct_api_key_config_endpoint(auth_client: AsyncClient, configured_api_key):
    """测试正确 API Key 时请求配置端点成功（验证多个受保护端点）"""
    resp = await auth_client.get(
        "/api/v1/config",
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0


@pytest.mark.asyncio
async def test_empty_api_key_returns_401(auth_client: AsyncClient, configured_api_key):
    """测试空 API Key 时返回 401"""
    resp = await auth_client.get(
        "/api/v1/keywords",
        headers={"X-API-Key": ""},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_endpoint_no_auth_required(auth_client: AsyncClient, configured_api_key):
    """测试健康检查端点不需要认证（即使配置了 API Key 也能访问）"""
    resp = await auth_client.get("/health")
    assert resp.status_code == 200
