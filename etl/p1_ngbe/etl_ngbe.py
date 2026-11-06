#!/usr/bin/env python3
"""
Módulo ETL P1 - Nomenclátor Geográfico Básico de España (NGBE - IGN)
Responsable: Desarrollador P1

Objetivo:
Extraer entidades municipales de la Sierra Norte de la Comunidad de Madrid,
transformar coordenadas WGS84 a geometrías PostGIS (EPSG:4326) y poblar las tablas
`municipios` y `metricas_infraestructura`.

Ejecución aislada:
    python etl/p1_ngbe/etl_ngbe.py
"""


def get_db_connection():
    """
    TODO: Crear y devolver una conexión `psycopg2` a PostgreSQL leyendo las
    variables de entorno: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER,
    POSTGRES_PASSWORD y POSTGRES_DB.
    """
    pass


def load_sample_csv() -> list[dict]:
    """
    TODO: Leer el fichero local de respaldo `data/raw/ngbe_madrid_sample.csv`
    utilizando `csv.DictReader` y devolver la lista de diccionarios con los
    municipios de la Sierra Norte.
    """
    pass


def extract_ngbe_data() -> list[dict]:
    """
    TODO: Intentar conectar en vivo al servicio WFS/NGBE del IGN con un timeout corto.
    - Si la petición funciona, registrar en el log el éxito de la conexión.
    - Si falla por red, timeout o código HTTP distinto de 200, imprimir un aviso
      y hacer fallback automático llamando a `load_sample_csv()`.
    """
    pass


def run_etl_p1() -> str:
    """
    TODO: Ejecutar el flujo completo ETL P1 (Extracción -> Transformación -> Carga):
    1. Obtener los registros llamando a `extract_ngbe_data()`.
    2. Abrir conexión con `get_db_connection()`.
    3. Por cada municipio:
       - Insertar/actualizar (`ON CONFLICT (codigo_ine) DO UPDATE`) en la tabla `municipios`,
         construyendo el punto PostGIS con `ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)`.
       - Insertar/actualizar en la tabla `metricas_infraestructura` los indicadores de
         cobertura 5G, fibra, viviendas vacías, precio/m2 y servicios básicos.
    4. Imprimir el mensaje requerido:
       `[ETL P1-NGBE] Conectando a IGN / Leyendo CSV... Insertados municipios.`
    5. Retornar un string resumen con el número de municipios insertados.
    """
    pass


if __name__ == "__main__":
    run_etl_p1()
