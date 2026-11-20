"""
Servicio P2 - Consulta C3 e Ingesta Bajo Demanda de Series Demográficas (INE 2015-2025)
Responsable: Desarrollador P2

-----------------------------------------------------------------------------
[Notas para entender el fichero]
Este fichero hace tres cosas:
  1. Carga bajo demanda: si en el frontend se pulsa un municipio que aún no tiene datos → se llama
     al ETL, que lo descarga de la tabla 2881 del INE y lo guarda en la BD.
  2. Consulta 3: calcula a partir de demografia_anual la variación de población a 10 y a 5 años.
  3. Clasificación: según esas variaciones se asigna al municipio una etiqueta de «inercia
     demográfica» y se comprueba si conserva una población mínima (masa crítica).

Criterio de cálculo (todas las funciones pasan por calcular_indicadores(), así los resultados cuadran):
  - anio_actual          = el año más reciente de ese municipio en la tabla (ahora mismo 2025)
  - poblacion_actual     = población en anio_actual
  - poblacion_inicial_10a= población en anio_actual - 10 (2015)
  - poblacion_5a         = población en anio_actual - 5 (2020)
  - variacion_Na_pct     = (P_actual - P_base) / P_base × 100, redondeado a 2 decimales
  Si falta un año o P_base = 0, la variación es None (ni se inventa ni se rompe).

  El «año más reciente» no está fijado en el código: se saca de la BD (max() en Python, MAX(anio) en SQL).
  Los datos de demografia_anual solo llegan desde el ETL, y el ETL solo escribe los años entre
  ANIO_INICIO y ANIO_FIN de etl_ine.py (2015–2025), así que aquí el «año más reciente» coincide
  automáticamente con el del ETL y nunca saldrá un 2026.
  Si algún día se cambia ANIO_FIN a 2026, hay que volver a ejecutar el ETL para todos los municipios
  ya cargados (el ON CONFLICT añadirá el año nuevo); si no, los municipios cargados antes y los
  cargados después tendrían un «año más reciente» distinto.

Los datos por edad (poblacion_mayor_65, tasa_envejecimiento, etc.) están de momento todos a NULL;
el motivo está explicado al principio de etl/p2_ine/etl_ine.py, en la parte sobre la tabla 69744.
-----------------------------------------------------------------------------
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# =============================================================================
# Umbrales de clasificación (provisionales, pendientes de confirmar en el grupo)
# =============================================================================
# Salvo que se diga otra cosa, todos son «variación acumulada en 10 años, en %».

# -20 %: en 10 años se pierde 1 de cada 5 vecinos, más o menos un -2,2 % anual (compuesto).
# A ese ritmo es muy difícil mantener servicios como la escuela o el consultorio: lo tratamos como «colapso».
UMBRAL_COLAPSO_PCT = -20.0

# ±5 %: un ±5 % en 10 años es más o menos un ±0,5 % al año. En pueblos de unas decenas o centenas
# de habitantes eso son unas pocas familias que llegan o se van, una oscilación normal; por eso dentro de ±5 % es «estancamiento».
UMBRAL_DECLIVE_PCT = -5.0
UMBRAL_CRECIMIENTO_PCT = 5.0

# 50 habitantes: con tan poca gente, que se vaya una sola familia ya es un -5 %/-10 %; mientras siga
# bajando lo consideramos en riesgo de «colapso», haya llegado o no la caída al -20 %.
POBLACION_MINIMA_COLAPSO = 50

# 100 habitantes: en la dimensión «Tamaño de los municipios» de la tabla 2881 del INE, el tramo más
# pequeño es «Menos de 101» (≤100 hab.) y el siguiente «De 101 a 500».
# Ojo: siguiendo al pie de la letra los tramos del INE, «salir del tramo más pequeño» sería > 100; aquí usamos
# ≥ 100 según la regla provisional del grupo. Las dos opciones solo se diferencian si la población es justo 100.
UMBRAL_MASA_CRITICA = 100

# Etiquetas de clasificación
COLAPSO = "COLAPSO"
DECLIVE = "DECLIVE"
ESTANCAMIENTO = "ESTANCAMIENTO"
RECUPERACION = "RECUPERACION"
REPUNTE_RECIENTE = "REPUNTE_RECIENTE"
SIN_DATOS = "SIN_DATOS"


# =============================================================================
# 1. Funciones de cálculo puras (no tocan la BD, así se pueden probar por separado)
# =============================================================================

def calcular_variacion_pct(actual: Optional[int], base: Optional[int]) -> Optional[float]:
    """
    (actual - base) / base × 100, redondeado a 2 decimales.
    Devuelve None si falta alguno de los dos años (None) o si base == 0 (no se puede dividir entre 0).
    """
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
    Asigna al municipio una etiqueta de «inercia demográfica» según sus variaciones. Las reglas se
    evalúan por orden de prioridad, de arriba abajo, y se devuelve la primera que se cumpla:

      1. SIN_DATOS        var_10a es None (falta el dato de hace 10 años), no se puede valorar
      2. COLAPSO          var_10a ≤ -20 %, o bien población < 50 y var_10a < 0
      3. REPUNTE_RECIENTE var_10a < 0 pero var_5a > 0 (a 10 años baja, pero en los últimos 5 se recupera)
      4. DECLIVE          -20 % < var_10a ≤ -5 %
      5. ESTANCAMIENTO    -5 % < var_10a < +5 %
      6. RECUPERACION     var_10a ≥ +5 % y var_5a > 0
      7. Lo que queda: var_10a ≥ +5 % pero var_5a ≤ 0 (o sin dato)
         → va a ESTANCAMIENTO: el crecimiento se dio en los primeros 5 años y en los últimos 5
           ya se ha frenado o ha retrocedido, así que no se puede decir que «se esté recuperando».
           Esta regla la hemos añadido nosotros; pendiente de confirmar en el grupo.

    Por qué REPUNTE_RECIENTE va antes de DECLIVE / ESTANCAMIENTO pero después de COLAPSO:
      la recuperación de los últimos 5 años refleja mejor la situación actual que la tendencia a
      10 años, así que tiene prioridad; pero en un pueblo que ya ha colapsado (o con muy poca
      población), un repunte a corto plazo no basta para cambiar el diagnóstico.

    tasa_env (tasa de envejecimiento): de momento no hay datos de edad y siempre llega None, así que
    las reglas no la usan todavía. El parámetro se mantiene para poder añadir reglas cuando haya
    datos sin que quien llama tenga que cambiar nada.
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
    return ESTANCAMIENTO


def preserva_masa_critica(pob_actual: Optional[int]) -> bool:
    """Indica si la población alcanza el mínimo (el umbral se explica en UMBRAL_MASA_CRITICA). Sin dato devuelve False."""
    return pob_actual is not None and pob_actual >= UMBRAL_MASA_CRITICA


def calcular_indicadores(
    poblacion_por_anio: Dict[int, int], tasa_env: Optional[float] = None
) -> Optional[Dict]:
    """
    Recibe el {año: población} de un municipio y devuelve todos los indicadores que necesita la Consulta 3.
    La llaman las dos funciones de consulta del service y el script de análisis offline, para que el criterio sea el mismo.
    Si la entrada está vacía devuelve None.
    """
    if not poblacion_por_anio:
        return None

    anio_actual = max(poblacion_por_anio)
    pob_actual = poblacion_por_anio[anio_actual]
    # dict.get: si ese año no existe devuelve None, y las funciones siguientes ya saben tratar el None
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
    """Las columnas NUMERIC se leen como Decimal; se pasan a float para JSON/pydantic y None se queda en None."""
    return None if valor is None else float(valor)


# =============================================================================
# 2. Carga bajo demanda (Ingesta Híbrida Bajo Demanda)
# =============================================================================

def _importar_ingesta():
    """
    Importa ingest_ine_for_municipio del ETL.

    - En Docker: backend/Dockerfile copia etl/ a /app/etl y define
      PYTHONPATH=/app/backend:/app/etl, así que basta con `from p2_ine.etl_ine import ...`.
    - En local: normalmente se arranca desde backend/ y etl/ no está en sys.path.
      Este fichero está en <raíz>/backend/services/; subiendo dos niveles se llega a la raíz,
      y el etl/ de la raíz es la carpeta que buscamos (en Docker coincide con /app/etl): se añade a sys.path.
    p2_ine no tiene __init__.py; Python 3 lo trata como «paquete de espacio de nombres» y se importa igual.

    El import va dentro de la función (y no al principio del fichero): así el ETL solo se importa cuando
    de verdad hace falta una carga bajo demanda, y ni el arranque del backend ni el resto de endpoints se ven afectados.
    """
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
    TODO (Ingesta Híbrida Bajo Demanda - P2):
    Verificar si existen filas en `demografia_anual` para `codigo_ine`.
    - Si NO existen (el municipio aún no había sido seleccionado en el Frontend):
      llamar a `ingest_ine_for_municipio(codigo_ine)` (de `p2_ine.etl_ine`) para
      descargar en vivo la serie 2015-2025 del INE (o fallback local) y guardarla
      permanentemente en `demografia_anual`.
    - Retornar el número de registros insertados.

    Notas de implementación:
    - Si ya hay datos → devuelve 0 sin llamar al INE (la BD hace de caché).
    - Si no hay datos → llama al ETL para descargar y guardar, y devuelve el número de filas escritas.
      Si el municipio no está en la tabla municipios o falla el acceso al INE, el ETL lo deja en el
      log y devuelve 0, sin lanzar excepción.
      (No hay datos locales de respaldo: la única fuente es la tabla 2881 del INE.)

    Por qué asyncio.to_thread:
      FastAPI atiende todas las peticiones con un único event loop. Una función async solo cede el
      control en los await. ingest_ine_for_municipio es una función síncrona normal: tanto la descarga
      del INE con requests como la escritura con psycopg2 «bloquean» el hilo actual hasta terminar
      (la descarga tarda alrededor de 1 segundo). Si se llamara directamente dentro de la función async,
      todo el event loop se quedaría parado ese tiempo y las peticiones de los demás usuarios tendrían que esperar.
      asyncio.to_thread la ejecuta en otro hilo, el event loop sigue atendiendo otras peticiones,
      y el await espera a que ese hilo acabe para recoger el valor devuelto.

    Sobre las transacciones: el ETL usa su propia conexión psycopg2 y hace su propio commit al terminar.
      El nivel de aislamiento por defecto de PostgreSQL es READ COMMITTED: cada sentencia ve lo que ya
      se ha confirmado antes, así que las consultas posteriores con db (esta AsyncSession) leen las filas recién escritas.
      Si dos peticiones cargan a la vez el mismo municipio no pasa nada: el ETL escribe con ON CONFLICT y el resultado es el mismo.
    """
    resultado = await db.execute(
        text("SELECT EXISTS (SELECT 1 FROM demografia_anual WHERE codigo_ine = :codigo)"),
        {"codigo": codigo_ine},
    )
    if resultado.scalar():
        return 0

    ingest_ine_for_municipio = _importar_ingesta()
    return await asyncio.to_thread(ingest_ine_for_municipio, codigo_ine)


