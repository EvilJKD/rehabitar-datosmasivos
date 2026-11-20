"""
Servicio P5.1 - Integración Virtual en Tiempo Real con API CartoCiudad (IGN)
Responsable: Desarrollador P5

REGLA ARQUITECTÓNICA DE LA PROPUESTA (Sección 6.3, 7.3 y Diagrama Sección 9):
"El tiempo de trayecto hacia el punto sanitario NO se almacena en ninguna tabla para
evitar obsolescencia. Al consultar un municipio, el backend identifica el punto
asistencial más cercano en PostGIS y realiza la llamada REST en tiempo real a la API
de CartoCiudad, fusionando estos valores en memoria con el motor WLC."
"""

import asyncio
import json
import logging
import math
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import requests

try:
    import httpx
except ImportError:  # pragma: no cover - permite ejecutar pruebas sin httpx en host
    httpx = None  # type: ignore

logger = logging.getLogger("backend.p5_cartociudad")

EARTH_RADIUS_KM = 6371.0088
SINUOSITY_FACTOR = 1.32
RURAL_SPEED_KMH = 45.0

CARTOCIUDAD_ROUTE_URL = os.getenv(
    "CARTOCIUDAD_ROUTE_URL",
    "https://www.cartociudad.es/services/api/route",
)
CARTOCIUDAD_TIMEOUT_SECONDS = float(os.getenv("EXTERNAL_API_TIMEOUT", "10"))
CARTOCIUDAD_CACHE_TTL_SECONDS = int(os.getenv("CARTOCIUDAD_CACHE_TTL_SECONDS", "900"))

