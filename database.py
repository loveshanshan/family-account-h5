from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base

from config import config

# 创建数据库引擎
engine = create_engine(
    config.DATABASE_URL,
    echo=config.DEBUG
)

# 创建异步数据库引擎
async_engine = create_async_engine(
    config.DATABASE_URL,
    echo=config.DEBUG
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# 创建基础模型类
Base = declarative_base()

# 依赖注入：获取数据库会话
async def get_db():
    """获取异步数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def get_sync_db():
    """获取同步数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()