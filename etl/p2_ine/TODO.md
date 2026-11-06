# 📋 TODO List — Módulo ETL P2: API Pública Tempus del INE (`etl/p2_ine/`)

> **Responsable:** Desarrollador P2
> **Fuente Pública Oficial (Sección 3 y 6.2.1):** API REST JSON Tempus del INE — Tabla 2881 (*Padrón Municipal por municipios*) y Tabla 69744.
> **Archivo a completar:** `etl_ine.py`

## Paso a Paso para Completar `etl_ine.py`

- [ ] **Paso 1: Implementar `get_db_connection()`**
  - Abrir conexión `psycopg2` usando las variables de entorno `POSTGRES_*`.

- [ ] **Paso 2: Implementar `fetch_ine_series_api(codigo_ine=None)` (Conexión directa a API Tempus del INE)**
  - Hacer petición `requests.get("https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2881")` (o usando el endpoint de series del INE filtrando por el municipio `codigo_ine`).
  - Parsear la estructura JSON nativa de Tempus (`[{"COD": ..., "Nombre": ..., "Data": [{"Anyo": 2023, "Valor": 47}, ...]}]`).
  - Extraer para cada año el campo `"Anyo"` (`anio`) y `"Valor"` (`poblacion`).

- [ ] **Paso 3: Implementar `ingest_ine_for_municipio(codigo_ine, conn=None)` (Fase 2 - Bajo Demanda)**
  - Invocar a `fetch_ine_series_api(codigo_ine=codigo_ine)`.
  - Ejecutar `INSERT INTO demografia_anual (codigo_ine, anio, poblacion, ...) VALUES (...) ON CONFLICT (codigo_ine, anio) DO UPDATE` para guardar en PostgreSQL la serie descargada del INE.

- [ ] **Paso 4: Implementar `run_etl_p2(target_codes=None)` (Fase 1 - Carga Inicial Ligera)**
  - Llamar a `ingest_ine_for_municipio` para los municipios semilla (`target_codes`) al iniciar el contenedor `etl_runner`.
