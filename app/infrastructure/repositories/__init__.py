from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

from app.utils.logger_util import get_logger
from app.config import settings

# Configure logger
logger = get_logger(__name__)

# Create the async engine using the database URL from your settings
engine = create_async_engine(
    settings.DATABASE_URL,
    # optionally set echo=True for SQL debugging
)

# Create a sessionmaker that returns AsyncSession instances
AsyncSessionLocal = sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async SQLAlchemy session.

    Usage:
        @router.get("/example")
        async def example_endpoint(db: AsyncSession = Depends(get_async_db)):
            # use 'db' here for queries
            ...

    Workflow:
        1. Acquire an async session from `AsyncSessionLocal`.
        2. Yield the session to the caller (endpoint/other code).
        3. When the caller finishes (on success or exception),
           commit if no exception occurred, else rollback.
        4. Close the session to free up resources.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Hand control back to the caller (endpoint) with 'yield'
            yield session
        except Exception as exc:
            # On error, roll back any pending changes
            await session.rollback()
            logger.error("Database transaction rolled back due to exception: %s", exc)
            raise
        else:
            # If no errors occurred, commit pending changes
            await session.commit()
        finally:
            # Ensure session is closed, releasing connection back to pool
            await session.close()

async def get_websocket_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for WebSocket endpoints."""
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()