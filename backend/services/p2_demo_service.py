"""
Servicio P2 - Consulta C3: Inercia Demográfica y Variación Poblacional (INE 2015-2025)
Responsable: Desarrollador P2
"""

from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession


def classify_demographic_inertia(
    var_10a: float, var_5a: float, tasa_env: float, pob_actual: int
) -> str:
    """
    TODO: Clasificar mediante reglas de negocio el diagnóstico demográfico del municipio
    a partir de su variación a 10 años (`var_10a`), variación a 5 años (`var_5a`),
    tasa de envejecimiento (`tasa_env`) y población actual (`pob_actual`).
    Ejemplos de etiquetas:
    - "Fragilidad Extrema / Hiper-envejecimiento"
    - "Regresión Estructural y Riesgo de Despoblación"
    - "Expansión Dinámica y Atracción Residencial"
    - "Estabilidad Moderada con Envejecimiento Progresivo"
    """
    pass


async def get_demografia_summary_all(db: AsyncSession) -> Dict[str, Dict]:
    """
    TODO (Consulta C3 agregada): Consultar la tabla `demografia_anual` agrupando por
    `codigo_ine` para extraer la población en 2015, 2020 y 2025, mayores de 65,
    menores de 15 y tasa de envejecimiento en 2025.
    Calcular para cada municipio:
    - `variacion_10a_pct`: ((pob_2025 - pob_2015) / pob_2015) * 100
    - `variacion_5a_pct`: ((pob_2025 - pob_2020) / pob_2020) * 100
    - `ratio_reemplazo_pct`: (menor_15 / mayor_65) * 100
    - `inercia_demografica`: llamando a `classify_demographic_inertia(...)`
    Retornar un diccionario indexado por `codigo_ine`.
    """
    pass


async def get_demografia_serie_by_municipio(
    db: AsyncSession, codigo_ine: str, importe_total_ayudas_hab: float = 0.0
) -> Optional[Dict]:
    """
    TODO: Obtener la serie histórica anual (2015 a 2025) de `demografia_anual`
    para el `codigo_ine` indicado, ordenada por `anio ASC`.
    Cruzar cada año con una estimación ponderada de `ayudas_estimadas_hab_anio`
    para que el gráfico dual de Chart.js en el frontend pueda superponer la curva
    de población frente a las subvenciones por habitante.
    """
    pass
