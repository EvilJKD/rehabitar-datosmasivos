"""
Servicio P2 para la Consulta 3 e ingesta bajo demanda de series demográficas (INE 2015-2025).

Calcula la variación poblacional a 5 y 10 años, clasifica la inercia demográfica y
comprueba la masa crítica a partir de la tabla `demografia_anual`.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Optional

from ._sa_compat import AsyncSession, text

# Umbrales provisionales de clasificación (variación acumulada en 10 años, en %)
UMBRAL_COLAPSO_PCT = -20.0
UMBRAL_DECLIVE_PCT = -5.0
UMBRAL_CRECIMIENTO_PCT = 5.0

# Con menos de 50 habitantes en descenso se considera en riesgo de colapso
POBLACION_MINIMA_COLAPSO = 50

# Mínimo de habitantes para considerar que el municipio preserva masa crítica
UMBRAL_MASA_CRITICA = 100

# Etiquetas de clasificación
COLAPSO = "COLAPSO"
DECLIVE = "DECLIVE"
ESTANCAMIENTO = "ESTANCAMIENTO"
RECUPERACION = "RECUPERACION"
REPUNTE_RECIENTE = "REPUNTE_RECIENTE"
SIN_DATOS = "SIN_DATOS"


# Cálculos de indicadores demográficos

def calcular_variacion_pct(actual: Optional[int], base: Optional[int]) -> Optional[float]:
    """Calcula la variación porcentual entre base y actual redondeada a 2 decimales, o None si falta algún dato o base es 0."""
    if actual is None or base is None or base == 0:
        return None
    return round((actual - base) / base * 100, 2)


def classify_demographic_inertia(
    var_10a: Optional[float],
    var_5a: Optional[float],
    tasa_env: Optional[float],
    pob_actual: int,
) -> str:
    """
    Asigna una etiqueta de inercia demográfica según las variaciones a 10 y 5 años y la población actual.
    Mantiene tasa_env en la firma por compatibilidad mientras no haya datos por edad.
    """
    if var_10a is None:
        return SIN_DATOS

    if var_10a <= UMBRAL_COLAPSO_PCT or (pob_actual < POBLACION_MINIMA_COLAPSO and var_10a < 0):
        return COLAPSO

    reciente_positivo = var_5a is not None and var_5a > 0

    if var_10a < 0 and reciente_positivo:
        return REPUNTE_RECIENTE
    if var_10a <= UMBRAL_DECLIVE_PCT:
        return DECLIVE
    if var_10a < UMBRAL_CRECIMIENTO_PCT:
        return ESTANCAMIENTO
    if reciente_positivo:
        return RECUPERACION
    # Si creció en el tramo inicial pero se estancó o cayó en los últimos 5 años, no se marca como recuperación
    return ESTANCAMIENTO


def preserva_masa_critica(pob_actual: Optional[int]) -> bool:
    """Indica si la población actual alcanza el umbral mínimo de masa crítica, o False si no hay dato."""
    return pob_actual is not None and pob_actual >= UMBRAL_MASA_CRITICA


def calcular_indicadores(
    poblacion_por_anio: Dict[int, int], tasa_env: Optional[float] = None
) -> Optional[Dict]:
    """Calcula los indicadores de Consulta 3 a partir de un diccionario {anio: poblacion}, o None si está vacío."""
    if not poblacion_por_anio:
        return None

    anio_actual = max(poblacion_por_anio)
    pob_actual = poblacion_por_anio[anio_actual]
    pob_10a = poblacion_por_anio.get(anio_actual - 10)
    pob_5a = poblacion_por_anio.get(anio_actual - 5)

    var_10a = calcular_variacion_pct(pob_actual, pob_10a)
    var_5a = calcular_variacion_pct(pob_actual, pob_5a)

    return {
        "anio_actual": anio_actual,
        "poblacion_actual": pob_actual,
        "poblacion_inicial_10a": pob_10a,
        "poblacion_5a": pob_5a,
        "variacion_10a_pct": var_10a,
        "variacion_5a_pct": var_5a,
        "tasa_envejecimiento": tasa_env,
        "inercia_demografica": classify_demographic_inertia(var_10a, var_5a, tasa_env, pob_actual),
        "preserva_masa_critica": preserva_masa_critica(pob_actual),
    }


def _a_float(valor) -> Optional[float]:
    """Convierte a float un valor numérico (por ejemplo Decimal de SQL), preservando None."""
    return None if valor is None else float(valor)


# Ingesta bajo demanda

def _importar_ingesta():
    """Importa de forma diferida ingest_ine_for_municipio añadiendo etl/ a sys.path si hace falta."""
    try:
        from p2_ine.etl_ine import ingest_ine_for_municipio
    except ImportError:
        etl_dir = Path(__file__).resolve().parents[2] / "etl"
        if str(etl_dir) not in sys.path:
            sys.path.append(str(etl_dir))
        from p2_ine.etl_ine import ingest_ine_for_municipio
    return ingest_ine_for_municipio


async def hydrate_demografia_on_demand(db: AsyncSession, codigo_ine: str) -> int:
    """
    Verifica si existen registros en demografia_anual para codigo_ine y, si faltan, lanza la ingesta desde el INE en un hilo separado.
    Devuelve el número de filas insertadas o 0 si el municipio ya estaba cargado.
    """
    resultado = await db.execute(
        text("SELECT EXISTS (SELECT 1 FROM demografia_anual WHERE codigo_ine = :codigo)"),
        {"codigo": codigo_ine},
    )
    if resultado.scalar():
        return 0

    ingest_ine_for_municipio = _importar_ingesta()
    return await asyncio.to_thread(ingest_ine_for_municipio, codigo_ine)


# Consultas para Consulta 3

# Obtiene para cada municipio cargado su año más reciente y la población de ese año, 5 años atrás y 10 años atrás
SQL_SUMMARY_ALL = text("""
    WITH ultimo AS (
        SELECT codigo_ine, MAX(anio) AS anio_actual
        FROM demografia_anual
        GROUP BY codigo_ine
    )
    SELECT u.codigo_ine,
           u.anio_actual,
           MAX(d.poblacion)           FILTER (WHERE d.anio = u.anio_actual)      AS pob_actual,
           MAX(d.poblacion)           FILTER (WHERE d.anio = u.anio_actual - 5)  AS pob_5a,
           MAX(d.poblacion)           FILTER (WHERE d.anio = u.anio_actual - 10) AS pob_10a,
           MAX(d.tasa_envejecimiento) FILTER (WHERE d.anio = u.anio_actual)      AS tasa_env
    FROM ultimo u
    JOIN demografia_anual d
      ON d.codigo_ine = u.codigo_ine
     AND d.anio IN (u.anio_actual, u.anio_actual - 5, u.anio_actual - 10)
    GROUP BY u.codigo_ine, u.anio_actual
    ORDER BY u.codigo_ine
