#!/usr/bin/env python3
"""
Módulo ETL P2 - API REST Tempus del Instituto Nacional de Estadística (INE)
Responsable: Desarrollador P2

Objetivo:
Conectarse directamente a la API REST JSON Tempus del INE (Tabla 2881)
para descargar las series anuales de población de los municipios de la Comunidad de
Madrid e insertarlas en la tabla distribuida `demografia_anual`.

Ejecución aislada:
    python etl/p2_ine/etl_ine.py                      # carga los municipios semilla en BD
    python etl/p2_ine/etl_ine.py --dry-run 28070      # solo descarga e imprime (sin BD)

-----------------------------------------------------------------------------
[Notas para entender el fichero]
ETL = Extract (descargar del INE) → Transform (dejarlo como año/población) → Load (escribirlo en PostgreSQL)

Quién llama a quién:
    run_etl_p2(["28070", "28027"])
        └─ ingest_ine_for_municipio("28070")
              ├─ fetch_ine_series_api("28070")   ← E + T
              │     └─ _download_tabla(2881)     ← población total
              └─ INSERT ... ON CONFLICT ...      ← L

La única fuente de datos es la tabla 2881 de INE Tempus; no hay ficheros locales de respaldo.

Sobre la tabla 69744 (no se usa por ahora):
  En el repo se daba por hecho que era «población por grupos de edad», pero al comprobarla en la API
  real resulta que son los datos de inmigraciones entre municipios de la Estadística de Migraciones
  (Inmigraciones intermunicipales). Sus únicas dimensiones son: provincia/municipio de destino (de toda
  España) × país de nacimiento × sexo, solo para 2021–2024, y no tiene dimensión de edad. Así que de
  momento no se cargan datos por edad: las columnas poblacion_mayor_65, poblacion_menor_15 y
  tasa_envejecimiento se escriben como None (en la BD quedan a NULL, que significa «sin dato», no
  «0 personas»). De dónde sacar los datos de edad queda pendiente de hablarlo en el grupo.
-----------------------------------------------------------------------------
"""

import argparse
import os
import re
import sys

import requests

# =============================================================================
# Configuración (todo se puede sobrescribir con variables de entorno)
# =============================================================================

# Endpoint de INE Tempus que devuelve «la tabla entera»; al final se le añade el número de tabla
INE_TEMPUS_BASE = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA"
TABLA_POBLACION_TOTAL = os.getenv("INE_TABLA_POBLACION", "2881")   # Padrón: población por municipios

# Rango de años que pide el proyecto: 2015–2025
ANIO_INICIO = 2015
ANIO_FIN = 2025

# La tabla entera pesa bastante y 4 segundos (el valor por defecto de EXTERNAL_API_TIMEOUT) pueden no bastar, así que el INE lleva su propio timeout
INE_TIMEOUT = float(os.getenv("INE_API_TIMEOUT", "30"))

# Si no se indica ningún municipio y tampoco hay ninguno en la BD, se usan estos dos municipios semilla (igual que en docker-compose)
DEFAULT_SEED_CODES = os.getenv("INITIAL_SEED_CODES", "28070,28027")

# Caché sencilla en memoria: dentro de una misma ejecución, cada tabla se descarga una sola vez.
# Si no, habría que volver a bajar la tabla entera por cada municipio procesado.
_CACHE_TABLAS: dict[str, list[dict]] = {}


def log(msg: str) -> None:
    """Prefijo común en los logs, para encontrar fácilmente los mensajes de P2 en la salida de docker compose."""
    print(f"[ETL P2-INE] {msg}", flush=True)


# =============================================================================
# 0. Conexión a la base de datos
# =============================================================================

def get_db_connection():
    """
    Crear y devolver una conexión `psycopg2` a PostgreSQL.

    Se usa primero DATABASE_URL_SYNC (docker-compose se la define al ETL);
    si no está, se monta la conexión con las variables POSTGRES_* por separado.
    Para probar en local desde VS Code, POSTGRES_HOST vale localhost por defecto
    (docker-compose publica el puerto 5432 de la BD en el propio equipo).
    """
    # El import va dentro de la función: así el modo --dry-run funciona aunque no esté instalado psycopg2
    import psycopg2

    url = os.getenv("DATABASE_URL_SYNC")
    if url:
        return psycopg2.connect(url)

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "rehabitar"),
        password=os.getenv("POSTGRES_PASSWORD", "rehabitar_pwd"),
        dbname=os.getenv("POSTGRES_DB", "rehabitar_db"),
    )


