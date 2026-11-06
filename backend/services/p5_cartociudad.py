"""
Servicio P5.1 - Integración Virtual en Tiempo Real con API CartoCiudad (IGN)
Responsable: Desarrollador P5

REGLA ARQUITECTÓNICA DE LA PROPUESTA (Sección 6.3, 7.3 y Diagrama Sección 9):
"El tiempo de trayecto hacia el punto sanitario NO se almacena en ninguna tabla para
evitar obsolescencia. Al consultar un municipio, el backend identifica el punto
asistencial más cercano en PostGIS y realiza la llamada REST en tiempo real a la API
de CartoCiudad, fusionando estos valores en memoria con el motor WLC."
"""

from typing import Dict, List


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    TODO: Calcular distancia ortodrómica Haversine en kilómetros entre dos coordenadas WGS84.
    """
    pass


def build_curved_mountain_polyline(
    lat1: float, lon1: float, lat2: float, lon2: float, steps: int = 12
) -> List[List[float]]:
    """
    TODO: Generar polilínea interpolada `[[lat, lon], ...]` de respaldo para Leaflet
    cuando la API externa de CartoCiudad no esté accesible.
    """
    pass


def compute_fallback_route(
    lat_orig: float, lon_orig: float, lat_dest: float, lon_dest: float
) -> Dict:
    """
    TODO: Cálculo de respaldo en memoria (Haversine * factor de sinuosidad 1.32x y
    velocidad media rural de 45 km/h) para garantizar que la Consulta 2 y el motor WLC
    nunca fallen durante la demostración en vivo si CartoCiudad sufre caídas o timeouts.
    """
    pass


async def calculate_route_cartociudad(
    lat_orig: float, lon_orig: float, lat_dest: float, lon_dest: float
) -> Dict:
    """
    TODO (Integración Virtual en Tiempo Real - Consulta 2 y Motor WLC):
    1. Realizar petición HTTP GET asíncrona (`httpx.AsyncClient`) en tiempo real a
       `https://www.cartociudad.es/services/api/route` con `orig` y `dest`.
    2. Extraer `distancia_carretera_km`, `tiempo_estimado_min` y `geometria_ruta` (`[[lat, lon], ...]`).
    3. Si falla o expira el timeout, retornar `compute_fallback_route(...)`.
    4. IMPORTANTE (Sección 7.3): Retornar el diccionario en memoria al Mediador FastAPI
       SIN guardarlo en ninguna tabla de PostgreSQL.
    """
    pass