""")

# Serie histórica completa de un municipio junto con su nombre
SQL_SERIE_MUNICIPIO = text("""
    SELECT m.nombre,
           d.anio,
           d.poblacion,
           d.poblacion_mayor_65,
           d.poblacion_menor_15,
           d.tasa_envejecimiento
    FROM demografia_anual d
    JOIN municipios m ON m.codigo_ine = d.codigo_ine
    WHERE d.codigo_ine = :codigo
    ORDER BY d.anio
""")


async def get_demografia_summary_all(db: AsyncSession) -> Dict[str, Dict]:
    """
    Devuelve los indicadores demográficos de Consulta 3 para los municipios ya presentes en demografia_anual.
    No dispara descargas bajo demanda.
    """
    resultado = await db.execute(SQL_SUMMARY_ALL)

    resumen: Dict[str, Dict] = {}
    for fila in resultado.mappings():
        anio = fila["anio_actual"]
        poblacion_por_anio = {
            a: p
            for a, p in ((anio, fila["pob_actual"]), (anio - 5, fila["pob_5a"]), (anio - 10, fila["pob_10a"]))
            if p is not None
        }
        indicadores = calcular_indicadores(poblacion_por_anio, _a_float(fila["tasa_env"]))
        resumen[fila["codigo_ine"]] = {"codigo_ine": fila["codigo_ine"], **indicadores}
    return resumen


async def get_demografia_serie_by_municipio(
    db: AsyncSession,
    codigo_ine: str,
    importe_total_ayudas_hab: float = 0.0,
    *,
    cobertura_fibra_pct: Optional[float] = None,
    distancia_urgencias_km: Optional[float] = None,
    num_ayudas_abiertas: Optional[int] = None,
) -> Optional[Dict]:
    """
    Asegura que el municipio esté cargado en demografia_anual y devuelve su serie histórica e indicadores para Consulta 3.
    Devuelve None si no existen datos tras intentar la carga e incluye sin modificarlos los valores recibidos de otros módulos.
    """
    await hydrate_demografia_on_demand(db, codigo_ine)

    resultado = await db.execute(SQL_SERIE_MUNICIPIO, {"codigo": codigo_ine})
    filas = resultado.mappings().all()
    if not filas:
        return None

    serie_anual = [
        {
            "anio": f["anio"],
            "poblacion": f["poblacion"],
            "poblacion_mayor_65": f["poblacion_mayor_65"],
            "poblacion_menor_15": f["poblacion_menor_15"],
            "tasa_envejecimiento": _a_float(f["tasa_envejecimiento"]),
        }
        for f in filas
    ]
    poblacion_por_anio = {p["anio"]: p["poblacion"] for p in serie_anual}
    # Al estar ordenada por anio, la última fila corresponde al año más reciente
    indicadores = calcular_indicadores(poblacion_por_anio, serie_anual[-1]["tasa_envejecimiento"])

    return {
        "codigo_ine": codigo_ine,
        "nombre": filas[0]["nombre"],
        **indicadores,
        "cobertura_fibra_pct": cobertura_fibra_pct,
        "distancia_urgencias_km": distancia_urgencias_km,
        "num_ayudas_abiertas": num_ayudas_abiertas,
        "serie_anual": serie_anual,
    }