# =============================================================================
# 3. Consulta 3: consultas
# =============================================================================

# Una sola consulta trae lo que hace falta de todos los municipios ya cargados:
#   - ultimo: el año más reciente de cada municipio
#   - consulta principal: solo coge las filas de 3 años (el último, -5 y -10) y con FILTER las «pasa a columnas»,
#     de modo que cada municipio queda en una fila: pob_actual, pob_5a, pob_10a, tasa_env.
#   FILTER (WHERE ...) es sintaxis de PostgreSQL: solo pasa a la función de agregación las filas que cumplen la condición.
#   Cada (codigo_ine, anio) tiene una única fila (es la PK), así que el MAX simplemente devuelve ese valor.
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

# Serie completa de un municipio. El JOIN con municipios solo sirve para sacar nombre (el schema de respuesta lo exige);
# la FK garantiza que todo municipio de demografia_anual existe en municipios.
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
    TODO (Consulta C3 agregada): Consultar `demografia_anual` agrupando por `codigo_ine`
    para los municipios ya hidratados en la base de datos.

    Devuelve {codigo_ine: diccionario de indicadores}; los campos están en calcular_indicadores().
    Solo incluye los municipios ya cargados; no dispara la carga bajo demanda (si no, habría que descargar muchos de golpe).
    """
    resultado = await db.execute(SQL_SUMMARY_ALL)

    resumen: Dict[str, Dict] = {}
    for fila in resultado.mappings():
        anio = fila["anio_actual"]
        # Reconstruimos {año: población} con los 3 años obtenidos y se lo pasamos a la función de cálculo común;
        # los años que faltan (valor None) ni se meten, y calcular_indicadores los trata como ausentes
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
    TODO: Primero asegurarse de que la demografía del municipio esté en BD llamando a
    `await hydrate_demografia_on_demand(db, codigo_ine)`.
    Luego consultar y devolver la serie histórica 2015-2025 para Chart.js.

    El diccionario devuelto sirve tal cual para construir DemografiaSerieResponseSchema; si el municipio
    no tiene ningún dato devuelve None (por ejemplo, si no está en la tabla municipios o falla el acceso
    al INE), y main.py puede responder con un 404.

    Campos que son de otros compañeros (cobertura_fibra_pct viene de P1, distancia_urgencias_km de P3,
    num_ayudas_abiertas de P4): P2 no consulta las tablas de los demás; main.py obtiene esos valores
    de los services correspondientes y los pasa como argumentos con nombre, y aquí se copian tal cual
    al resultado; si no se pasan, quedan en None.
    El * delante de esos parámetros obliga a pasarlos por nombre, para no equivocarse con el orden.

    importe_total_ayudas_hab: parámetro que ya estaba; se conserva para no cambiar la firma acordada,
    pero P2 de momento no lo usa (las «ayudas por habitante» de la gráfica del frontend son datos de P4).

    Además de los campos que exige el schema, el resultado lleva variacion_5a_pct, inercia_demografica,
    preserva_masa_critica, etc. (pydantic ignora las claves sobrantes al construir el schema),
    que main.py puede aprovechar directamente al montar MunicipioDetailSchema.
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
    # Está ordenado por anio, así que la última fila es el año más reciente
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
