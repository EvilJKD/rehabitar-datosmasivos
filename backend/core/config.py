"""
Configuración central del Backend (Variables de entorno y pesos por defecto del motor WLC).
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    TODO: Definir los atributos de configuración de la aplicación leyendo las variables de entorno:
    - PROJECT_NAME: str
    - VERSION: str
    - POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT
    - DATABASE_URL_ASYNC: str (formato `postgresql+asyncpg://user:pass@host:port/db`)
    - EXTERNAL_API_TIMEOUT: float (timeout en segundos para CartoCiudad)
    - CARTOCIUDAD_ROUTE_URL: str
    - Pesos WLC por defecto (deben sumar 1.0):
        * WLC_WEIGHT_DEMO (ej. 0.35)
        * WLC_WEIGHT_HEALTH (ej. 0.30)
        * WLC_WEIGHT_GRANTS (ej. 0.20)
        * WLC_WEIGHT_INFRA (ej. 0.15)
    """
    pass


# TODO: Instanciar `settings = Settings()` para importarlo desde el resto de módulos
settings = None
