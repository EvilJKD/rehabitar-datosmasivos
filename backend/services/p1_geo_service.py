"""
Servicio P1 - Consulta Geográfica, Estado de Hidratación e Infraestructura
Responsable: Desarrollador P1
"""

from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession


async def get_all_municipios_base(db: AsyncSession) -> List[Dict]:
    """
    TODO: Consultar en PostgreSQL todos los municipios de la tabla `municipios`
    (incluyendo las columnas `hidratado` y `ultima_ingesta`) haciendo `LEFT JOIN`
    con `metricas_infraestructura` y ordenar por `nombre ASC`.
    """
    pass


async def get_municipio_by_ine(db: AsyncSession, codigo_ine: str) -> Optional[Dict]:
    """
    TODO: Consultar en PostgreSQL un único municipio por `codigo_ine` (incluyendo
    `hidratado`, `ultima_ingesta` y sus columnas de `metricas_infraestructura`, así como
    la caché vial `distancia_carretera_urg_km`, `tiempo_urg_min`, `geometria_ruta_json`).
    Devolver el diccionario o `None` si no existe.
    """
    pass


async def hydrate_infraestructura_on_demand(db: AsyncSession, codigo_ine: str) -> Dict:
    """
    TODO (Ingesta Híbrida Bajo Demanda - P1):
    Cuando el usuario selecciona un pueblo en el Frontend que aún no tiene métricas en
    `metricas_infraestructura`, invocar la lógica de extracción de P1 (`ingest_infraestructura_municipio`)
    para consultar la fuente e insertar el registro en `metricas_infraestructura`.
    """
    pass