# Caché efímera únicamente en memoria RAM (nunca persistida en PostgreSQL)
_CARTOCIUDAD_MEM_CACHE: Dict[Tuple[float, float, float, float], Dict[str, Any]] = {}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia ortodrómica Haversine en kilómetros entre dos coordenadas WGS84.
    """
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    d_phi = math.radians(float(lat2) - float(lat1))
    d_lambda = math.radians(float(lon2) - float(lon1))

    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(d_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return round(EARTH_RADIUS_KM * c, 2)


def build_curved_mountain_polyline(
    lat1: float, lon1: float, lat2: float, lon2: float, steps: int = 12
) -> List[List[float]]:
    """
    Genera una polilínea interpolada `[[lat, lon], ...]` de respaldo para Leaflet
    con curvatura suave de trazado de montaña cuando CartoCiudad no esté accesible.
    Garantiza exactamente `steps + 1` puntos con coincidencia exacta en los extremos.
    """
    n_steps = max(1, int(steps))
    p_orig = [float(lat1), float(lon1)]
    p_dest = [float(lat2), float(lon2)]

    dlat = p_dest[0] - p_orig[0]
    dlon = p_dest[1] - p_orig[1]
    dist_deg = math.hypot(dlat, dlon)

    if dist_deg == 0.0:
        return [list(p_orig) for _ in range(n_steps + 1)]

    perp_lat = -dlon / dist_deg
    perp_lon = dlat / dist_deg
    curvature = dist_deg * 0.08

    points: List[List[float]] = [p_orig]
    for i in range(1, n_steps):
        t = i / n_steps
        offset = math.sin(math.pi * t) * curvature
        lat_i = round(p_orig[0] + t * dlat + offset * perp_lat, 6)
        lon_i = round(p_orig[1] + t * dlon + offset * perp_lon, 6)
        points.append([lat_i, lon_i])
    points.append(p_dest)
    return points


def compute_fallback_route(
    lat_orig: float, lon_orig: float, lat_dest: float, lon_dest: float
) -> Dict[str, Any]:
    """
    Cálculo de respaldo en memoria (Haversine * factor de sinuosidad 1.32x y
    velocidad media rural de 45 km/h) para garantizar que la Consulta 2 y el motor WLC
    nunca fallen durante la demostración en vivo si CartoCiudad sufre caídas o timeouts.
    """
    distancia_euclidea_km = haversine_km(lat_orig, lon_orig, lat_dest, lon_dest)
    distancia_carretera_km = round(distancia_euclidea_km * SINUOSITY_FACTOR, 2)
    tiempo_estimado_min = round((distancia_carretera_km / RURAL_SPEED_KMH) * 60.0, 2)

    return {
        "distancia_euclidea_km": distancia_euclidea_km,
        "distancia_carretera_km": distancia_carretera_km,
        "tiempo_estimado_min": tiempo_estimado_min,
        "fuente_ruta": "Fallback Haversine (45 km/h)",
        "geometria_ruta": build_curved_mountain_polyline(
            lat_orig, lon_orig, lat_dest, lon_dest
        ),
    }


def _to_leaflet_latlon(coord_x: float, coord_y: float) -> List[float]:
    """Convierte un par (lon, lat) de WKT/GeoJSON a formato Leaflet [lat, lon]."""
    return [round(float(coord_y), 6), round(float(coord_x), 6)]


def _decode_encoded_polyline(encoded: str, precision: int = 5) -> List[List[float]]:
    """Decodifica una cadena Google Encoded Polyline (precision 1e-5 usada por CartoCiudad IGN)."""
    if not isinstance(encoded, str) or not encoded:
        return []

    points: List[List[float]] = []
    index = 0
    lat = 0
    lng = 0
    factor = float(10 ** precision)
    length = len(encoded)

    try:
        while index < length:
            for axis in (0, 1):
                shift = 0
                result = 0
                while True:
                    if index >= length:
                        return []
                    raw_ord = ord(encoded[index])
                    if raw_ord < 63 or raw_ord > 126:
                        return []
                    byte = raw_ord - 63
                    index += 1
                    result |= (byte & 0x1F) << shift
                    shift += 5
                    if byte < 0x20:
                        break
                delta = ~(result >> 1) if (result & 1) else (result >> 1)
                if axis == 0:
                    lat += delta
                else:
                    lng += delta

            lat_val = round(lat / factor, 6)
            lon_val = round(lng / factor, 6)
            # Validar ámbito geográfico coherente para España (Península, Baleares, Canarias, Ceuta/Melilla)
            if not (27.0 <= lat_val <= 45.0 and -19.0 <= lon_val <= 6.0):
                return []
            points.append([lat_val, lon_val])
    except (IndexError, TypeError, ValueError):
        return []

    return points if len(points) >= 2 else []


def _parse_cartociudad_geometry(raw_geom: Any) -> List[List[float]]:
    """
    Extrae una polilínea `[[lat, lon], ...]` desde la geometría devuelta por CartoCiudad
    soportando Encoded Polyline (`geom` de IGN), WKT (`LINESTRING` / `MULTILINESTRING`),
    diccionario o cadena GeoJSON y listas de puntos.
    """
    if not raw_geom:
        return []

    if isinstance(raw_geom, dict):
        gtype = str(raw_geom.get("type") or "").upper()
        coords = raw_geom.get("coordinates")
        try:
            if gtype == "MULTILINESTRING" and isinstance(coords, list):
                flat: List[List[float]] = []
                for segment in coords:
                    if isinstance(segment, list):
                        for pt in segment:
                            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                                flat.append(_to_leaflet_latlon(pt[0], pt[1]))
                return flat
            if isinstance(coords, list):
                return [
                    _to_leaflet_latlon(pt[0], pt[1])
                    for pt in coords
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2
                ]
        except (TypeError, ValueError):
            return []
        return []

    if isinstance(raw_geom, list):
        parsed: List[List[float]] = []
        try:
            for pt in raw_geom:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    x, y = float(pt[0]), float(pt[1])
                    # Detectar si el par ya viene en [lat, lon] para España/Madrid vs [lon, lat]
                    if 25.0 <= x <= 55.0 and -20.0 <= y <= 10.0:
                        parsed.append([round(x, 6), round(y, 6)])
                    else:
                        parsed.append(_to_leaflet_latlon(x, y))
        except (TypeError, ValueError):
            return []
        return parsed

    if isinstance(raw_geom, str):
        stripped = raw_geom.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                decoded_json = json.loads(stripped)
            except ValueError:
                return []
            if not isinstance(decoded_json, str):
                return _parse_cartociudad_geometry(decoded_json)
            return []

        upper_geom = stripped.upper()
        if "LINESTRING" in upper_geom or ("(" in stripped and " " in stripped):
            pairs = re.findall(r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)", stripped)
            try:
                return [_to_leaflet_latlon(float(lon_s), float(lat_s)) for lon_s, lat_s in pairs]
            except ValueError:
                return []
        return _decode_encoded_polyline(stripped)

    return []


def _parse_cartociudad_payload(
    payload: Any,
    lat_orig: float,
    lon_orig: float,
    lat_dest: float,
    lon_dest: float,
) -> Optional[Dict[str, Any]]:
    """Normaliza la respuesta JSON de CartoCiudad a unidades homogéneas (km, min, [[lat, lon]])."""
    if not isinstance(payload, dict) or payload.get("found") is False:
        return None

    uses_native_dist = payload.get("distance") is not None
    uses_native_time = payload.get("time") is not None

    raw_dist = payload["distance"] if uses_native_dist else payload.get("distancia")
    raw_time = payload["time"] if uses_native_time else payload.get("tiempo")
    if raw_dist is None or raw_time is None:
        return None

    try:
        dist_val = float(raw_dist)
        time_val = float(raw_time)
    except (TypeError, ValueError):
        return None

    if dist_val < 0.0 or time_val < 0.0:
        return None

    dist_eucl_km = haversine_km(lat_orig, lon_orig, lat_dest, lon_dest)
    if (dist_val == 0.0 or time_val == 0.0) and dist_eucl_km > 0.05:
        return None

    if uses_native_dist:
        dist_km = dist_val / 1000.0
    else:
        dist_km = dist_val / 1000.0 if dist_val > 200.0 else dist_val

    if uses_native_time:
        time_min = time_val / 60000.0
    elif time_val > 10000.0:
        time_min = time_val / 60000.0
    elif time_val > 180.0:
        time_min = time_val / 60.0
    else:
        time_min = time_val

    geometria = _parse_cartociudad_geometry(
        payload.get("geom") or payload.get("geometry") or payload.get("coordinates")
    )
    if len(geometria) < 2:
        geometria = build_curved_mountain_polyline(
            lat_orig, lon_orig, lat_dest, lon_dest
        )

    return {
        "distancia_euclidea_km": dist_eucl_km,
        "distancia_carretera_km": round(dist_km, 2),
        "tiempo_estimado_min": round(time_min, 2),
        "fuente_ruta": "API CartoCiudad IGN (Tiempo Real)",
        "geometria_ruta": geometria,
    }


def _fetch_cartociudad_sync(params: Dict[str, str], timeout: float) -> Any:
    """Ejecución síncrona auxiliar con `requests` cuando `httpx` no está disponible."""
    resp = requests.get(
        CARTOCIUDAD_ROUTE_URL,
        params=params,
        timeout=timeout,
        headers={"User-Agent": "ReHabitar-PoC-UC3M/1.0"},
    )
    resp.raise_for_status()
    return resp.json()


async def _request_cartociudad(params: Dict[str, str], timeout: float) -> Any:
    """Realiza la petición GET asíncrona usando `httpx.AsyncClient` si está disponible."""
    if httpx is not None:
        async with httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "ReHabitar-PoC-UC3M/1.0"},
        ) as client:
            resp = await client.get(CARTOCIUDAD_ROUTE_URL, params=params)
            resp.raise_for_status()
            return resp.json()

    return await asyncio.to_thread(_fetch_cartociudad_sync, params, timeout)


def _clone_route_dict(route: Dict[str, Any]) -> Dict[str, Any]:
    """Devuelve una copia independiente del diccionario de ruta para evitar mutaciones."""
    cloned = dict(route)
    cloned["geometria_ruta"] = [list(pt) for pt in route.get("geometria_ruta", [])]
    return cloned


async def calculate_route_cartociudad(
    lat_orig: float,
    lon_orig: float,
    lat_dest: float,
    lon_dest: float,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Integración Virtual en Tiempo Real (Consulta 2 y Motor WLC):
    1. Consulta caché efímera en memoria RAM (`_CARTOCIUDAD_MEM_CACHE`) salvo `force_refresh=True`.
    2. Realiza petición HTTP GET asíncrona en tiempo real a
       `https://www.cartociudad.es/services/api/route` con `orig` y `dest`.
    3. Extrae `distancia_carretera_km`, `tiempo_estimado_min` y `geometria_ruta` (`[[lat, lon], ...]`).
    4. Si falla, expira el timeout o devuelve datos inválidos, retorna `compute_fallback_route(...)`.
    5. Retornar el diccionario en memoria al Mediador FastAPI SIN guardarlo en PostgreSQL.
    """
    cache_key = (
        round(float(lat_orig), 5),
        round(float(lon_orig), 5),
        round(float(lat_dest), 5),
        round(float(lon_dest), 5),
    )

    if not force_refresh and cache_key in _CARTOCIUDAD_MEM_CACHE:
        entry = _CARTOCIUDAD_MEM_CACHE[cache_key]
        if (time.time() - float(entry["timestamp"])) < CARTOCIUDAD_CACHE_TTL_SECONDS:
            return _clone_route_dict(entry["data"])

    params = {
        "orig": f"{lat_orig},{lon_orig}",
        "dest": f"{lat_dest},{lon_dest}",
        "locale": "es",
        "vehicle": "CAR",
    }

    try:
        payload = await _request_cartociudad(params, CARTOCIUDAD_TIMEOUT_SECONDS)
        parsed = _parse_cartociudad_payload(
            payload, lat_orig, lon_orig, lat_dest, lon_dest
        )
        if parsed is not None:
            _CARTOCIUDAD_MEM_CACHE[cache_key] = {
                "timestamp": time.time(),
                "data": _clone_route_dict(parsed),
            }
            return parsed
        logger.warning("Respuesta de CartoCiudad incompleta o inválida; usando fallback Haversine.")
    except Exception as exc:
        logger.warning("CartoCiudad no disponible (%s); usando fallback Haversine.", exc)

    return compute_fallback_route(lat_orig, lon_orig, lat_dest, lon_dest)
