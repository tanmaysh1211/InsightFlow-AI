from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Create async engine for metadata storage
engine = create_async_engine(
    settings.METADATA_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def init_metadata_db():
    """Initializes metadata database, creating all tables if they don't exist."""
    async with engine.begin() as conn:
        # Import models here to ensure they register on Base
        from app.db.models import DatabaseConnection, QueryHistory, AgentExecutionLog
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Dependency to get async session for FastAPI requests."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
