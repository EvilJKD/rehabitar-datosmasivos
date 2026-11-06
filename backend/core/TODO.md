# 📋 TODO List — Configuración y Conexión a Base de Datos (`backend/core/`)

> **Archivos a completar:** `config.py` y `database.py`

## 1. Paso a Paso para `backend/core/config.py`

- [ ] **Paso 1.1: Definir los atributos de la clase `Settings(BaseSettings)`**
  - `PROJECT_NAME: str = "Re-Habitar PoC"`
  - `VERSION: str = "1.0.0"`
  - Variables de conexión PostgreSQL leídas con `os.getenv()`:
    - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`
  - `DATABASE_URL_ASYNC: str` con el formato `postgresql+asyncpg://usuario:password@host:puerto/base_datos`.
  - `EXTERNAL_API_TIMEOUT: float = 3.5`
  - `CARTOCIUDAD_ROUTE_URL: str = "https://www.cartociudad.es/services/api/route"`
  - Pesos por defecto del motor WLC:
    - `WLC_WEIGHT_DEMO: float = 0.35`
    - `WLC_WEIGHT_HEALTH: float = 0.30`
    - `WLC_WEIGHT_GRANTS: float = 0.20`
    - `WLC_WEIGHT_INFRA: float = 0.15`

- [ ] **Paso 1.2: Instanciar `settings`**
  - Al final del archivo, asignar `settings = Settings()`.

---

## 2. Paso a Paso para `backend/core/database.py`

- [ ] **Paso 2.1: Crear el motor asíncrono de SQLAlchemy**
  - Importar `create_async_engine` y `async_sessionmaker` de `sqlalchemy.ext.asyncio`.
  - Inicializar `engine = create_async_engine(settings.DATABASE_URL_ASYNC, pool_pre_ping=True)`.

- [ ] **Paso 2.2: Crear la factoría de sesiones asíncronas**
  - Inicializar `AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)`.

- [ ] **Paso 2.3: Implementar el generador `get_db()`**
  - Usar `async with AsyncSessionLocal() as session:` y hacer `yield session` para que los endpoints de FastAPI puedan inyectar la sesión con `Depends(get_db)`.
