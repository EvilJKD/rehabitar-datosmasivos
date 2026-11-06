#!/usr/bin/env python3
"""
Módulo ETL P2 - Instituto Nacional de Estadística (INE API Tempus - Tabla 2881)
Responsable: Desarrollador P2

Objetivo:
Extraer las series históricas del Padrón Municipal (2015-2025) para los municipios
de la Sierra Norte de Madrid e insertarlas en la tabla `demografia_anual`.

Ejecución aislada:
    python etl/p2_ine/etl_ine.py
"""


def get_db_connection():
    """
    TODO: Crear y devolver una conexión `psycopg2` a PostgreSQL leyendo las
    variables de entorno de configuración de la base de datos.
    """
    pass


def load_sample_json() -> dict:
    """
    TODO: Abrir y parsear el archivo de muestra `data/raw/ine_series_sample.json`
    que contiene las series históricas 2015-2025 de la Sierra Norte.
    """
    pass


def extract_ine_series() -> list[dict]:
    """
    TODO: Intentar consultar la API Tempus del INE (`https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2881`).
    - Si la API no responde o hay error de red/timeout, activar automáticamente el fallback
      leyendo `load_sample_json()` y retornar la lista bajo la clave `"series"`.
    """
    pass


def run_etl_p2() -> str:
    """
    TODO: Ejecutar el flujo completo ETL P2:
    1. Obtener las series llamando a `extract_ine_series()`.
    2. Conectar a la base de datos con `get_db_connection()`.
    3. Recorrer cada municipio y su lista `"datos"` (años 2015 a 2025):
       - Insertar cada registro anual en `demografia_anual` (`codigo_ine`, `anio`,
         `poblacion_total`, `poblacion_mayor_65`, `poblacion_menor_15`, `tasa_envejecimiento`)
         usando `ON CONFLICT (codigo_ine, anio) DO UPDATE`.
    4. Imprimir el mensaje requerido:
       `[ETL P2-INE] Obteniendo series anuales del INE para Sierra Norte... OK.`
    5. Retornar un resumen con el total de registros anuales insertados.
    """
    pass


if __name__ == "__main__":
    run_etl_p2()
