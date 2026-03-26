from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from app.models.base import Base
from app.models import (
    Customer,
    Package,
    Policy,
    Doctor,
    DoctorNetwork,
    Appointment,
)
import os
from dotenv import load_dotenv
load_dotenv()

# =============================================
# Database URL from env
# =============================================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+aiomysql://insurance:insurancepass@mysql:3306/insurance"
)

# =============================================
# Engine
# =============================================
engine: AsyncEngine = create_async_engine(
    url=DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# =============================================
# Session Factory
# =============================================
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# =============================================
# Dependency → used in routers
# =============================================
async def get_session() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# =============================================
# Create all tables on startup
# =============================================
async def create_all_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ All tables created.")

# =============================================
# Dispose engine on shutdown
# =============================================
async def close_db():
    await engine.dispose()
    print(" DB connection closed.")