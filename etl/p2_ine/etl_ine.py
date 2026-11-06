#!/usr/bin/env python3
"""
Módulo ETL P2 - API REST Tempus del Instituto Nacional de Estadística (INE)
Responsable: Desarrollador P2

Objetivo:
Conectarse directamente a la API REST JSON Tempus del INE (Tabla 2881 y Tabla 69744)
para descargar las series anuales de población de los municipios de la Comunidad de
Madrid e insertarlas en la tabla distribuida `demografia_anual`.

Ejecución aislada:
    python etl/p2_ine/etl_ine.py
"""


def get_db_connection():
    """
    TODO: Crear y devolver una conexión `psycopg2` a PostgreSQL.
    """
    pass


def fetch_ine_series_api(codigo_ine: str | None = None) -> list[dict]:
    """
    TODO: Realizar la petición HTTP GET directamente a la API REST JSON Tempus del INE:
    - Endpoint Tabla 2881: `https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2881`
    - Endpoint Tabla 69744: `https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/69744`
    Parsear el JSON devuelto por el INE (filtrando la serie de `"Total"` de habitantes
    para el `codigo_ine` solicitado o para los municipios de Madrid `28xxx`) y extraer
    para cada año (`Anyo` en el JSON de Tempus) su valor (`Valor` -> `poblacion`).
    """
    pass


def ingest_ine_for_municipio(codigo_ine: str, conn=None) -> int:
    """
    TODO (Fase 2 - Ingesta Bajo Demanda desde API del INE):
    1. Llamar en vivo a `fetch_ine_series_api(codigo_ine=codigo_ine)`.
    2. Insertar los registros anuales obtenidos de la API del INE en la tabla
       `demografia_anual (codigo_ine, anio, poblacion, ...)` usando
       `ON CONFLICT (codigo_ine, anio) DO UPDATE`.
    3. Retornar el número de años insertados en PostgreSQL.
    """
    pass


def run_etl_p2(target_codes: list[str] | None = None) -> str:
    """
    TODO (Fase 1 - Carga Inicial Ligera):
    1. Recorrer los códigos INE de `target_codes` (o los municipios registrados en BD)
       y llamar a `ingest_ine_for_municipio(code, conn)` para descargar sus datos reales del INE.
    2. Imprimir: `[ETL P2-INE] Obteniendo series anuales de la API del INE... OK.`
    """
    pass


if __name__ == "__main__":
    run_etl_p2()