# =============================================================================
# 1. EXTRACT: descargar la tabla entera de INE Tempus
# =============================================================================

def _download_tabla(id_tabla: str) -> list[dict]:
    """
    Descarga una tabla del INE y devuelve la lista de «series».

    Respuesta real de la tabla 2881 (con tip=AM, comprobada con datos reales). Cada elemento es una serie
    temporal; hay 540 en total = 180 unidades (provincia de Madrid + 179 municipios) × 3 sexos (total/hombres/mujeres):
    [
      {
        "COD": "DPOP13129",
        "Nombre": "Hiruela, La. Total. Total habitantes. Personas. ",
        "T3_Unidad": "Personas",
        "MetaData": [                     ← solo aparece al añadir tip=AM
            {"Id": ..., "T3_Variable": "Municipios", "Nombre": "Hiruela, La", "Codigo": "28069"},
            {"Id": 451, "T3_Variable": "Sexo", "Nombre": "Total", "Codigo": "0"},
            {"T3_Variable": "Tamaño de los municipios", "Nombre": "Total habitantes", "Codigo": "0"},
            {"T3_Variable": "Tipo de dato", "Nombre": "Personas", "Codigo": ""}
        ],
        "Data": [                         ← en orden descendente de año: el más reciente va primero
            {"Fecha": "2025-01-01T00:00:00.000+01:00", "T3_TipoDato": "Definitivo",
             "T3_Periodo": "A", "Anyo": 2025, "Valor": 88.0},
            {"Anyo": 2024, ...}, ..., {"Anyo": 2015, "Valor": 54.0}
        ]
      },
      ...
    ]
    Ojo:
      - El nombre de la dimensión está en "T3_Variable"; el valor en "Nombre" y el código en "Codigo".
      - Codigo de Sexo: 0 = Total, 1 = Hombres, 2 = Mujeres.
      - La serie del total provincial usa "Provincias" (Codigo "28"), no "Municipios".

    Parámetros:
      tip=AM  → devuelve el formato «amigable» con metadatos (MetaData), que incluye el código de municipio
                (p. ej. 28069), así no hay que emparejar por nombre.
      date=AAAAMMDD:AAAAMMDD → solo los datos de ese rango de fechas; aquí, 20150101:20251231.

    Por qué date y no nult («los últimos N periodos»):
      nult=11 cuenta hacia atrás desde el último año publicado por el INE. Cuando el INE publique 2026,
      nult=11 pasará a ser 2016–2026; tras el filtro 2015–2025 de más abajo solo quedarían 10 años,
      se perdería 2015 y ya no se podría calcular la variación a 10 años. date fija un rango de años
      concreto: publique el INE hasta el año que sea, siempre se recibe 2015–2025.
      (Comprobado en la API real: date=20150101:20251231 devuelve exactamente 11 años.
       Cuidado con pasar nult a la vez: si van los dos, nult vuelve a recortar los últimos N periodos dentro del rango.)
      Cada dato del Padrón tiene fecha 1 de enero de su año, así que un rango de 0101 a 1231 incluye todos los años.
      En _serie_a_diccionario() se mantiene el filtro 2015–2025 como segunda red de seguridad.
    """
    if id_tabla in _CACHE_TABLAS:
        return _CACHE_TABLAS[id_tabla]

    url = f"{INE_TEMPUS_BASE}/{id_tabla}"
    params = {"tip": "AM", "date": f"{ANIO_INICIO}0101:{ANIO_FIN}1231"}

    log(f"Descargando tabla {id_tabla} de la API Tempus del INE...")
    resp = requests.get(url, params=params, timeout=INE_TIMEOUT)
    resp.raise_for_status()           # si no es HTTP 200, aquí se lanza una excepción directamente
    series = resp.json()

    if not isinstance(series, list):
        raise ValueError(f"Respuesta inesperada del INE para la tabla {id_tabla}")

    log(f"Tabla {id_tabla}: {len(series)} series recibidas.")
    _CACHE_TABLAS[id_tabla] = series
    return series


