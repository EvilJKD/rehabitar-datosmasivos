"""
Servicio P3 - Análisis Espacial PostGIS de Accesibilidad Sanitaria (KNN <->)
Responsable: Desarrollador P3
"""

from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession


async def get_nearest_emergency_all(db: AsyncSession) -> Dict[str, Dict]:
    """
    TODO: Ejecutar una consulta espacial en PostGIS que obtenga para cada municipio
    su centro sanitario con urgencias 24h (`tiene_urgencias = TRUE`) más cercano.
    Requisitos PostGIS:
    - Usar `CROSS JOIN LATERAL` (o subconsulta correlacionada) ordenando por el
      operador espacial KNN `ORDER BY m.geom <-> cs.geom LIMIT 1` para aprovechar el índice GiST.
    - Calcular la distancia en línea recta en kilómetros usando
      `ST_DistanceSphere(m.geom, cs.geom) / 1000.0`.
    Devolver un diccionario indexado por `codigo_ine`.
    """
    pass


async def get_nearest_health_centers_for_municipio(
    db: AsyncSession, codigo_ine: str
) -> Dict[str, Optional[Dict]]:
    """
    TODO: Dado un `codigo_ine`, ejecutar la búsqueda KNN en PostGIS (`ORDER BY m.geom <-> cs.geom LIMIT 1`)
    para encontrar:
    1. `"urgencias"`: El centro con `tiene_urgencias = TRUE` más cercano.
    2. `"consultorio"`: El centro sanitario o consultorio local más cercano (con o sin urgencias).
    Devolver un diccionario `{"urgencias": ..., "consultorio": ...}`.
    """
    pass
