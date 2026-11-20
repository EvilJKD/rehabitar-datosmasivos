#!/usr/bin/env python3
"""
Orquestador de la Carga Inicial Ligera (Fase 1 de la Ingesta Híbrida).
Al levantar Docker (`etl_runner`), realiza una carga semilla ultrarrápida:
  1. P1 (NGBE): Inserta el catálogo geográfico de municipios con `hidratado = FALSE` y métricas semilla.
  2. P2 (INE): Carga series demográficas 2015-2025 únicamente para `INITIAL_SEED_CODES`.
  3. P3 (CAM): Inserta la red base de centros sanitarios con urgencias y consultorios semilla.
  4. P4 (BDNS): Carga el catálogo general de convocatorias y pre-hidrata únicamente `INITIAL_SEED_CODES`.
El resto de pueblos se ingesta bajo demanda (Fase 2) cuando el usuario los selecciona
en el Frontend, construyendo la base de datos poco a poco.
"""

import os
import sys
import time
from contextlib import closing

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from p1_ngbe.etl_ngbe import get_db_connection, run_etl_p1
from p2_ine.etl_ine import run_etl_p2
from p3_cam.etl_sanidad import run_etl_p3
from p4_bdns.etl_bdns import run_etl_p4

DEFAULT_INITIAL_SEED_CODES = "28078,28069,28027"
LEGACY_CODE_ALIASES = {
    # En la versión preliminar del repo se anotó 28070 para La Hiruela; su código INE oficial es 28069.
    "28070": "28069",
}


def get_initial_seed_codes() -> list[str]:
    """
    Lee `INITIAL_SEED_CODES` (por defecto `"28078,28069,28027"`: Madarcos, La Hiruela y
    Buitrago del Lozoya), traduce `"28070"` -> `"28069"` si aparece en configuraciones heredadas
    y elimina duplicados preservando el orden.
    """
    raw = os.getenv("INITIAL_SEED_CODES", DEFAULT_INITIAL_SEED_CODES)
    seen: dict[str, None] = {}
    for token in raw.split(","):
        code = token.strip()
        if not code:
            continue
        code = LEGACY_CODE_ALIASES.get(code, code)
        seen.setdefault(code, None)
    return list(seen.keys())


def wait_for_db(max_retries: int = 20, wait_seconds: float = 2.0) -> None:
    """Comprueba que PostgreSQL + PostGIS esté listo antes de iniciar la carga semilla."""
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            with closing(get_db_connection()) as conn, conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
            print(f"[ETL RUNNER] Conexión a PostgreSQL + PostGIS verificada (intento {attempt}).", flush=True)
            return
        except Exception as exc:
            last_error = exc
            print(
                f"[ETL RUNNER] Esperando a PostgreSQL ({attempt}/{max_retries}): {exc}",
                flush=True,
            )
            if attempt < max_retries:
                time.sleep(wait_seconds)
    raise RuntimeError(f"PostgreSQL no estuvo disponible tras {max_retries} intentos: {last_error}")


def print_banner() -> None:
    """Imprime un encabezado en consola explicando la carga inicial híbrida."""
    print("=" * 78, flush=True)
    print("  RE-HABITAR PoC · CARGA INICIAL HIBRIDA (Catalogo Base + Municipios Semilla)", flush=True)
    print("  Flujo: P1 (NGBE) -> P2 (INE 2881) -> P3 (Sanidad CAM) -> P4 (BDNS)", flush=True)
    print("=" * 78, flush=True)


def main() -> None:
    """Ejecuta la Fase 1 (Carga Inicial Ligera) en orden P1 -> P2 -> P3 -> P4."""
    print_banner()
    wait_for_db()
    seed_codes = get_initial_seed_codes()
    print(f"[ETL RUNNER] Códigos semilla iniciales: {seed_codes}", flush=True)

    res_p1 = run_etl_p1(seed_codes=seed_codes)
    print(f"[ETL RUNNER] {res_p1}", flush=True)

    res_p2 = run_etl_p2(target_codes=seed_codes)
    print(f"[ETL RUNNER] {res_p2}", flush=True)

    res_p3 = run_etl_p3()
    print(f"[ETL RUNNER] {res_p3}", flush=True)

    res_p4 = run_etl_p4(target_codes=seed_codes)
    print(f"[ETL RUNNER] {res_p4}", flush=True)

    print(
        "[ETL RUNNER] Carga inicial completada. El resto de municipios quedan listos "
        "para ingesta bajo demanda desde la API / Frontend.",
        flush=True,
    )


if __name__ == "__main__":
    main()