# =============================================================================
# 2. TRANSFORM: escoger de las series las de un municipio y dejarlas como {año: población}
# =============================================================================

def _metadatos(serie: dict) -> list[dict]:
    """Saca de forma segura el MetaData de una serie (si no hay, devuelve una lista vacía)."""
    return serie.get("MetaData") or []


def _es_del_municipio(serie: dict, codigo_ine: str) -> bool:
    """
    Indica si esta serie corresponde a este municipio.
    Primera opción: que algún elemento del MetaData tenga un Codigo igual a '28070'.
    Alternativa: que el nombre empiece por el código (en algunas tablas el nombre es del tipo '28070 Hiruela, La').
    """
    for md in _metadatos(serie):
        if str(md.get("Codigo", "")).strip() == codigo_ine:
            return True
    return str(serie.get("Nombre", "")).strip().startswith(codigo_ine)


def _valor_variable(serie: dict, nombre_variable: str) -> str | None:
    """
    Devuelve el valor de una dimensión. Por ejemplo, nombre_variable='Sexo' → devuelve 'Total' / 'Hombres' / 'Mujeres'.
    Si la serie no tiene esa dimensión, devuelve None.
    """
    for md in _metadatos(serie):
        # En el formato real de tip=AM, el nombre de la dimensión va en "T3_Variable" (p. ej. "Sexo", "Municipios"),
        # no en un {"Variable": {"Nombre": ...}} anidado
        if nombre_variable.lower() in str(md.get("T3_Variable", "")).lower():
            return str(md.get("Nombre", "")).strip()
    return None


def _es_sexo_total(serie: dict) -> bool:
    """
    Solo nos interesa el total de ambos sexos, no las series de hombres o de mujeres por separado.
    Si la tabla ni siquiera tiene la dimensión «sexo», la tomamos como total.
    """
    sexo = _valor_variable(serie, "Sexo")
    if sexo is None:
        # Si no hay metadatos, como plan B miramos el nombre
        nombre = str(serie.get("Nombre", "")).lower()
        return "hombres" not in nombre and "mujeres" not in nombre
    return sexo.lower().startswith("total") or sexo.lower().startswith("ambos")


def _serie_a_diccionario(serie: dict) -> dict[int, int]:
    """
    Convierte el Data de una serie en {año: población}, quedándose solo con 2015–2025 y saltando los valores vacíos.
    En Tempus cada punto tiene la forma {"Anyo": 2023, "Valor": 47.0}.
    """
    resultado: dict[int, int] = {}
    for punto in serie.get("Data") or []:
        anio = punto.get("Anyo")
        valor = punto.get("Valor")
        if anio is None or valor is None:      # el INE deja vacíos los datos protegidos por secreto estadístico
            continue
        anio = int(anio)
        if ANIO_INICIO <= anio <= ANIO_FIN:
            resultado[anio] = int(round(float(valor)))
    return resultado


