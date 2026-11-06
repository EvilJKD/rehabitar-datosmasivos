#!/usr/bin/env python3
"""
Módulo ETL P3 - API de Datos Abiertos de la Comunidad de Madrid (Centros Sanitarios)
Responsable: Desarrollador P3

Objetivo:
Conectarse directamente al Portal de Datos Abiertos de la Comunidad de Madrid
(API REST CKAN / descarga directa JSON o CSV del catálogo de Centros, Servicios
y Establecimientos Sanitarios) e insertar los registros geocodificados en la
tabla `centros_sanitarios` con geometría PostGIS `Point(4326)`.

Ejecución aislada:
    python etl/p3_cam/etl_sanidad.py
"""


def get_db_connection():
    """
    TODO: Crear y devolver una conexión `psycopg2` a PostgreSQL.
    """
    pass


def fetch_cam_health_centers_api() -> list[dict]:
    """
    TODO: Realizar petición HTTP GET directamente al endpoint del Portal de Datos
    Abiertos de la Comunidad de Madrid (`CAM_SANIDAD_CSV_URL` / API JSON CKAN).
    Parsear los registros devueltos por la API pública de la CAM para extraer:
    - `id_centro`
    - `nombre`
    - `tipo` (ej. 'Consultorio Local', 'Centro de Salud', 'Hospital')
    - `tiene_urgencias` (booleano según si dispone de urgencias / atención continuada SAR/SUAP)
    - `municipio_nombre`, `direccion`, `horario`, `telefono`
    - `latitud` y `longitud` (transformando desde UTM ETRS89 EPSG:25830 a WGS84 EPSG:4326 si el recurso viene en UTM)
    """
    pass


def run_etl_p3() -> str:
    """
    TODO: Ejecutar la ingesta desde la API de Datos Abiertos de la CAM:
    1. Obtener la lista de centros llamando a `fetch_cam_health_centers_api()`.
    2. Insertar cada centro en `centros_sanitarios` creando la geometría espacial con
       `ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)` y `ON CONFLICT (id_centro) DO UPDATE`.
    3. Imprimir: `[ETL P3-CAM] Geocodificando centros de salud desde API CAM... OK.`
    """
    pass


if __name__ == "__main__":
    run_etl_p3()
