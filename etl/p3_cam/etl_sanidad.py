#!/usr/bin/env python3
"""
Módulo ETL P3 - Portal de Datos Abiertos de la Comunidad de Madrid (Centros Sanitarios)
Responsable: Desarrollador P3

Objetivo:
Extraer y geocodificar los centros de salud, consultorios locales y puntos de
urgencias 24h (SAR/PAC/Hospital) del norte de la Comunidad de Madrid y cargarlos
en la tabla `centros_sanitarios` con geometría PostGIS EPSG:4326.

Ejecución aislada:
    python etl/p3_cam/etl_sanidad.py
"""


def get_db_connection():
    """
    TODO: Crear y devolver una conexión `psycopg2` a PostgreSQL leyendo las
    variables de entorno de conexión.
    """
    pass


def load_sample_csv() -> list[dict]:
    """
    TODO: Leer el archivo local de respaldo `data/raw/centros_salud_cam_sample.csv`
    con `csv.DictReader` y devolver la lista de centros sanitarios.
    """
    pass


def extract_cam_health_centers() -> list[dict]:
    """
    TODO: Intentar descargar el dataset de centros sanitarios desde el Portal de
    Datos Abiertos de la Comunidad de Madrid.
    - Si falla la conexión o el timeout expira, activar el fallback automático
      llamando a `load_sample_csv()`.
    """
    pass


def run_etl_p3() -> str:
    """
    TODO: Ejecutar el flujo completo ETL P3:
    1. Obtener la lista de centros con `extract_cam_health_centers()`.
    2. Por cada centro sanitario:
       - Convertir `tiene_urgencias` a booleano (`True`/`False`) y `latitud`/`longitud` a `float`.
       - Insertar en `centros_sanitarios` construyendo la geometría espacial con
         `ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)` y manejando duplicados con
         `ON CONFLICT (id_centro) DO UPDATE`.
    3. Imprimir el mensaje requerido:
       `[ETL P3-CAM] Geocodificando centros de salud de la CAM... OK.`
    4. Retornar un resumen con el total de centros geocodificados.
    """
    pass


if __name__ == "__main__":
    run_etl_p3()