def fetch_ine_series_api(codigo_ine: str | None = None) -> list[dict]:
    """
    Realizar la petición HTTP GET directamente a la API REST JSON Tempus del INE
    y devolver la serie anual 2015-2025 del municipio.

    Formato devuelto (una fila por año, que corresponde exactamente a las columnas de demografia_anual):
    [
      {"codigo_ine": "28069", "anio": 2015, "poblacion": 54,
       "poblacion_mayor_65": None, "poblacion_menor_15": None, "tasa_envejecimiento": None},
      ...
    ]
    Si codigo_ine es None, devuelve los datos de todos los municipios de Madrid (28xxx) de la tabla.
    """
    series = _download_tabla(TABLA_POBLACION_TOTAL)

    # ---- 1) Población total: de la tabla 2881 nos quedamos con la serie de este municipio para ambos sexos ----
    poblacion_por_municipio: dict[str, dict[int, int]] = {}
    for serie in series:
        if not _es_sexo_total(serie):
            continue
        codigos = [codigo_ine] if codigo_ine else _codigos_madrid_en_serie(serie)
        for codigo in codigos:
            if _es_del_municipio(serie, codigo):
                datos = _serie_a_diccionario(serie)
                if datos:
                    poblacion_por_municipio.setdefault(codigo, {}).update(datos)

    if codigo_ine and codigo_ine not in poblacion_por_municipio:
        log(f"AVISO: el municipio {codigo_ine} no aparece en la tabla {TABLA_POBLACION_TOTAL}.")
        return []

    # ---- 2) Montar las filas finales ----
    # De momento no hay ninguna fuente de datos por edad utilizable (ver la nota sobre la tabla 69744 al principio del fichero),
    # así que las tres columnas de edad van a None. psycopg2 convierte None en NULL de SQL,
    # que significa «sin dato»; un 0 se entendería como «0 personas mayores».
    filas: list[dict] = []
    for codigo, por_anio in poblacion_por_municipio.items():
        for anio in sorted(por_anio):
            filas.append({
                "codigo_ine": codigo,
                "anio": anio,
                "poblacion": por_anio[anio],
                "poblacion_mayor_65": None,
                "poblacion_menor_15": None,
                "tasa_envejecimiento": None,
            })
    return filas


def _codigos_madrid_en_serie(serie: dict) -> list[str]:
    """Se usa cuando codigo_ine es None: busca en los metadatos los códigos de municipio de 5 dígitos que empiezan por 28."""
    return [
        str(md.get("Codigo")).strip()
        for md in _metadatos(serie)
        if re.fullmatch(r"28\d{3}", str(md.get("Codigo", "")).strip())
    ]


# =============================================================================
# 3. LOAD: escribir en PostgreSQL
# =============================================================================

SQL_UPSERT = """
    INSERT INTO demografia_anual
        (codigo_ine, anio, poblacion, poblacion_mayor_65, poblacion_menor_15, tasa_envejecimiento)
    VALUES
        (%(codigo_ine)s, %(anio)s, %(poblacion)s,
         %(poblacion_mayor_65)s, %(poblacion_menor_15)s, %(tasa_envejecimiento)s)
    ON CONFLICT (codigo_ine, anio) DO UPDATE SET
        poblacion           = EXCLUDED.poblacion,
        poblacion_mayor_65  = EXCLUDED.poblacion_mayor_65,
        poblacion_menor_15  = EXCLUDED.poblacion_menor_15,
        tasa_envejecimiento = EXCLUDED.tasa_envejecimiento;
"""
# Qué hace ON CONFLICT: si la fila (codigo_ine, anio) ya existe, la actualiza en vez de dar error.
# Por eso el ETL se puede ejecutar todas las veces que haga falta y el resultado es siempre el mismo (esto se llama «idempotencia»).
# EXCLUDED es «la fila que se intentaba insertar esta vez y que no entró por el conflicto».


