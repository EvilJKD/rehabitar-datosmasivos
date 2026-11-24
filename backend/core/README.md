# Configuración y Base de Datos (`backend/core/`)

Módulo transversal encargado de cargar la configuración del entorno y proporcionar sesiones asíncronas de SQLAlchemy hacia PostgreSQL + PostGIS.

## Archivos principales

- `__init__.py`: Inicializa el paquete `core`.
- `config.py`: Define `Settings` (e instancia global `settings`) con los parámetros del proyecto, credenciales y URLs de PostgreSQL (`DATABASE_URL_ASYNC`, `DATABASE_URL_SYNC`), configuración de APIs externas (`EXTERNAL_API_TIMEOUT`, `CARTOCIUDAD_ROUTE_URL`) y pesos por defecto del motor WLC. Incluye un respaldo ligero si `pydantic-settings` no está instalado.
- `database.py`: Configura el motor asíncrono (`engine`), la factoría de sesiones (`AsyncSessionLocal`), la clase declarativa `Base` y la dependencia `get_db()` utilizada por los endpoints de FastAPI.
