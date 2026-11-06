"""
Servicio P4 - Consulta C4: Canalización de Subvenciones y Ayudas Públicas (BDNS)
Responsable: Desarrollador P4
"""

from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession


async def get_grants_summary_all(db: AsyncSession) -> Dict[str, Dict]:
    """
    TODO: Consultar para todos los municipios el resumen de ayudas activas haciendo
    `LEFT JOIN` entre `municipios`, `convocatoria_municipio` y `convocatorias` (`activa = TRUE`).
    Agrupar por `codigo_ine` para calcular:
    - `num_ayudas_activas`: `COUNT(...)`
    - `importe_total_ayudas_hab`: `SUM(importe_estimado_hab)`
    Devolver un diccionario indexado por `codigo_ine`.
    """
    pass


async def get_convocatorias(
    db: AsyncSession, codigo_ine: Optional[str] = None, categoria: Optional[str] = None
) -> List[Dict]:
    """
    TODO (Consulta C4): Listar las convocatorias de la BDNS:
    - Si se recibe `codigo_ine`, hacer `JOIN` entre `convocatoria_municipio` y `convocatorias`
      para devolver únicamente las ayudas asignadas a ese municipio, ordenadas por
      `importe_estimado_hab DESC`.
    - Si `codigo_ine` es `None`, devolver todas las convocatorias del catálogo general.
    - Si se recibe `categoria`, filtrar adicionalmente por `c.categoria = :categoria`.
    """
    pass
