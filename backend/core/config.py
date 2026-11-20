"""
Configuración central del Backend (Variables de entorno y pesos por defecto del motor WLC).
"""

import os

try:
    from pydantic import ConfigDict
    from pydantic_settings import BaseSettings

    _HAS_PYDANTIC_SETTINGS = True
except ImportError:  # pragma: no cover - permite ejecutar pruebas unitarias en host sin pydantic-settings
    _HAS_PYDANTIC_SETTINGS = False

    def ConfigDict(**kwargs):  # type: ignore
        """Devuelve la configuración como diccionario cuando falta pydantic."""
        return kwargs

    class BaseSettings:  # type: ignore
        """Clase base mínima para leer atributos de configuración sin pydantic-settings."""

        def __init__(self, **kwargs):
            """Asigna los atributos de clase sobrescribiéndolos con `kwargs` si llegan."""
            for attr_name, attr_val in type(self).__dict__.items():
                if not attr_name.startswith("_") and attr_name != "model_config" and not callable(attr_val):
                    setattr(self, attr_name, kwargs.get(attr_name, attr_val))


class Settings(BaseSettings):
    """Configuración del backend leída desde variables de entorno."""

    if _HAS_PYDANTIC_SETTINGS:
        model_config = ConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Re-Habitar PoC")
    VERSION: str = os.getenv("VERSION", "1.0.0")

    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "rehabitar")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "rehabitar_pwd")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "rehabitar_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    DATABASE_URL_ASYNC: str = os.getenv(
        "DATABASE_URL_ASYNC",
        (
            f"postgresql+asyncpg://{os.getenv('POSTGRES_USER', 'rehabitar')}:"
            f"{os.getenv('POSTGRES_PASSWORD', 'rehabitar_pwd')}@"
            f"{os.getenv('POSTGRES_HOST', 'db')}:{os.getenv('POSTGRES_PORT', '5432')}/"
            f"{os.getenv('POSTGRES_DB', 'rehabitar_db')}"
        ),
    )
    DATABASE_URL_SYNC: str = os.getenv(
        "DATABASE_URL_SYNC",
        (
            f"postgresql://{os.getenv('POSTGRES_USER', 'rehabitar')}:"
            f"{os.getenv('POSTGRES_PASSWORD', 'rehabitar_pwd')}@"
            f"{os.getenv('POSTGRES_HOST', 'db')}:{os.getenv('POSTGRES_PORT', '5432')}/"
            f"{os.getenv('POSTGRES_DB', 'rehabitar_db')}"
        ),
    )

    EXTERNAL_API_TIMEOUT: float = float(os.getenv("EXTERNAL_API_TIMEOUT", "4.0"))
    CARTOCIUDAD_ROUTE_URL: str = os.getenv(
        "CARTOCIUDAD_ROUTE_URL", "https://www.cartociudad.es/services/api/route"
    )

    # Pesos por defecto del motor WLC (suman 1.0)
    WLC_WEIGHT_DEMO: float = float(os.getenv("WLC_WEIGHT_DEMO", "0.35"))
    WLC_WEIGHT_HEALTH: float = float(os.getenv("WLC_WEIGHT_HEALTH", "0.30"))
    WLC_WEIGHT_GRANTS: float = float(os.getenv("WLC_WEIGHT_GRANTS", "0.20"))
    WLC_WEIGHT_INFRA: float = float(os.getenv("WLC_WEIGHT_INFRA", "0.15"))


settings = Settings()
