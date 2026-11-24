"""
Gestión de la conexión asíncrona a PostgreSQL/PostGIS con SQLAlchemy 2.0 y asyncpg.
"""

from typing import Any, AsyncGenerator

from core.config import settings

try:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        """Clase base declarativa para los modelos ORM de SQLAlchemy."""

        pass

    try:
        engine = create_async_engine(settings.DATABASE_URL_ASYNC, pool_pre_ping=True)
        AsyncSessionLocal = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
    except (ImportError, ModuleNotFoundError):  # pragma: no cover - host sin driver asyncpg
        engine = None
        AsyncSessionLocal = None
except ImportError:  # pragma: no cover - permite ejecutar pruebas unitarias en host sin sqlalchemy
    AsyncSession = Any  # type: ignore

    class Base:  # type: ignore
        """Clase base sustitutiva cuando SQLAlchemy no está instalado."""

        pass

    engine = None
    AsyncSessionLocal = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia de FastAPI (`Depends(get_db)`) que abre una sesión asíncrona
    contra PostgreSQL/PostGIS y la cede (`yield session`) a cada endpoint.
    """
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "La factoría de sesiones asíncronas no está disponible (requiere sqlalchemy y asyncpg)."
        )
    async with AsyncSessionLocal() as session:
        yield session
