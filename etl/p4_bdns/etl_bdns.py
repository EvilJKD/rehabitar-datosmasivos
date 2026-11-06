#!/usr/bin/env python3
"""
Módulo ETL P4 - Base de Datos Nacional de Subvenciones (BDNS / SNPSAP)
Responsable: Desarrollador P4

Objetivo:
Extraer convocatorias orientadas al Reto Demográfico y Desarrollo Rural y realizar
el matching contra la población actual y envejecimiento de cada municipio (< 20.000 hab),
poblando las tablas `convocatorias` y `convocatoria_municipio`.

Ejecución aislada:
    python etl/p4_bdns/etl_bdns.py
"""


def get_db_connection():
    """
    TODO: Crear y devolver una conexión `psycopg2` a PostgreSQL leyendo las
    variables de entorno de configuración.
    """
    pass


def load_sample_json() -> dict:
    """
    TODO: Leer y parsear el archivo local `data/raw/bdns_convocatorias_sample.json`
    con las convocatorias de ejemplo para municipios rurales.
    """
    pass


def extract_bdns_grants() -> list[dict]:
    """
    TODO: Intentar consultar la API de convocatorias de la BDNS (`BDNS_API_URL`).
    - Si falla o no devuelve JSON directo, activar el fallback automático llamando
      a `load_sample_json()` y devolviendo la lista `"convocatorias"`.
    """
    pass


def run_etl_p4() -> str:
    """
    TODO: Ejecutar el flujo completo ETL P4:
    1. Obtener las convocatorias llamando a `extract_bdns_grants()`.
    2. Insertar/actualizar cada convocatoria en la tabla `convocatorias`.
    3. Consultar en la base de datos los municipios registrados junto con su última
       `poblacion_total` y `tasa_envejecimiento` de `demografia_anual`.
    4. Realizar el matching en `convocatoria_municipio`:
       - Si la población del municipio es `<= poblacion_max_objetivo` de la convocatoria,
         calcular `importe_estimado_hab`, asignar `prioridad_asignacion` (`CRÍTICA`, `ALTA`, `MEDIA`)
         e insertar el vínculo en `convocatoria_municipio`.
    5. Imprimir el mensaje requerido:
       `[ETL P4-BDNS] Asignando convocatorias rurales a municipios < 20.000 hab... OK.`
    6. Retornar un resumen con el número de convocatorias y asignaciones creadas.
    """
    pass


if __name__ == "__main__":
    run_etl_p4()
