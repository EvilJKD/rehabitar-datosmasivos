# 📋 TODO List — Módulo ETL P3: API Datos Abiertos CAM (`etl/p3_cam/`)

> **Responsable:** Desarrollador P3
> **Fuente Pública Oficial (Sección 3 y 6.2.3):** Portal de Datos Abiertos de la Comunidad de Madrid — *Catálogo de Centros, Servicios y Establecimientos Sanitarios*.
> **Archivo a completar:** `etl_sanidad.py`

## Paso a Paso para Completar `etl_sanidad.py`

- [ ] **Paso 1: Implementar `get_db_connection()`**
  - Conectar a PostgreSQL usando `psycopg2`.

- [ ] **Paso 2: Implementar `fetch_cam_health_centers_api()` (Conexión directa a API de la CAM)**
  - Hacer una petición `requests.get(...)` al recurso JSON/CSV de la API de Datos Abiertos de la Comunidad de Madrid.
  - Filtrar los centros asistenciales (Hospitales, Centros de Salud, Consultorios Locales y Puntos de Atención Continuada / Urgencias).
  - Si las coordenadas del portal de la CAM vienen proyectadas en UTM ETRS89 (`EPSG:25830`), transformarlas a `EPSG:4326` (o usar directamente `ST_Transform(ST_SetSRID(ST_MakePoint(x, y), 25830), 4326)` en PostGIS al insertar).

- [ ] **Paso 3: Implementar `run_etl_p3()`**
  - Insertar los centros devueltos por la API en la tabla `centros_sanitarios` con `ON CONFLICT (id_centro) DO UPDATE`.
  - Imprimir: `[ETL P3-CAM] Geocodificando centros de salud desde API CAM... OK.`
