#!/usr/bin/env python3
"""
Orquestador de la Carga Inicial Ligera (Fase 1 de la Ingesta Híbrida).
Al levantar Docker (`etl_runner`), realiza una carga semilla ultrarrápida:
  1. P1 (NGBE): Inserta el catálogo geográfico de municipios con `hidratado = FALSE`.
  2. P3 (CAM): Inserta la red de centros sanitarios y urgencias.
  3. P2 (INE) y P4 (BDNS): Carga el catálogo general de convocatorias y pre-hidrata
     ÚNICAMENTE los municipios semilla (`INITIAL_SEED_CODES`, p. ej. 28070 y 28027).
El resto de pueblos se ingesta bajo demanda (Fase 2) cuando el usuario los selecciona
en el Frontend, construyendo la base de datos poco a poco.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from p1_ngbe.etl_ngbe import run_etl_p1
from p2_ine.etl_ine import run_etl_p2
from p3_cam.etl_sanidad import run_etl_p3
from p4_bdns.etl_bdns import run_etl_p4


def get_initial_seed_codes() -> list[str]:
    """
    TODO: Leer la variable de entorno `INITIAL_SEED_CODES` (por defecto `"28070,28027"`,
    es decir, La Hiruela y Buitrago del Lozoya) y devolver la lista de códigos INE
    que se cargarán inicialmente para no alargar el arranque del contenedor.
    """
    pass


def wait_for_db(max_retries: int = 20, wait_seconds: float = 2.0) -> None:
    """
    TODO: Comprobar que PostgreSQL + PostGIS esté listo antes de iniciar la carga semilla.
    """
    pass


def print_banner() -> None:
    """
    TODO: Imprimir un encabezado en consola explicando que se inicia la
    CARGA INICIAL HÍBRIDA (Catálogo Base + Municipios Semilla).
    """
    pass


def main() -> None:
    """
    TODO: Ejecutar la Fase 1 (Carga Inicial Ligera):
    1. Llamar a `print_banner()`, `wait_for_db()` y obtener `seed_codes = get_initial_seed_codes()`.
    2. Ejecutar `run_etl_p1()` -> Carga las coordenadas de todos los pueblos (`hidratado = FALSE`).
    3. Ejecutar `run_etl_p2(target_codes=seed_codes)` -> Descarga e inserta demografía INE solo para `seed_codes`.
    4. Ejecutar `run_etl_p3()` -> Carga la red de centros de salud de la CAM.
    5. Ejecutar `run_etl_p4(target_codes=seed_codes)` -> Carga catálogo BDNS, cruza ayudas para `seed_codes`
       y marca esos municipios semilla con `hidratado = TRUE` en la tabla `municipios`.
    6. Imprimir en consola que el resto de municipios quedan listos para ingesta bajo demanda desde el Frontend.
    """
    pass


if __name__ == "__main__":
    main()
