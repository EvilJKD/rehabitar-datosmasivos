"""
Servicio P4 - Consulta C4 e Ingesta Bajo Demanda de Subvenciones (BDNS)
Responsable: Desarrollador P4
"""

from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession


async def hydrate_grants_on_demand(db: AsyncSession, codigo_ine: str) -> int:
    """
    TODO (Ingesta Híbrida Bajo Demanda - P4):
    Cuando el usuario selecciona un pueblo en el Frontend que aún no ha sido cruzado
    con las ayudas de la BDNS:
    1. Invocar a `ingest_bdns_for_municipio(codigo_ine)` (de `p4_bdns.etl_bdns`) para
       evaluar qué convocatorias activas aplican a su población/envejecimiento.
    2. Insertar las filas resultantes en `convocatoria_municipio` y marcar
       `municipios.hidratado = TRUE` y `municipios.ultima_ingesta = NOW()`.
    3. Retornar el número de subvenciones asignadas y guardadas en BD.
    """
    pass


async def get_grants_summary_all(db: AsyncSession) -> Dict[str, Dict]:
    """
    TODO: Consultar para todos los municipios el resumen de ayudas activas almacenadas
    hasta el momento en `convocatoria_municipio`.
    """
    pass


async def get_convocatorias(
    db: AsyncSession, codigo_ine: Optional[str] = None, categoria: Optional[str] = None
) -> List[Dict]:
    """
    TODO (Consulta C4): Listar las convocatorias de la BDNS (filtrando por `codigo_ine`
    y/o `categoria` si se proporcionan).
    """
    pass
