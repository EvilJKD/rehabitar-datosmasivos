# Backend API (`backend/`)

Esta carpeta contiene el servidor **FastAPI** que expone la API REST del proyecto, coordina la hidratación bajo demanda en PostgreSQL/PostGIS, calcula rutas en tiempo real con CartoCiudad y ejecuta en memoria el motor de viabilidad WLC. El frontend Angular se sirve en un contenedor separado.

## Archivos y submódulos principales

- `main.py`: Aplicación principal FastAPI (`app`) y mediador entre PostgreSQL, los módulos ETL bajo demanda, CartoCiudad y el motor WLC. Expone los endpoints:
  - `GET /api/health`
  - `GET /api/municipios`
  - `GET /api/municipios/{codigo_ine}`
  - `POST /api/municipios/{codigo_ine}/ingest`
  - `GET /api/municipios/{codigo_ine}/demografia`
  - `GET /api/convocatorias`
  - `GET /api/centros-sanitarios`
- `core/`: Configuración leída de variables de entorno y gestión de sesiones asíncronas con SQLAlchemy.
- `models/`: Modelos ORM de SQLAlchemy alineados con `db/schema.sql`.
- `schemas/`: Esquemas Pydantic de validación y serialización para los endpoints.
- `services/`: Servicios de negocio asíncronos (`p1_geo_service.py`, `p2_demo_service.py`, `p3_health_service.py`, `p4_grants_service.py`), cliente de rutas (`p5_cartociudad.py`), motor de puntuación (`p5_wlc_engine.py`) y capa de compatibilidad (`_sa_compat.py`).
- `Dockerfile` y `requirements.txt`: Imagen `python:3.11-slim` y dependencias del servicio `app`.
