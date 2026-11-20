#!/usr/bin/env python3
"""ETL municipal del IGN e infraestructura de P1."""

import argparse
import os
import re
from contextlib import closing

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_values
except ImportError:  # pragma: no cover - permite ejecutar pruebas unitarias en host sin psycopg2
    psycopg2 = None  # type: ignore
    RealDictCursor = None  # type: ignore
    execute_values = None  # type: ignore

if __package__:
    from .sources import fetch_municipios_ign_api, get_coverage, get_infrastructure_lines
else:
    from sources import fetch_municipios_ign_api, get_coverage, get_infrastructure_lines


UPSERT_MUNICIPIOS = """
    INSERT INTO municipios (codigo_ine, nombre, provincia, comarca, latitud, longitud, geom)
    VALUES %s
    ON CONFLICT (codigo_ine) DO UPDATE SET
        nombre = EXCLUDED.nombre,
        provincia = EXCLUDED.provincia,
        comarca = EXCLUDED.comarca,
        latitud = EXCLUDED.latitud,
        longitud = EXCLUDED.longitud,
        geom = EXCLUDED.geom
"""

MUNICIPIO_VALUES = """
    (%(codigo_ine)s, %(nombre)s, %(provincia)s, %(comarca)s, %(latitud)s, %(longitud)s,
     ST_SetSRID(ST_MakePoint(%(longitud)s, %(latitud)s), 4326))
"""

UPSERT_INFRAESTRUCTURA = """
    INSERT INTO metricas_infraestructura (
        codigo_ine, distancia_carretera_km, distancia_recurso_hidrico_km,
        cobertura_fibra_pct, cobertura_movil_pct, fecha_actualizacion
    )
    SELECT codigo_ine,
           ST_Distance(geom::geography, ST_GeomFromGeoJSON(%s)::geography) / 1000,
           ST_Distance(geom::geography, ST_GeomFromGeoJSON(%s)::geography) / 1000,
           %s, %s, CURRENT_DATE
    FROM municipios
    WHERE codigo_ine = %s
    ON CONFLICT (codigo_ine) DO UPDATE SET
        distancia_carretera_km = EXCLUDED.distancia_carretera_km,
        distancia_recurso_hidrico_km = EXCLUDED.distancia_recurso_hidrico_km,
        cobertura_fibra_pct = EXCLUDED.cobertura_fibra_pct,
        cobertura_movil_pct = EXCLUDED.cobertura_movil_pct,
        fecha_actualizacion = EXCLUDED.fecha_actualizacion
    RETURNING codigo_ine, distancia_carretera_km::double precision,
              distancia_recurso_hidrico_km::double precision,
              cobertura_fibra_pct::double precision, cobertura_movil_pct::double precision,
              fecha_actualizacion
"""


def get_db_connection():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 no está instalado en este entorno.")
    dsn = os.getenv("DATABASE_URL_SYNC")
    if dsn:
        return psycopg2.connect(dsn, connect_timeout=10)
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "rehabitar"),
        password=os.getenv("POSTGRES_PASSWORD", "rehabitar_pwd"),
        dbname=os.getenv("POSTGRES_DB", "rehabitar_db"),
        connect_timeout=10,
    )


def ingest_infraestructura_municipio(codigo_ine: str, conn=None) -> dict:
    """Actualiza las métricas usando la transacción del llamante si proporciona una."""
    if not re.fullmatch(r"28[0-9]{3}", codigo_ine):
        raise ValueError(f"Código INE de Madrid inválido: {codigo_ine!r}.")
    if conn is None:
        with closing(get_db_connection()) as owned_connection, owned_connection:
            return _ingest_infraestructura(codigo_ine, owned_connection)
    return _ingest_infraestructura(codigo_ine, conn)


def _ingest_infraestructura(codigo_ine: str, conn) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            "SELECT latitud, longitud FROM municipios WHERE codigo_ine = %s",
            (codigo_ine,),
        )
        municipio = cursor.fetchone()
        if municipio is None:
            raise LookupError(f"No existe el municipio {codigo_ine} en el catálogo del IGN.")

        fibra, movil = get_coverage(codigo_ine)
        carreteras, agua = get_infrastructure_lines(municipio["latitud"], municipio["longitud"])
        cursor.execute(UPSERT_INFRAESTRUCTURA, (carreteras, agua, fibra, movil, codigo_ine))
        metricas = cursor.fetchone()
        if metricas is None:
            raise LookupError(f"El municipio {codigo_ine} ya no existe en el catálogo.")
        return dict(metricas)


def run_etl_p1(seed_codes: list[str] | None = None) -> str:
    """Carga el catálogo y, si se indican, las métricas de los municipios semilla."""
    municipios = fetch_municipios_ign_api()
    codes = dict.fromkeys(seed_codes or [])
    unknown = codes.keys() - {municipio["codigo_ine"] for municipio in municipios}
    if unknown:
        raise ValueError(f"Códigos semilla fuera del catálogo del IGN: {', '.join(sorted(unknown))}.")

    with closing(get_db_connection()) as conn, conn, conn.cursor() as cursor:
        execute_values(cursor, UPSERT_MUNICIPIOS, municipios, template=MUNICIPIO_VALUES)

    print(f"[ETL P1-NGBE] {len(municipios)} municipios del IGN cargados en PostGIS.")
    for codigo_ine in codes:
        ingest_infraestructura_municipio(codigo_ine)
    if codes:
        print(f"[ETL P1-NGBE] Métricas de infraestructura cargadas para {len(codes)} municipios.")
    return f"P1: {len(municipios)} municipios cargados y {len(codes)} con métricas actualizadas."


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", action="append", metavar="CODIGO_INE", help="Cargar sus métricas")
    run_etl_p1(parser.parse_args().seed)
