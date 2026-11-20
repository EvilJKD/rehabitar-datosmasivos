# Base de datos (`db/`)

Esta carpeta contiene la definición e inicialización del almacén espacial en **PostgreSQL 15 + PostGIS 3.4** (compatible con Citus).

## Archivos principales

- `schema.sql`: Script DDL que habilita la extensión `postgis` y crea las seis tablas del proyecto junto con sus restricciones e índices espaciales GiST y B-Tree:
  - `municipios`: Catálogo maestro de municipios con geometría `Point` en WGS84 (EPSG:4326) y estado de hidratación.
  - `demografia_anual`: Serie histórica de población municipal (clave primaria compuesta por `codigo_ine` y `anio`).
  - `metricas_infraestructura`: Distancias físicas y cobertura de fibra y red móvil por municipio.
  - `centros_sanitarios`: Directorio georreferenciado de centros sanitarios y puntos de urgencias.
  - `convocatorias`: Catálogo de ayudas y subvenciones públicas procedentes de la BDNS.
  - `convocatoria_municipio`: Relación de convocatorias asignadas a cada municipio y la regla aplicada.
- `Dockerfile`: Construye la imagen `postgis/postgis:15-3.4-alpine` copiando `schema.sql` en `/docker-entrypoint-initdb.d/01_schema.sql` para inicializar la base de datos automáticamente al crear el volumen.
