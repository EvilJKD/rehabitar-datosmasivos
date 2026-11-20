#!/usr/bin/env python3
"""
Módulo ETL P2 para la descarga e ingesta de población municipal desde el INE.

Descarga la serie 2015-2025 de la tabla 2881 (API Tempus) para municipios de la
Comunidad de Madrid y la carga en `demografia_anual`. Las columnas de edad se
dejan a None mientras no exista una fuente desagregada por grupos de edad.
"""

import argparse
import os
import re
import sys

import requests

# Configuración (sobrescribible mediante variables de entorno)
INE_TEMPUS_BASE = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA"
TABLA_POBLACION_TOTAL = os.getenv("INE_TABLA_POBLACION", "2881")

ANIO_INICIO = 2015
ANIO_FIN = 2025

# Timeout específico para la descarga completa de la tabla del INE
INE_TIMEOUT = float(os.getenv("INE_API_TIMEOUT", "30"))

# Códigos semilla usados si no se pasan argumentos ni hay municipios en la BD
DEFAULT_SEED_CODES = os.getenv("INITIAL_SEED_CODES", "28078,28069,28027")

# Caché en memoria para descargar cada tabla una sola vez por ejecución
_CACHE_TABLAS: dict[str, list[dict]] = {}


def log(msg: str) -> None:
    """Imprime un mensaje de log con el prefijo del módulo P2."""
    print(f"[ETL P2-INE] {msg}", flush=True)


# Conexión a la base de datos

def get_db_connection():
    """Abre y devuelve una conexión psycopg2 usando DATABASE_URL_SYNC o las variables POSTGRES_*."""
    # Import local para permitir ejecutar --dry-run sin psycopg2 instalado
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


# Descarga desde la API Tempus del INE

def _download_tabla(id_tabla: str) -> list[dict]:
    """
    Descarga una tabla del INE para el rango ANIO_INICIO-ANIO_FIN y la guarda en caché.
    Usa el parámetro date en lugar de nult para fijar el intervalo exacto aunque se publiquen nuevos años.
    """
    if id_tabla in _CACHE_TABLAS:
        return _CACHE_TABLAS[id_tabla]

    url = f"{INE_TEMPUS_BASE}/{id_tabla}"
    params = {"tip": "AM", "date": f"{ANIO_INICIO}0101:{ANIO_FIN}1231"}

    log(f"Descargando tabla {id_tabla} de la API Tempus del INE...")
    resp = requests.get(url, params=params, timeout=INE_TIMEOUT)
    resp.raise_for_status()
    series = resp.json()

    if not isinstance(series, list):
        raise ValueError(f"Respuesta inesperada del INE para la tabla {id_tabla}")

    log(f"Tabla {id_tabla}: {len(series)} series recibidas.")
    _CACHE_TABLAS[id_tabla] = series
    return series


# Transformación de series del INE

def _metadatos(serie: dict) -> list[dict]:
    """Devuelve la lista MetaData de una serie del INE, o una lista vacía si no existe."""
    return serie.get("MetaData") or []


def _es_del_municipio(serie: dict, codigo_ine: str) -> bool:
    """Comprueba si la serie pertenece al municipio por su código en MetaData o por el prefijo del nombre."""
    for md in _metadatos(serie):
        if str(md.get("Codigo", "")).strip() == codigo_ine:
            return True
    return str(serie.get("Nombre", "")).strip().startswith(codigo_ine)


def _valor_variable(serie: dict, nombre_variable: str) -> str | None:
    """Devuelve el valor de una dimensión de MetaData (por ejemplo, Sexo), o None si no existe."""
    for md in _metadatos(serie):
        if nombre_variable.lower() in str(md.get("T3_Variable", "")).lower():
            return str(md.get("Nombre", "")).strip()
    return None


def _es_sexo_total(serie: dict) -> bool:
    """Indica si la serie corresponde al total de ambos sexos o no desagrega por sexo."""
    sexo = _valor_variable(serie, "Sexo")
    if sexo is None:
        nombre = str(serie.get("Nombre", "")).lower()
        return "hombres" not in nombre and "mujeres" not in nombre
    return sexo.lower().startswith("total") or sexo.lower().startswith("ambos")


def _serie_a_diccionario(serie: dict) -> dict[int, int]:
    """Convierte los datos de una serie en un diccionario {anio: poblacion} dentro de ANIO_INICIO-ANIO_FIN."""
    resultado: dict[int, int] = {}
    for punto in serie.get("Data") or []:
        anio = punto.get("Anyo")
        valor = punto.get("Valor")
        if anio is None or valor is None:
            continue
        anio = int(anio)
        if ANIO_INICIO <= anio <= ANIO_FIN:
            resultado[anio] = int(round(float(valor)))
    return resultado


def fetch_ine_series_api(codigo_ine: str | None = None) -> list[dict]:
    """
    Descarga de la tabla 2881 del INE la serie anual 2015-2025 de un municipio o de todos los de Madrid.
    Devuelve una lista de diccionarios con el esquema de columnas de demografia_anual.
    """
    series = _download_tabla(TABLA_POBLACION_TOTAL)

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

    # Las columnas por edad se mantienen a None mientras no haya fuente de edad
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
    """Extrae de MetaData los códigos de municipio de Madrid con formato 28xxx."""
    return [
        str(md.get("Codigo")).strip()
        for md in _metadatos(serie)
        if re.fullmatch(r"28\d{3}", str(md.get("Codigo", "")).strip())
    ]


# Carga en PostgreSQL

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


def _municipio_existe(conn, codigo_ine: str) -> bool:
    """Comprueba si codigo_ine existe en la tabla municipios para respetar la clave foránea."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM municipios WHERE codigo_ine = %s", (codigo_ine,))
        return cur.fetchone() is not None


def ingest_ine_for_municipio(codigo_ine: str, conn=None) -> int:
    """
    Descarga la serie del INE para un municipio y la guarda en demografia_anual mediante upsert.
    Devuelve el número de filas guardadas, o 0 si el municipio no existe en BD o falla la descarga.
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
            log(f"ERROR descargando la serie de {codigo_ine}: {exc}")
            return 0

        if not filas:
            return 0

        with conn.cursor() as cur:
            cur.executemany(SQL_UPSERT, filas)
        conn.commit()
        log(f"{codigo_ine}: {len(filas)} años guardados ({filas[0]['anio']}-{filas[-1]['anio']}).")
        return len(filas)

    except Exception:
        conn.rollback()
        raise
    finally:
        if propia_conexion:
            conn.close()


# Punto de entrada del ETL y CLI

def _codigos_desde_bd(conn) -> list[str]:
    """Devuelve la lista ordenada de códigos INE registrados en la tabla municipios."""
    with conn.cursor() as cur:
        cur.execute("SELECT codigo_ine FROM municipios ORDER BY codigo_ine")
        return [fila[0] for fila in cur.fetchall()]


def run_etl_p2(target_codes: list[str] | None = None) -> str:
    """
    Carga en demografia_anual los códigos de target_codes, los de BD o los códigos semilla.
    Devuelve una cadena de resumen con el total de filas y municipios procesados.
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


def _fmt(valor, ancho: int, sufijo: str = "") -> str:
    """Formatea un valor alineado a la derecha o devuelve '-' si es None."""
    texto = "-" if valor is None else f"{valor}{sufijo}"
    return f"{texto:>{ancho}}"


def _dry_run(codigos: list[str]) -> None:
    """Descarga las series del INE para los códigos indicados y las imprime sin tocar la BD."""
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
