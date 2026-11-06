#!/usr/bin/env python3
"""
Orquestador principal de pipelines ETL del proyecto Re-Habitar.
Debe ejecutar secuencialmente P1 (NGBE/IGN) -> P2 (INE) -> P3 (CAM Sanidad) -> P4 (BDNS)
imprimiendo trazas detalladas en consola.
"""

import os
import sys

# Asegurar que el directorio actual esté en sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from p1_ngbe.etl_ngbe import run_etl_p1
from p2_ine.etl_ine import run_etl_p2
from p3_cam.etl_sanidad import run_etl_p3
from p4_bdns.etl_bdns import run_etl_p4


def wait_for_db(max_retries: int = 20, wait_seconds: float = 2.0) -> None:
    """
    TODO: Verificar que PostgreSQL + PostGIS acepte conexiones antes de lanzar los ETL.
    Pasos:
    1. Leer variables de entorno POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER,
       POSTGRES_PASSWORD y POSTGRES_DB.
    2. Intentar conectar con `psycopg2.connect(...)` en un bucle de hasta `max_retries`.
    3. Si conecta con éxito, cerrar la conexión y retornar.
    4. Si falla tras todos los intentos, terminar el proceso con `sys.exit(1)`.
    """
    pass


def print_banner() -> None:
    """
    TODO: Imprimir por consola un encabezado visual indicando el inicio del
    contenedor `etl_runner` del proyecto Re-Habitar.
    """
    pass


def main() -> None:
    """
    TODO: Orquestar la ejecución en orden estricto de los 4 módulos ETL:
    1. Llamar a `print_banner()` y `wait_for_db()`.
    2. Ejecutar en orden:
       - `run_etl_p1()` (Municipios NGBE + geometría PostGIS)
       - `run_etl_p2()` (Series demográficas INE 2015-2025)
       - `run_etl_p3()` (Centros sanitarios CAM + geometría PostGIS)
       - `run_etl_p4()` (Convocatorias BDNS y cruce con municipios < 20.000 hab)
    3. Medir tiempos de ejecución e imprimir un resumen final en consola.
    """
    pass


if __name__ == "__main__":
    main()
