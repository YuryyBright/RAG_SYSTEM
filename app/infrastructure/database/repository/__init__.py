from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# Make sure your DATABASE_URL starts with 'postgresql+asyncpg://'
assert settings.DATABASE_URL.startswith("postgresql+asyncpg://"), "DATABASE_URL must use asyncpg driver"

# Create async engine
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=settings.DB_ECHO,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)
# Base class for models
Base = declarative_base()

# Dependency for FastAPI or other async-compatible frameworks
async def get_async_db():
    """
    Async dependency to get a SQLAlchemy AsyncSession.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
