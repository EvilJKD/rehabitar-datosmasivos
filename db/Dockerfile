# =============================================================================
# Dockerfile para Base de Datos PostgreSQL 15 + PostGIS 3.4 (LISTO PARA USAR)
# =============================================================================
FROM postgis/postgis:15-3.4-alpine

LABEL maintainer="Equipo Re-Habitar - Master en Informatica"
LABEL description="PostgreSQL 15 + PostGIS 3.4 con inicializacion automatica de schema.sql"

# Copia el script DDL para que PostgreSQL lo ejecute automaticamente al crear el volumen
COPY schema.sql /docker-entrypoint-initdb.d/01_schema.sql

EXPOSE 5432
