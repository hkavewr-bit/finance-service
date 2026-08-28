from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession

from jinrong.config.settings import settings

session_engine : AsyncEngine | None = None

session_factory : async_sessionmaker[AsyncSession] | None = None


def init_db_engine():
    """
    初始化数据库引擎和会话工厂
    """
    global session_engine, session_factory


    # 创建异步数据库引擎
    session_engine = create_async_engine(url=settings.database_url, echo=False)

    # 创建异步会话工厂
    session_factory = async_sessionmaker(session_engine, expire_on_commit=False)


async def dispose_engine():
    await session_engine.dispose()


async def main_test():
    init_db_engine()
    async with session_factory() as conn:
        result = await conn.execute(text("SELECT 1"))
        print(result.mappings().fetchone())



    await dispose_engine()



if __name__ == '__main__':
    import asyncio
    asyncio.run(main_test())