# 📋 TODO List — Módulo ETL P1: API Pública IGN / NGBE (`etl/p1_ngbe/`)

> **Responsable:** Desarrollador P1
> **Fuente Pública Oficial (Sección 3 y 6.2.2):** Servicio WFS INSPIRE / NGBE del Instituto Geográfico Nacional (IGN).
> **Archivo a completar:** `etl_ngbe.py`

## Paso a Paso para Completar `etl_ngbe.py`

- [ ] **Paso 1: Implementar `get_db_connection()`**
  - Conectar a PostgreSQL con `psycopg2` leyendo las variables de entorno `POSTGRES_*`.

- [ ] **Paso 2: Implementar `fetch_municipios_ign_api()` (Conexión directa a API del IGN)**
  - Realizar una petición `requests.get(...)` al servicio público WFS del IGN (`https://www.ign.es/wfs-inspire/unidades-administrativas` o WFS NGBE) solicitando formato `application/json` (GeoJSON) o GML para los municipios de la Comunidad de Madrid (`28xxx`).
  - Parsear cada *feature* para extraer `codigo_ine`, `nombre`, `provincia` (`"Madrid"`), `latitud` y `longitud`.

- [ ] **Paso 3: Implementar `ingest_infraestructura_municipio(codigo_ine, conn=None)` (Fase 2 - Bajo Demanda)**
  - Obtener los indicadores físicos y digitales del municipio (`distancia_carretera_km`, `distancia_recurso_hidrico_km`, `cobertura_fibra_pct`, `cobertura_movil_pct`) desde las fuentes públicas abiertas e insertarlos en la tabla `metricas_infraestructura` (`ON CONFLICT (codigo_ine) DO UPDATE`).

- [ ] **Paso 4: Implementar `run_etl_p1(seed_codes=None)` (Fase 1 - Carga Inicial)**
  - Llamar a `fetch_municipios_ign_api()`.
  - Insertar todos los municipios devueltos por la API en la tabla `municipios` con su geometría PostGIS `ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)` y `hidratado = FALSE`.
  - Si `seed_codes` está definido, hidratar inicialmente solo las métricas de infraestructura de esos códigos semilla.