def _municipio_existe(conn, codigo_ine: str) -> bool:
    """
    demografia_anual.codigo_ine tiene una FK hacia municipios (de la que se encarga P1).
    Si P1 todavía no ha insertado este municipio, el INSERT daría un error de clave foránea, así que lo comprobamos antes.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM municipios WHERE codigo_ine = %s", (codigo_ine,))
        return cur.fetchone() is not None


def ingest_ine_for_municipio(codigo_ine: str, conn=None) -> int:
    """
    (Fase 2 - Ingesta Bajo Demanda desde API del INE)
    1. Llamar en vivo a `fetch_ine_series_api(codigo_ine=codigo_ine)`.
    2. Insertar los registros anuales en `demografia_anual` con `ON CONFLICT ... DO UPDATE`.
    3. Retornar el número de años insertados en PostgreSQL.

    Esta función se usa desde dos sitios:
      - run_etl_p2() de este mismo fichero (al arrancar; se le pasa la conn que ya existe)
      - la carga bajo demanda de p2_demo_service.py en el backend (sin conn: la abre y la cierra ella misma)
    """
    propia_conexion = conn is None
    if propia_conexion:
        conn = get_db_connection()

    try:
        if not _municipio_existe(conn, codigo_ine):
            log(f"AVISO: {codigo_ine} no existe en `municipios` (¿se ejecutó P1?). Se omite.")
            return 0

        try:
            filas = fetch_ine_series_api(codigo_ine=codigo_ine)
        except Exception as exc:
            # Se ha caído la red, el INE no responde, timeout...: lo dejamos en el log, pero sin tumbar todo el programa
            log(f"ERROR descargando la serie de {codigo_ine}: {exc}")
            return 0

        if not filas:
            return 0

        with conn.cursor() as cur:
            cur.executemany(SQL_UPSERT, filas)   # ejecuta todas las filas de una vez
        conn.commit()                            # sin commit, los datos no se guardan de verdad
        log(f"{codigo_ine}: {len(filas)} años guardados ({filas[0]['anio']}-{filas[-1]['anio']}).")
        return len(filas)

    except Exception:
        conn.rollback()   # si algo falla se deshace la transacción, para no dejar datos a medias
        raise
    finally:
        if propia_conexion:
            conn.close()


# =============================================================================
# 4. Punto de entrada general
# =============================================================================

def _codigos_desde_bd(conn) -> list[str]:
    """Si no se pasa target_codes, se procesan todos los municipios registrados en la BD."""
    with conn.cursor() as cur:
        cur.execute("SELECT codigo_ine FROM municipios ORDER BY codigo_ine")
        return [fila[0] for fila in cur.fetchall()]


def run_etl_p2(target_codes: list[str] | None = None) -> str:
    """
    (Fase 1 - Carga Inicial Ligera)
    Recorrer los códigos INE de `target_codes` (o los municipios registrados en BD)
    y llamar a `ingest_ine_for_municipio(code, conn)`.

    Devuelve una línea de resumen que run_all.py puede imprimir.
    """
    log("Obteniendo series anuales de la API del INE...")
    conn = get_db_connection()
    try:
        codigos = target_codes or _codigos_desde_bd(conn)
        if not codigos:
            codigos = [c.strip() for c in DEFAULT_SEED_CODES.split(",") if c.strip()]

        total = 0
        for codigo in codigos:
            total += ingest_ine_for_municipio(codigo, conn)
    finally:
        conn.close()

    resumen = f"{total} filas en demografia_anual para {len(codigos)} municipios"
    log(f"Obteniendo series anuales de la API del INE... OK. ({resumen})")
    return resumen


# =============================================================================
# Punto de entrada por línea de comandos
# =============================================================================

def _fmt(valor, ancho: int, sufijo: str = "") -> str:
    """Muestra None (sin dato) como '-' y el resto alineado a la derecha. None no se puede formatear directamente con :>5, da TypeError."""
    texto = "-" if valor is None else f"{valor}{sufijo}"
    return f"{texto:>{ancho}}"


def _dry_run(codigos: list[str]) -> None:
    """Solo descarga e imprime, sin tocar la BD. Viene bien para ver por primera vez en VS Code qué pinta tienen los datos."""
    for codigo in codigos:
        filas = fetch_ine_series_api(codigo)
        print(f"\n=== {codigo}: {len(filas)} años ===")
        for f in filas:
            print(f"  {f['anio']}: {f['poblacion']:>6} hab | >65: {_fmt(f['poblacion_mayor_65'], 5)} "
                  f"| <15: {_fmt(f['poblacion_menor_15'], 5)} "
                  f"| envejec.: {_fmt(f['tasa_envejecimiento'], 6, '%')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL P2 - Padrón INE (Tempus)")
    parser.add_argument("codigos", nargs="*", help="Códigos INE, p. ej. 28070 28027")
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo descargar e imprimir, sin escribir en la base de datos")
    args = parser.parse_args()

    if args.dry_run:
        _dry_run(args.codigos or DEFAULT_SEED_CODES.split(","))
    else:
        print(run_etl_p2(args.codigos or None))
        sys.exit(0)
