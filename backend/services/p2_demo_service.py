"""
Servicio P2 - Consulta C3 e Ingesta Bajo Demanda de Series Demográficas (INE 2015-2025)
Responsable: Desarrollador P2
"""

from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession


def classify_demographic_inertia(
    var_10a: float, var_5a: float, tasa_env: float, pob_actual: int
) -> str:
    """
    TODO: Clasificar mediante reglas de negocio el diagnóstico demográfico del municipio.
    """
    pass


async def hydrate_demografia_on_demand(db: AsyncSession, codigo_ine: str) -> int:
    """
    TODO (Ingesta Híbrida Bajo Demanda - P2):
    Verificar si existen filas en `demografia_anual` para `codigo_ine`.
    - Si NO existen (el municipio aún no había sido seleccionado en el Frontend):
      llamar a `ingest_ine_for_municipio(codigo_ine)` (de `p2_ine.etl_ine`) para
      descargar en vivo la serie 2015-2025 del INE (o fallback local) y guardarla
      permanentemente en `demografia_anual`.
    - Retornar el número de registros insertados.
    """
    pass


async def get_demografia_summary_all(db: AsyncSession) -> Dict[str, Dict]:
    """
    TODO (Consulta C3 agregada): Consultar `demografia_anual` agrupando por `codigo_ine`
    para los municipios ya hidratados en la base de datos.
    """
    pass


async def get_demografia_serie_by_municipio(
    db: AsyncSession, codigo_ine: str, importe_total_ayudas_hab: float = 0.0
) -> Optional[Dict]:
    """
    TODO: Primero asegurarse de que la demografía del municipio esté en BD llamando a
    `await hydrate_demografia_on_demand(db, codigo_ine)`.
    Luego consultar y devolver la serie histórica 2015-2025 para Chart.js.
    """
    pass
