"""
Servicio P1 - Consulta Geográfica y Territorial Base (NGBE / IGN + Infraestructura)
Responsable: Desarrollador P1
"""

from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession


async def get_all_municipios_base(db: AsyncSession) -> List[Dict]:
    """
    TODO: Consultar en PostgreSQL todos los municipios de la tabla `municipios`
    haciendo un `LEFT JOIN` con `metricas_infraestructura` (por `codigo_ine`)
    y ordenar alfabéticamente por `nombre`.
    Devolver una lista de diccionarios con:
    `codigo_ine`, `nombre`, `comarca`, `altitud_m`, `superficie_km2`, `latitud`,
    `longitud`, `cobertura_5g_pct`, `cobertura_fibra_pct`, `viviendas_vacias_pct`,
    `precio_m2_eur` y `servicios_basicos_score`.
    """
    pass


async def get_municipio_by_ine(db: AsyncSession, codigo_ine: str) -> Optional[Dict]:
    """
    TODO: Consultar en PostgreSQL un único municipio filtrando por `WHERE m.codigo_ine = :codigo_ine`
    junto con sus métricas de infraestructura (`LEFT JOIN metricas_infraestructura`).
    Devolver el diccionario con sus atributos o `None` si no existe.
    """
    pass
