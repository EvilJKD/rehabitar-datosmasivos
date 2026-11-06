"""
Servicio P5.1 - Wrapper de Enrutamiento Vial CartoCiudad (IGN) en Tiempo Real
Responsable: Desarrollador P5
"""

from typing import Dict, List


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    TODO: Calcular y devolver la distancia ortodrómica (fórmula de Haversine) en kilómetros
    entre dos pares de coordenadas WGS84 `(lat1, lon1)` y `(lat2, lon2)`.
    """
    pass


def build_curved_mountain_polyline(
    lat1: float, lon1: float, lat2: float, lon2: float, steps: int = 12
) -> List[List[float]]:
    """
    TODO: Generar una lista de coordenadas `[[lat, lon], ...]` interpoladas entre el origen
    y el destino para dibujar la polilínea en el mapa Leaflet cuando se utilice el modo de
    respaldo (fallback) sin conexión a CartoCiudad.
    """
    pass


def compute_fallback_route(
    lat_orig: float, lon_orig: float, lat_dest: float, lon_dest: float
) -> Dict:
    """
    TODO: Implementar el cálculo de respaldo garantizado cuando la API de CartoCiudad
    falle o supere el timeout:
    1. Obtener `distancia_euclidea_km` con `haversine_km(...)`.
    2. Estimar `distancia_carretera_km` aplicando un coeficiente de sinuosidad de montaña (ej. 1.32x).
    3. Estimar `tiempo_estimado_min` asumiendo una velocidad media rural de 45 km/h.
    4. Construir `geometria_ruta` con `build_curved_mountain_polyline(...)`.
    5. Retornar el diccionario con las claves requeridas por `RutaSanitariaSchema`.
    """
    pass


async def calculate_route_cartociudad(
    lat_orig: float, lon_orig: float, lat_dest: float, lon_dest: float
) -> Dict:
    """
    TODO: Realizar una petición HTTP asíncrona (`httpx.AsyncClient`) en tiempo real
    al endpoint de rutas de CartoCiudad (`https://www.cartociudad.es/services/api/route`)
    pasando las coordenadas de origen y destino.
    - Si responde HTTP 200 con distancia y tiempo válidos, extraer `distancia_carretera_km`,
      `tiempo_estimado_min` y parsear la geometría WKT (`LINESTRING`) a lista de pares `[lat, lon]`.
    - Si ocurre cualquier excepción de red, timeout o formato inválido, capturar el error
      y retornar `compute_fallback_route(lat_orig, lon_orig, lat_dest, lon_dest)` para que la
      demostración en vivo nunca falle.
    """
    pass
