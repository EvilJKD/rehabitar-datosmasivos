"""Consultas municipales y carga de infraestructura bajo demanda."""

import asyncio
import sys
from pathlib import Path

from ._sa_compat import AsyncSession, text

try:
    # En Docker, el directorio del ETL está en PYTHONPATH.
    from p1_ngbe.etl_ngbe import ingest_infraestructura_municipio
except ModuleNotFoundError as exc:
    if exc.name != "p1_ngbe":
        raise
    etl_dir = Path(__file__).resolve().parents[2] / "etl"
    if str(etl_dir) not in sys.path:
        sys.path.insert(0, str(etl_dir))
    from p1_ngbe.etl_ngbe import ingest_infraestructura_municipio


MUNICIPIOS_QUERY = """
    SELECT m.codigo_ine, m.nombre, m.provincia, m.comarca, m.latitud, m.longitud,
           m.hidratado, m.fecha_hidratacion,
           i.distancia_carretera_km::double precision,
           i.distancia_recurso_hidrico_km::double precision,
           i.cobertura_fibra_pct::double precision, i.cobertura_movil_pct::double precision,
           i.fecha_actualizacion
    FROM municipios AS m
    LEFT JOIN metricas_infraestructura AS i USING (codigo_ine)
"""
LIST_MUNICIPIOS = text(MUNICIPIOS_QUERY + " ORDER BY m.nombre, m.codigo_ine")
GET_MUNICIPIO = text(MUNICIPIOS_QUERY + " WHERE m.codigo_ine = :codigo_ine")
METRICAS_FIELDS = (
    "codigo_ine",
    "distancia_carretera_km",
    "distancia_recurso_hidrico_km",
    "cobertura_fibra_pct",
    "cobertura_movil_pct",
    "fecha_actualizacion",
)


async def get_all_municipios_base(db: AsyncSession) -> list[dict]:
    """Devuelve todos los municipios del catálogo ordenados por nombre junto con sus métricas si ya están cargadas."""
    result = await db.execute(LIST_MUNICIPIOS)
    return [dict(row) for row in result.mappings()]


async def get_municipio_by_ine(db: AsyncSession, codigo_ine: str) -> dict | None:
    """Busca un municipio por su código INE y devuelve sus datos junto con las métricas disponibles, o None si no existe."""
    result = await db.execute(GET_MUNICIPIO, {"codigo_ine": codigo_ine})
    row = result.mappings().one_or_none()
    return dict(row) if row is not None else None


async def hydrate_infraestructura_on_demand(db: AsyncSession, codigo_ine: str) -> dict:
    """Reutiliza las métricas persistidas del municipio o ejecuta el ETL síncrono fuera del event loop.

    El orquestador actualiza el estado global del municipio después de todos los módulos.
    """
    municipio = await get_municipio_by_ine(db, codigo_ine)
    if municipio is None:
        raise LookupError(f"No existe el municipio {codigo_ine} en el catálogo del IGN.")
    if municipio["fecha_actualizacion"] is not None:
        return {field: municipio[field] for field in METRICAS_FIELDS}
    return await asyncio.to_thread(ingest_infraestructura_municipio, codigo_ine)
