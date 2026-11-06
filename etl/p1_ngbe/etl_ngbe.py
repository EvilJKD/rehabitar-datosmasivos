#!/usr/bin/env python3
"""
Módulo ETL P1 - Nomenclátor Geográfico Básico de España (NGBE / WFS IGN)
Responsable: Desarrollador P1

Objetivo:
Conectarse directamente a los servicios públicos WFS/REST del Instituto Geográfico
Nacional (IGN) para extraer el directorio oficial de municipios de la Comunidad de
Madrid (`codigo_ine` 28xxx, nombre y coordenadas oficiales) e insertarlos en la
tabla `municipios` con geometría PostGIS `Point(4326)`.

Ejecución aislada:
    python etl/p1_ngbe/etl_ngbe.py
"""


def get_db_connection():
    """
    TODO: Crear y devolver una conexión `psycopg2` a PostgreSQL leyendo las
    variables de entorno (POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER,
    POSTGRES_PASSWORD, POSTGRES_DB).
    """
    pass


def fetch_municipios_ign_api() -> list[dict]:
    """
    TODO: Realizar la petición HTTP en vivo al servicio público WFS INSPIRE / NGBE del IGN
    (por ejemplo `https://www.ign.es/wfs-inspire/unidades-administrativas` o servicio NGBE)
    filtrando las entidades municipales de la Comunidad de Madrid (provincia 28).
    Parsear la respuesta GeoJSON / GML devuelta por el IGN para extraer:
    - `codigo_ine` (5 dígitos, ej. '28078')
    - `nombre` (ej. 'Madarcos')
    - `provincia` ('Madrid')
    - `latitud` y `longitud` (en EPSG:4326)
    """
    pass


def ingest_infraestructura_municipio(codigo_ine: str, conn=None) -> dict:
    """
    TODO (Fase 2 - Hidratación Bajo Demanda):
    Consultar las fuentes públicas de telecomunicaciones / hidrología / red viaria
    para el `codigo_ine` seleccionado e insertar sus indicadores en la tabla
    `metricas_infraestructura` (`distancia_carretera_km`, `distancia_recurso_hidrico_km`,
    `cobertura_fibra_pct`, `cobertura_movil_pct`, `fecha_actualizacion`).
    """
    pass


def run_etl_p1(seed_codes: list[str] | None = None) -> str:
    """
    TODO (Fase 1 - Carga Inicial desde API del IGN):
    1. Llamar a `fetch_municipios_ign_api()` para obtener en vivo los municipios desde el IGN.
    2. Insertar los municipios en la tabla `municipios` construyendo el punto PostGIS con
       `ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)` y `hidratado = FALSE`.
    3. Si hay `seed_codes`, llamar a `ingest_infraestructura_municipio` para esos códigos iniciales.
    4. Imprimir: `[ETL P1-NGBE] Conectando a API IGN... Insertados municipios.`
    """
    pass


if __name__ == "__main__":
    run_etl_p1()
