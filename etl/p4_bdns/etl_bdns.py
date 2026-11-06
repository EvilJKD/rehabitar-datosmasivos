#!/usr/bin/env python3
"""
Módulo ETL P4 - API OpenAPI de la Base de Datos Nacional de Subvenciones (BDNS / SNPSAP)
Responsable: Desarrollador P4

Objetivo:
Conectarse directamente a la API REST OpenAPI del portal SNPSAP / BDNS
(`https://www.infosubvenciones.es/bdnstrans/api/...`) para extraer las convocatorias
de subvenciones con alcance en la Comunidad de Madrid, almacenarlas en `convocatorias`
y aplicar las reglas de inferencia territorial en `convocatoria_municipio`.

Ejecución aislada:
    python etl/p4_bdns/etl_bdns.py
"""


def get_db_connection():
    """
    TODO: Crear y devolver una conexión `psycopg2` a PostgreSQL.
    """
    pass


def fetch_bdns_convocatorias_api() -> list[dict]:
    """
    TODO: Realizar petición HTTP GET directamente a la API OpenAPI de la BDNS / SNPSAP
    filtrando las convocatorias con alcance en la Comunidad de Madrid.
    Extraer para cada convocatoria los campos de la Sección 7.1.5:
    - `codigo_bdns`
    - `descripcion`
    - `organo_nivel1`, `organo_nivel2`, `organo_nivel3`
    - `fecha_recepcion`, `inicio_solicitud`, `fin_solicitud`, `abierta`
    - `presupuesto_total`, `tipo_beneficiario`, `poblacion_max_objetivo`, `url_bases`
    """
    pass


def ingest_bdns_for_municipio(codigo_ine: str, conn=None) -> int:
    """
    TODO (Fase 2 - Matching Bajo Demanda para un municipio):
    1. Consultar en PostgreSQL la población actual de `codigo_ine` (en `demografia_anual`)
       y las convocatorias de la tabla `convocatorias`.
    2. Determinar qué convocatorias aplican al municipio y con qué `regla_asignacion`
       (`'organo_local' | 'umbral_poblacion' | 'region_completa'`).
    3. Insertar las asignaciones en `convocatoria_municipio (codigo_ine, codigo_bdns, regla_asignacion)`
       usando `ON CONFLICT (codigo_ine, codigo_bdns) DO UPDATE`.
    4. Marcar el municipio como hidratado:
       `UPDATE municipios SET hidratado = TRUE, fecha_hidratacion = CURRENT_TIMESTAMP WHERE codigo_ine = %s;`
    """
    pass


def run_etl_p4(target_codes: list[str] | None = None) -> str:
    """
    TODO (Fase 1 - Carga Inicial desde API BDNS):
    1. Llamar a `fetch_bdns_convocatorias_api()` e insertar las convocatorias en la tabla `convocatorias`.
    2. Ejecutar `ingest_bdns_for_municipio` para los municipios semilla en `target_codes`.
    3. Imprimir: `[ETL P4-BDNS] Asignando convocatorias rurales desde API BDNS... OK.`
    """
    pass


if __name__ == "__main__":
    run_etl_p4()
