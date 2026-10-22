"""SQLAlchemy async 数据库配置"""
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

# 正确检测 SQLite：检查 URL 是否以 sqlite 开头（dialect 部分）
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {"echo": settings.DEBUG, "future": True}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)


# 启用 SQLite WAL 模式提升并发写入能力（写时不阻塞读）
if _is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001
        """在每个新数据库连接上设置 SQLite PRAGMA。

        - journal_mode=WAL：Write-Ahead Logging，允许并发读写在同一数据库上并行，
          显著提升多写/多读场景下的吞吐与响应时间。
        - synchronous=NORMAL：在 WAL 模式下提供更好的性能/安全平衡。
        """
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        finally:
            cursor.close()

AsyncSessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：获取数据库 session。
    Service 层应自行调用 await db.commit() 提交写入操作。
    请求结束时 session 自动关闭，未显式 commit 的写入不会持久化。
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            # 仅在 session 有挂起变更时才 commit
            if session.in_transaction():
                await session.commit()
        except Exception:
            await session.rollback()
            raise


# 用于非请求上下文（如初始化脚本、测试）
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return AsyncSessionFactory


async def check_db_connection() -> bool:
    """健康检查：验证数据库连接是否正常"""
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
