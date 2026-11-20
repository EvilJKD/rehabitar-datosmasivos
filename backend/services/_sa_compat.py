"""Compatibilidad ligera de SQLAlchemy para pruebas unitarias en entornos sin driver/ORM."""

from typing import Any

try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:  # pragma: no cover - permite ejecutar pruebas unitarias en host sin sqlalchemy

    def text(sql: str) -> str:  # type: ignore
        return sql

    AsyncSession = Any  # type: ignore
