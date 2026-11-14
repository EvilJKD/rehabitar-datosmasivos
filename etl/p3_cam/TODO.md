# 📋 TODO List — Módulo ETL P3: API Datos Abiertos CAM (`etl/p3_cam/`)

> **Responsable:** Desarrollador P3 (Rama `P3` — **COMPLETADO**)
> **Fuente Pública Oficial (Sección 3 y 6.2.3):** Portal de Datos Abiertos de la Comunidad de Madrid — *Catálogo de Centros, Servicios y Establecimientos Sanitarios*.
> **Archivos implementados:** `etl/p3_cam/etl_sanidad.py`, `db/schema.sql` (tabla `centros_sanitarios`), `backend/services/p3_health_service.py`, `backend/models/domain.py` (`CentroSanitario`), `backend/schemas/domain.py` (`CentroSanitarioSchema`, `RutaSanitariaSchema`), `tests/test_p3_sanidad.py`

## Estado de Desarrollo en la Rama `P3`

- [x] **Paso 1: Implementar `get_db_connection()`**
  - Conecta a PostgreSQL/PostGIS usando `psycopg2` mediante variables de entorno (`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`).

- [x] **Paso 2: Implementar `fetch_cam_health_centers_api()` (Conexión directa a API de la CAM)**
  - Descubre dinámicamente los recursos JSON y CSV desde la API CKAN de Datos Abiertos de la Comunidad de Madrid (`package_show?id=centros_servicios_establecimientos_sanitarios`) y descarga los 46.000+ registros oficiales filtrando y consolidando los **548 centros sanitarios asistenciales únicos** (Hospitales, Centros de Salud, Consultorios de Atención Primaria y Puntos de Urgencias/SAR).
  - Reproyecta las coordenadas `localizacion_coordenada_x` y `localizacion_coordenada_y` desde UTM Huso 30N ETRS89 (`EPSG:25830`) a WGS84 (`EPSG:4326`) mediante `utm30n_etrs89_to_wgs84()`.

- [x] **Paso 3: Implementar `upsert_health_centers_to_db()` y `run_etl_p3()`**
  - Inserta los centros en la tabla `centros_sanitarios` con `ON CONFLICT (id_centro) DO UPDATE` y genera la geometría espacial `ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)`.
  - Incluye `ingest_centros_for_municipio()` para hidratación selectiva bajo demanda.

- [x] **Paso 4: Implementar Servicio Espacial KNN PostGIS y Pruebas Unitarias**
  - Consultas espaciales `CROSS JOIN LATERAL` con operador KNN `<->` y cálculo `ST_DistanceSphere` implementadas en `backend/services/p3_health_service.py`.
  - Suite de 10 pruebas unitarias y de integración en vivo (`tests/test_p3_sanidad.py`) ejecutada con éxito.

