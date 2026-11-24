# Pipelines ETL (`etl/`)

Esta carpeta agrupa los procesos de extracción, transformación y carga en Python que nutren PostgreSQL + PostGIS desde fuentes oficiales mediante APIs y descargas HTTP.

Durante el arranque con Docker, el contenedor `etl_runner` ejecuta la carga semilla inicial (`P1 -> P2 -> P3 -> P4`) sobre los códigos configurados en `INITIAL_SEED_CODES`; posteriormente, el backend reutiliza estos mismos módulos para hidratar nuevos municipios bajo demanda.

## Archivos y submódulos principales

- `run_all.py`: Orquestador de la fase inicial. Espera a que PostgreSQL/PostGIS esté operativo, resuelve `INITIAL_SEED_CODES` (por defecto `28078,28069,28027`) y ejecuta en secuencia los cuatro pipelines.
- `p1_ngbe/`: `etl_ngbe.py` y `sources.py` obtienen el catálogo municipal del IGN, la cobertura de banda ancha (SETELECO) y referencias geográficas de IDEE para poblar `municipios` y `metricas_infraestructura`.
- `p2_ine/`: `etl_ine.py` descarga las series anuales de población desde la API Tempus del INE (tabla 2881) y carga `demografia_anual`.
- `p3_cam/`: `etl_sanidad.py` consulta los centros sanitarios en el Portal de Datos Abiertos de la Comunidad de Madrid, transforma coordenadas ETRS89 UTM 30N a WGS84 y actualiza `centros_sanitarios`.
- `p4_bdns/`: `etl_bdns.py` consulta las convocatorias de la BDNS/SNPSAP, carga `convocatorias` y calcula las asignaciones en `convocatoria_municipio`.
- `Dockerfile` y `requirements.txt`: Definen la imagen `python:3.11-slim` y las dependencias de red y PostgreSQL del servicio `etl_runner`.
