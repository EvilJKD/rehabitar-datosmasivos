# 📋 TODO List — Módulo ETL P4: API Pública BDNS / SNPSAP (`etl/p4_bdns/`)

> **Responsable:** Desarrollador P4
> **Fuente Pública Oficial (Sección 3 y 6.2.4):** API REST / OpenAPI del Sistema Nacional de Publicidad de Subvenciones y Ayudas Públicas (BDNS / SNPSAP).
> **Archivo a completar:** `etl_bdns.py`

## Paso a Paso para Completar `etl_bdns.py`

- [ ] **Paso 1: Implementar `get_db_connection()`**
  - Abrir conexión `psycopg2` a PostgreSQL.

- [ ] **Paso 2: Implementar `fetch_bdns_convocatorias_api()` (Conexión directa a API BDNS)**
  - Realizar petición HTTP GET a los endpoints REST públicos de la BDNS (`https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda` y detalle de convocatoria).
  - Extraer `codigo_bdns`, `descripcion`, `organo_nivel1`, `organo_nivel2`, `organo_nivel3`, `fecha_recepcion`, `inicio_solicitud`, `fin_solicitud`, `abierta`, `presupuesto_total`, `tipo_beneficiario`, `poblacion_max_objetivo` y `url_bases`.

- [ ] **Paso 3: Implementar `ingest_bdns_for_municipio(codigo_ine, conn=None)` (Fase 2 - Bajo Demanda)**
  - Cruzar las convocatorias con los datos del municipio `codigo_ine` aplicando las reglas de inferencia (`organo_local`, `umbral_poblacion`, `region_completa`).
  - Insertar los registros en `convocatoria_municipio` con `ON CONFLICT (codigo_ine, codigo_bdns) DO UPDATE`.
  - Actualizar `municipios.hidratado = TRUE` y `municipios.fecha_hidratacion = CURRENT_TIMESTAMP`.

- [ ] **Paso 4: Implementar `run_etl_p4(target_codes=None)` (Fase 1 - Carga Inicial)**
  - Descargar las convocatorias de la API de la BDNS, guardarlas en `convocatorias` y cruzar inicialmente los municipios semilla (`target_codes`).
