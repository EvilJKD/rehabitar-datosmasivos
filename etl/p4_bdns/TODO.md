# 📋 TODO List — Módulo ETL P4: API Pública BDNS / SNPSAP (`etl/p4_bdns/`)

> **Responsable:** Desarrollador P4 (Rama `P4` — **COMPLETADO**)
> **Fuente Pública Oficial (Sección 3 y 6.2.4):** API REST del Sistema Nacional de Publicidad de Subvenciones y Ayudas Públicas (BDNS / SNPSAP).
> **Archivos implementados:** `etl/p4_bdns/etl_bdns.py`, `db/schema.sql` (tablas `convocatorias` y `convocatoria_municipio`), `backend/services/p4_grants_service.py`, `backend/models/domain.py` (`Convocatoria`, `ConvocatoriaMunicipio`), `backend/schemas/domain.py` (`ConvocatoriaMunicipioItemSchema`), `backend/main.py` (`GET /api/convocatorias`), `tests/test_p4_bdns.py`

## Estado de Desarrollo en la Rama `P4`

- [x] **Paso 1: Implementar `get_db_connection()`**
  - Conexión `psycopg2` con `DATABASE_URL_SYNC` o las variables `POSTGRES_*` (mismo criterio que P2).

- [x] **Paso 2: Implementar `fetch_bdns_convocatorias_api()` (Conexión directa a API BDNS)**
  - Búsqueda paginada `GET /bdnstrans/api/convocatorias/busqueda?vpd=GE&regiones=26|27&fechaDesde=...` (26 = ES30 Comunidad de Madrid, 27 = ES300 Madrid) de los últimos `BDNS_MESES_ATRAS` meses.
  - Prefiltro sin coste de red: AUTONOMICA solo de la Comunidad de Madrid, ESTADO, LOCAL solo de nuestros municipios, palabras clave del dominio y descarte de ayudas dirigidas a un ayuntamiento ajeno ("Subvención al Ayuntamiento de X...").
  - Detalle `GET /bdnstrans/api/convocatorias?numConv=XXXX&vpd=GE` con tope `BDNS_MAX_DETALLES`, pausa entre peticiones y un reintento.
  - Normalización: fechas ISO o, si la BDNS no las publica, interpretación de `textInicio`/`textFin` ("HASTA 30 DE SEPTIEMBRE DE 2026"); `abierta` = `abierto` y plazo no vencido; `poblacion_max_objetivo` extraído del texto ("menos de 20.000 HB"); `finalidad` (categoría).
  - Copia del JSON crudo en `etl/data/raw/bdns/convocatorias_madrid.json` (se reutiliza durante `BDNS_CACHE_HORAS` y sirve de respaldo si la API cae).

- [x] **Paso 3: Implementar `ingest_bdns_for_municipio(codigo_ine, conn=None)` (Fase 2 - Bajo Demanda)**
  - Reglas por prioridad: `organo_local` (ayuntamiento convocante o destinatario) > `umbral_poblacion` (padrón de `demografia_anual` < umbral) > `region_completa` (Comunidad de Madrid o Estado sin restricciones).
  - Upsert en `convocatoria_municipio` con `ON CONFLICT (codigo_ine, codigo_bdns) DO UPDATE` y borrado de asignaciones que ya no aplican.
  - `municipios.hidratado = TRUE` y `fecha_hidratacion = CURRENT_TIMESTAMP`.

- [x] **Paso 4: Implementar `run_etl_p4(target_codes=None)` (Fase 1 - Carga Inicial)**
  - Descarga → upsert en `convocatorias` → asignación de los municipios semilla (o de todos si no se indican).
  - CLI: `python etl/p4_bdns/etl_bdns.py [codigos...] [--force-refresh] [--dry-run --nombres "La Hiruela,Madarcos"]`.

- [x] **Paso 5: Servicio, endpoint y pruebas**
  - `get_convocatorias` (Consulta 4), `get_grants_summary_all`, `get_num_ayudas_abiertas`, `hydrate_grants_on_demand`.
  - 40 pruebas (unidad, HTTP simulado, ORM/Pydantic, endpoint, integración PostGIS y 1 en vivo opcional):
    `docker compose -f tests/docker-compose.p4-test.yml run --rm tests`

## Dependencias con otros módulos
- **P1** (`municipios`): necesaria para asignar (FK). Sin ella, el ETL guarda el catálogo y avisa.
- **P2** (`demografia_anual`): necesaria para la regla `umbral_poblacion`. Sin padrón, esa regla no se aplica y se avisa.
- **Mediador** (`backend/main.py::ensure_municipio_hydrated`): debe llamar a `hydrate_grants_on_demand` en el Paso D.
