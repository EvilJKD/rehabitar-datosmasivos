"""
Gestión de la conexión asíncrona a PostgreSQL/PostGIS con SQLAlchemy 2.0 y asyncpg.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Clase base declarativa para los modelos ORM de SQLAlchemy."""
    pass


# TODO 1: Crear el motor asíncrono `engine = create_async_engine(settings.DATABASE_URL_ASYNC, ...)`
engine = None

# TODO 2: Crear la factoría de sesiones `AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, ...)`
AsyncSessionLocal = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    TODO 3: Dependencia de FastAPI (`Depends(get_db)`) que abre una sesión asíncrona
    contra PostgreSQL/PostGIS y la cede (`yield session`) a cada endpoint.
    """
    pass
