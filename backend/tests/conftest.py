"""Pytest 配置和共享 fixtures

测试环境与生产环境的差异说明：
================================

1. 建表方式差异（重要）：
   - 测试环境：使用 ``Base.metadata.create_all()`` 直接根据 ORM 模型定义创建表结构。
     这种方式**绕过了 Alembic 迁移**，仅能保证 ORM 模型与表结构一致，无法验证
     Alembic 迁移脚本本身的正确性（例如迁移脚本可能漏掉某个字段或索引，但
     ``create_all()`` 不会发现）。
   - 生产环境：必须通过 ``alembic upgrade head`` 执行迁移脚本建表，迁移脚本中的
     任何缺陷（遗漏字段、类型错误、索引缺失）都会在生产暴露。
   - 为了弥补这一差距，``test_api.py::test_alembic_migrations_exist`` 会校验
     Alembic 迁移脚本目录存在且至少包含一个迁移文件，提醒维护者保持迁移脚本与
     ORM 模型同步。

2. 认证差异：
   - 测试环境：默认通过 ``override_require_api_key`` 跳过 API Key 认证，方便
     功能测试。但认证逻辑本身需要被测试覆盖，因此提供 ``auth_client`` fixture
     （不覆盖 ``require_api_key`` 依赖），供 ``test_auth.py`` 使用。

3. 数据库差异：
   - 测试环境使用内存 SQLite（``sqlite+aiosqlite:///:memory:``），隔离性好、
     速度快，但与生产使用的数据库引擎可能存在行为差异（如外键约束、类型转换）。
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.base import Base
from app.main import app
from app.api.deps import require_api_key


# 内存 SQLite 数据库
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    """测试用数据库会话（与生产 get_db 行为一致：请求结束时自动 commit）。

    注意：必须 commit 才能将 Service 层 flush 的变更持久化到内存数据库，
    否则后续请求（使用新 session）无法看到前一个请求写入的数据。
    """
    async with TestingSessionLocal() as session:
        try:
            yield session
            if session.in_transaction():
                await session.commit()
        except Exception:
            await session.rollback()
            raise


async def override_require_api_key():
    """测试用：跳过 API Key 认证。

    注意：使用此覆盖的测试无法验证认证逻辑。需要测试认证逻辑时请使用
    ``auth_client`` fixture，它不会覆盖 ``require_api_key`` 依赖。
    """
    return None


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """每个测试前创建表，测试后删除。

    注意：此处使用 ``Base.metadata.create_all()`` 直接建表，绕过了 Alembic 迁移。
    这是为了测试速度和隔离性，但意味着迁移脚本本身的正确性无法在此处被验证。
    请参见 ``test_api.py::test_alembic_migrations_exist`` 对迁移文件存在性的最低限度校验。
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """HTTP 测试客户端（跳过 API Key 认证）。

    覆盖 ``require_api_key`` 依赖，使所有受保护端点在测试中无需提供 API Key 即可访问。
    适用于功能/集成测试，但不适合认证逻辑测试。
    """
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_api_key] = override_require_api_key
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client():
    """HTTP 测试客户端（保留真实 API Key 认证）。

    与 ``client`` 不同，此 fixture **不覆盖** ``require_api_key`` 依赖，因此受保护
    端点会执行真实的 API Key 校验逻辑。供 ``test_auth.py`` 等需要验证认证行为的
    测试使用。

    使用前应通过 ``monkeypatch`` 或直接设置 ``settings.API_KEY`` 来配置期望的 API Key。
    """
    app.dependency_overrides[get_db] = override_get_db
    # 注意： deliberately NOT overriding require_api_key here
    app.dependency_overrides.pop(require_api_key, None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def db_session():
    """数据库会话 fixture"""
    async with TestingSessionLocal() as session:
        yield session
