#!/usr/bin/env python3
"""
Módulo ETL P3 para la descarga y carga de centros sanitarios de la Comunidad de Madrid.

Consulta el catálogo del Portal de Datos Abiertos de la CAM (API CKAN y recursos JSON/CSV),
convierte coordenadas UTM ETRS89 (EPSG:25830) a WGS84 (EPSG:4326), clasifica los centros
con urgencias y carga los registros en la tabla `centros_sanitarios` de PostGIS.

Ejecución aislada:
    python etl/p3_cam/etl_sanidad.py
"""

import csv
import io
import json
import math
import os
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional, Tuple, Union
import requests

try:
    import psycopg2
except ImportError:  # pragma: no cover - permite ejecutar pruebas unitarias en host sin psycopg2
    psycopg2 = None  # type: ignore

MAGENTA = "\033[95m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

# Endpoints oficiales del Portal de Datos Abiertos de la Comunidad de Madrid (CKAN API v3)
CAM_CKAN_PACKAGE_URL = (
    "https://datos.comunidad.madrid/catalogo/api/3/action/"
    "package_show?id=centros_servicios_establecimientos_sanitarios"
)
CAM_DIRECT_JSON_URL = os.getenv(
    "CAM_SANIDAD_JSON_URL",
    "https://datos.comunidad.madrid/dataset/d8a0a444-adf5-4c04-8999-0eac3de52cb7/"
    "resource/94090084-2276-4a07-87b4-cd028ea6b46d/download/"
    "centros_servicios_establecimientos_sanitarios.json",
)
CAM_DIRECT_CSV_URL = os.getenv(
    "CAM_SANIDAD_CSV_URL",
    "https://datos.comunidad.madrid/dataset/d8a0a444-adf5-4c04-8999-0eac3de52cb7/"
    "resource/2948b4da-8b39-42b7-b667-779a5284f39d/download/"
    "centros_servicios_establecimientos_sanitarios.csv",
)

# Palabras clave de tipos de centro relevantes para atención primaria, rural y urgencias
RELEVANT_CENTER_TYPES = (
    "CENTRO DE SALUD",
    "CONSULTORIO",
    "HOSPITAL",
    "URGENCIAS",
    "ATENCION CONTINUADA",
    "ATENCIÓN CONTINUADA",
    "PUNTO DE ATENCION",
    "PUNTO DE ATENCIÓN",
    "SAR",
    "SUAP",
    "POLICLINICA",
)

# Municipios de referencia con Punto de Atención Continuada / Urgencias SAR 24h en el Norte de Madrid
SAR_24H_MUNICIPALITIES = {
    "BUITRAGO DEL LOZOYA",
    "TORRELAGUNA",
    "RASCAFRIA",
    "LA CABRERA",
    "SOTO DEL REAL",
    "MANZANARES EL REAL",
    "ALGETE",
    "SAN SEBASTIAN DE LOS REYES",
    "COLMENAR VIEJO",
    "TRES CANTOS",
}

# Municipios semilla para carga inicial ligera (el resto se hidrata bajo demanda)
DEFAULT_SEED_MUNICIPIOS = ["La Hiruela", "Buitrago del Lozoya"]

# Caché ligera en memoria del catálogo de la CAM para evitar descargas repetidas (~15 MB) en clics sucesivos
CAM_CACHE_TTL_SECONDS = int(os.getenv("CAM_CACHE_TTL_SECONDS", "600"))
_CAM_API_CACHE: Dict[str, Any] = {
    "timestamp": 0.0,
    "records": [],
    "only_relevant": True,
}


def _normalize_text(value: Any) -> str:
    """Normaliza texto a mayúsculas ASCII sin tildes ni espacios redundantes."""
    if value is None:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(value).strip())
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(without_accents.upper().split())


def get_db_connection():
    """Crea y devuelve una conexión `psycopg2` a PostgreSQL leyendo las variables de entorno."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "rehabitar"),
        password=os.getenv("POSTGRES_PASSWORD", "rehabitar_pwd"),
        dbname=os.getenv("POSTGRES_DB", "rehabitar_db"),
    )


def utm30n_etrs89_to_wgs84(x: float, y: float) -> Optional[Tuple[float, float]]:
    """
    Convierte coordenadas UTM Huso 30N ETRS89 (EPSG:25830) a coordenadas geográficas
    WGS84 (EPSG:4326) en formato `(latitud, longitud)`. Si ya llegan en grados WGS84
    válidos, las devuelve directamente.
    """
    # Si ya vienen en grados geográficos WGS84 (Madrid: lat ~40.4, lon ~-3.7), devolver directamente
    if 35.0 <= x <= 45.0 and -10.0 <= y <= 5.0:
        return round(x, 6), round(y, 6)
    if -10.0 <= x <= 5.0 and 35.0 <= y <= 45.0:
        return round(y, 6), round(x, 6)

    # Validar rango proyectado UTM Huso 30N (Península Ibérica)
    if not (100000.0 <= x <= 900000.0 and 3500000.0 <= y <= 5000000.0):
        return None

    a = 6378137.0  # Semieje mayor GRS80 / WGS84
    f = 1.0 / 298.257222101
    k0 = 0.9996
    lon0_deg = -3.0  # Meridiano central del Huso 30 (3° W)
    lon0 = math.radians(lon0_deg)

    e2 = 2 * f - f * f
    e_prime2 = e2 / (1.0 - e2)
    e1 = (1.0 - math.sqrt(1.0 - e2)) / (1.0 + math.sqrt(1.0 - e2))

    x_adj = x - 500000.0
    y_adj = y

    m = y_adj / k0
    mu = m / (a * (1.0 - e2 / 4.0 - 3.0 * (e2 ** 2) / 64.0 - 5.0 * (e2 ** 3) / 256.0))

    phi1 = (
        mu
        + (3.0 * e1 / 2.0 - 27.0 * (e1 ** 3) / 32.0) * math.sin(2.0 * mu)
        + (21.0 * (e1 ** 2) / 16.0 - 55.0 * (e1 ** 4) / 32.0) * math.sin(4.0 * mu)
        + (151.0 * (e1 ** 3) / 96.0) * math.sin(6.0 * mu)
        + (1097.0 * (e1 ** 4) / 512.0) * math.sin(8.0 * mu)
    )

    sin_phi1 = math.sin(phi1)
    cos_phi1 = math.cos(phi1)
    tan_phi1 = math.tan(phi1)

    n1 = a / math.sqrt(1.0 - e2 * (sin_phi1 ** 2))
    t1 = tan_phi1 ** 2
    c1 = e_prime2 * (cos_phi1 ** 2)
    r1 = a * (1.0 - e2) / ((1.0 - e2 * (sin_phi1 ** 2)) ** 1.5)
    d = x_adj / (n1 * k0)

    lat_rad = phi1 - (n1 * tan_phi1 / r1) * (
        (d ** 2) / 2.0
        - (5.0 + 3.0 * t1 + 10.0 * c1 - 4.0 * (c1 ** 2) - 9.0 * e_prime2) * (d ** 4) / 24.0
        + (61.0 + 90.0 * t1 + 298.0 * c1 + 45.0 * (t1 ** 2) - 252.0 * e_prime2 - 3.0 * (c1 ** 2))
        * (d ** 6)
        / 720.0
    )

    lon_rad = lon0 + (
        d
        - (1.0 + 2.0 * t1 + c1) * (d ** 3) / 6.0
        + (5.0 - 2.0 * c1 + 28.0 * t1 - 3.0 * (c1 ** 2) + 8.0 * e_prime2 + 24.0 * (t1 ** 2))
        * (d ** 5)
        / 120.0
    ) / cos_phi1

    lat_deg = round(math.degrees(lat_rad), 6)
    lon_deg = round(math.degrees(lon_rad), 6)
    return lat_deg, lon_deg


def detect_tiene_urgencias(
    tipo: str,
    nombre: str,
    municipio: str = "",
    raw_urg: Any = None,
    horario: str = "",
) -> bool:
    """
    Determina si un centro sanitario dispone de servicio de urgencias o atención
    continuada 24h según su tipo, nombre, horario o municipio cabecera SAR.
    """
    if raw_urg is not None and str(raw_urg).strip() != "":
        val = str(raw_urg).strip().lower()
        if val in ("true", "1", "si", "sí", "s", "yes"):
            return True
        if val in ("false", "0", "no", "n"):
            return False

    combined_norm = _normalize_text(f"{tipo} {nombre} {horario}")
    mun_norm = _normalize_text(municipio)

    if any(
        k in combined_norm
        for k in ("URGENCIAS", "HOSPITAL", "ATENCION CONTINUADA", "24 HORAS", "24H")
    ):
        return True

    if re.search(r"\b(?:SAR|SUAP|PAC)\b", combined_norm):
        return True

    if (
        "CENTRO DE SALUD" in combined_norm or "CONSULTORIO" in combined_norm
    ) and mun_norm in SAR_24H_MUNICIPALITIES:
        # Los centros de salud y consultorios en cabeceras SAR actúan como referencia de urgencias comarcal
        return True

    return False


def is_primary_or_emergency_center(tipo: str, nombre: str) -> bool:
    """Indica si un centro pertenece a atención primaria, hospitalaria o de urgencias."""
    combined = f"{tipo} {nombre}".upper()
    return any(keyword in combined for keyword in RELEVANT_CENTER_TYPES)


def _parse_float(value: Any) -> Optional[float]:
    """Convierte un valor a float aceptando coma decimal, o devuelve None si no es válido."""
    if value is None:
        return None
    s = str(value).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def normalize_cam_record(raw: Dict[str, Any], only_relevant: bool = True) -> Optional[Dict[str, Any]]:
    """
    Normaliza un registro crudo del JSON o CSV de la CAM al esquema de `centros_sanitarios`.
    Devuelve None si faltan datos obligatorios, no es asistencial o sus coordenadas quedan fuera de rango.
    """
    id_centro = str(
        raw.get("id_centro")
        or raw.get("centro_nro_registro")
        or raw.get("codigo_centro")
        or raw.get("cod_centro")
        or raw.get("PK")
        or ""
    ).strip()

    nombre_raw = str(
        raw.get("nombre")
        or raw.get("centro_denominacion")
        or raw.get("denominacion")
        or raw.get("nombre_centro")
        or raw.get("centro_desc")
        or ""
    ).strip()

    tipo = str(
        raw.get("tipo")
        or raw.get("centro_tipo_descripcion")
        or raw.get("centro_tipo")
        or raw.get("tipo_centro")
        or raw.get("clasificacion")
        or "Centro Sanitario"
    ).strip()

    municipio = str(
        raw.get("municipio_nombre")
        or raw.get("direccion_municipio_nombre")
        or raw.get("direccion_municipio")
        or raw.get("municipio")
        or raw.get("localidad")
        or ""
    ).strip()

    oferta = str(
        raw.get("oferta_asistecial")
        or raw.get("oferta_asistencial")
        or ""
    ).strip()

    nombre = nombre_raw or (f"{tipo} {municipio}".strip() if municipio else id_centro)

    if not id_centro or not nombre:
        return None

    if only_relevant and not is_primary_or_emergency_center(tipo, nombre):
        return None

    # Extraer coordenadas (WGS84 directo o UTM ETRS89 EPSG:25830 del portal de la CAM)
    lat = _parse_float(raw.get("latitud") or raw.get("lat"))
    lon = _parse_float(raw.get("longitud") or raw.get("lon") or raw.get("lng"))

    if lat is None or lon is None:
        utm_x = _parse_float(
            raw.get("localizacion_coordenada_x")
            or raw.get("direccion_coordenada_x")
            or raw.get("coordenada_x_etrs89")
            or raw.get("coordenada_x")
            or raw.get("x")
        )
        utm_y = _parse_float(
            raw.get("localizacion_coordenada_y")
            or raw.get("direccion_coordenada_y")
            or raw.get("coordenada_y_etrs89")
            or raw.get("coordenada_y")
            or raw.get("y")
        )
        if utm_x is not None and utm_y is not None and utm_x > 1000 and utm_y > 1000:
            coords = utm30n_etrs89_to_wgs84(utm_x, utm_y)
            if coords is not None:
                lat, lon = coords

    if lat is None or lon is None:
        return None

    # Validar que las coordenadas estén dentro del entorno geográfico de la Comunidad de Madrid / España central
    if not (39.5 <= lat <= 41.5 and -4.8 <= lon <= -2.8):
        return None

    vial_tipo = str(raw.get("direccion_vial_tipo") or "").strip()
    vial_nombre = str(
        raw.get("direccion")
        or raw.get("direccion_vial_nombre")
        or raw.get("domicilio")
        or raw.get("direccion_completa")
        or ""
    ).strip()
    num_vial = str(raw.get("direccion_vial_nro") or "").strip()
    cp = str(raw.get("direccion_codigo_postal") or "").strip()

    direccion = f"{vial_tipo} {vial_nombre}".strip() if vial_tipo and vial_tipo not in vial_nombre else vial_nombre
    if direccion and num_vial and num_vial not in direccion:
        direccion = f"{direccion} {num_vial}".strip()
    if direccion and cp and cp not in direccion:
        direccion = f"{direccion} ({cp})".strip()

    telefono = str(
        raw.get("telefono")
        or raw.get("contacto_telefono")
        or raw.get("tlf")
        or ""
    ).strip()[:30]

    tiene_urg = detect_tiene_urgencias(
        tipo=tipo,
        nombre=f"{nombre} {oferta}".strip(),
        municipio=municipio,
        raw_urg=raw.get("tiene_urgencias"),
        horario=str(raw.get("horario") or ""),
    )

    horario = str(
        raw.get("horario")
        or ("24 Horas / Atención Continuada" if tiene_urg else "Horario de Atención Primaria")
    ).strip()[:120]

    # Homologación del centro de referencia de Buitrago del Lozoya con código CS-28027.
    # Se exige igualdad exacta tras normalizar acentos para no colisionar con
    # 'Gargantilla del Lozoya y Pinilla de Buitrago'.
    if _normalize_text(municipio) == "BUITRAGO DEL LOZOYA" and (
        "CENTRO DE SALUD" in _normalize_text(tipo) or "CONSULTORIO" in _normalize_text(tipo)
    ):
        id_centro = "CS-28027"
        if not nombre_raw:
            nombre = "Consultorio Local Buitrago del Lozoya"
        tipo = "Centro de Salud / Urgencias"
        tiene_urg = True

    return {
        "id_centro": id_centro[:40],
        "nombre": nombre[:200],
        "tipo": tipo[:100],
        "tiene_urgencias": bool(tiene_urg),
        "municipio_nombre": municipio[:120] if municipio else "Madrid",
        "direccion": direccion[:250] if direccion else None,
        "horario": horario,
        "telefono": telefono if telefono else None,
        "latitud": round(float(lat), 6),
        "longitud": round(float(lon), 6),
    }


def discover_cam_sanidad_resource_urls(timeout: float = 8.0) -> List[Tuple[str, str]]:
    """
    Consulta la API CKAN de Datos Abiertos de la CAM para obtener las URLs vigentes
    en JSON y CSV del catálogo sanitario. Añade URLs de respaldo priorizando JSON sobre CSV.
    """
    discovered: List[Tuple[str, str]] = []
    try:
        resp = requests.get(CAM_CKAN_PACKAGE_URL, timeout=timeout)
        if resp.status_code == 200:
            payload = resp.json()
            resources = payload.get("result", {}).get("resources", [])
            for res in resources:
                fmt = str(res.get("format") or "").strip().upper()
                url = str(res.get("url") or "").strip()
                if url and fmt in ("JSON", "CSV"):
                    discovered.append((fmt, url))
    except Exception:
        pass

    # Priorizar formato JSON sobre CSV y añadir las URLs directas oficiales de respaldo sin duplicados
    discovered.sort(key=lambda item: 0 if item[0] == "JSON" else 1)
    for fallback in (("JSON", CAM_DIRECT_JSON_URL), ("CSV", CAM_DIRECT_CSV_URL)):
        if fallback not in discovered:
            discovered.append(fallback)
    return discovered


def parse_cam_json_payload(payload: Any, only_relevant: bool = True) -> List[Dict[str, Any]]:
    """Extrae y normaliza los centros sanitarios de una respuesta JSON evitando duplicados por id_centro."""
    raw_list: List[Dict[str, Any]] = []
    if isinstance(payload, dict):
        raw_list = payload.get("data") or payload.get("records") or payload.get("result") or []
    elif isinstance(payload, list):
        raw_list = payload

    by_id: Dict[str, Dict[str, Any]] = {}
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        norm = normalize_cam_record(item, only_relevant=only_relevant)
        if not norm:
            continue
        cid = norm["id_centro"]
        if cid not in by_id:
            by_id[cid] = norm
        elif norm["tiene_urgencias"] and not by_id[cid]["tiene_urgencias"]:
            by_id[cid]["tiene_urgencias"] = True
            by_id[cid]["horario"] = norm["horario"]
    return list(by_id.values())


def parse_cam_csv_content(raw_bytes: Union[bytes, str], only_relevant: bool = True) -> List[Dict[str, Any]]:
    """Decodifica y parsea un CSV sanitario de la CAM (UTF-8 o Latin-1) consolidando duplicados por id_centro."""
    if isinstance(raw_bytes, str):
        text_content = raw_bytes
    else:
        try:
            text_content = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text_content = raw_bytes.decode("latin-1", errors="replace")

    first_line = text_content.splitlines()[0] if text_content else ""
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","

    reader = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)
    by_id: Dict[str, Dict[str, Any]] = {}
    for row in reader:
        norm = normalize_cam_record(row, only_relevant=only_relevant)
        if not norm:
            continue
        cid = norm["id_centro"]
        if cid not in by_id:
            by_id[cid] = norm
        elif norm["tiene_urgencias"] and not by_id[cid]["tiene_urgencias"]:
            by_id[cid]["tiene_urgencias"] = True
            by_id[cid]["horario"] = norm["horario"]
    return list(by_id.values())


def fetch_cam_health_centers_api(
    timeout: Optional[float] = None,
    only_relevant: bool = True,
    force_refresh: bool = False,
) -> List[Dict[str, Any]]:
    """
    Descarga y normaliza el catálogo de centros sanitarios desde la API de Datos Abiertos
    de la CAM probando los recursos JSON y CSV. Usa caché en memoria con TTL configurable
    salvo que `force_refresh=True`.
    """
    if (
        not force_refresh
        and _CAM_API_CACHE["records"]
        and _CAM_API_CACHE.get("only_relevant") == only_relevant
        and (time.time() - float(_CAM_API_CACHE["timestamp"])) < CAM_CACHE_TTL_SECONDS
    ):
        return [dict(c) for c in _CAM_API_CACHE["records"]]

    req_timeout = timeout or float(os.getenv("EXTERNAL_API_TIMEOUT", "10"))
    candidate_urls = discover_cam_sanidad_resource_urls(timeout=req_timeout)

    last_error: Optional[Exception] = None
    for fmt, url in candidate_urls:
        try:
            print(f"{MAGENTA}[ETL P3-CAM] Consultando recurso {fmt} en API Datos Abiertos CAM: {url}{RESET}")
            resp = requests.get(
                url,
                timeout=req_timeout,
                headers={"User-Agent": "ReHabitar-PoC-UC3M/1.0 (Datos Masivos y Encadenados)"},
            )
            resp.raise_for_status()

            if fmt == "JSON" or url.lower().endswith(".json"):
                records = parse_cam_json_payload(resp.json(), only_relevant=only_relevant)
            else:
                records = parse_cam_csv_content(resp.content, only_relevant=only_relevant)

            if records:
                _CAM_API_CACHE["timestamp"] = time.time()
                _CAM_API_CACHE["records"] = [dict(c) for c in records]
                _CAM_API_CACHE["only_relevant"] = only_relevant
                print(
                    f"{GREEN}[ETL P3-CAM] Recibidos y normalizados {len(records)} centros sanitarios "
                    f"asistenciales desde la API oficial de la CAM.{RESET}"
                )
                return records
        except Exception as exc:
            last_error = exc
            print(f"{YELLOW}[ETL P3-CAM] Aviso al leer {url}: {exc}{RESET}")

    raise RuntimeError(
        f"No se pudo obtener el catálogo de centros sanitarios desde la API de la CAM: {last_error}"
    )


def upsert_health_centers_to_db(centers: List[Dict[str, Any]], conn=None) -> Tuple[int, int]:
    """
    Inserta o actualiza los centros sanitarios en `centros_sanitarios` creando su geometría
    PostGIS en EPSG:4326. Devuelve `(total_insertados, total_con_urgencias)`.
    """
    own_conn = False
    if conn is None:
        conn = get_db_connection()
        own_conn = True

    inserted_count = 0
    urgencias_count = 0

    upsert_sql = """
        INSERT INTO centros_sanitarios (
            id_centro, nombre, tipo, tiene_urgencias,
            municipio_nombre, direccion, horario, telefono,
            latitud, longitud, geom
        )
        VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        )
        ON CONFLICT (id_centro) DO UPDATE SET
            nombre = EXCLUDED.nombre,
            tipo = EXCLUDED.tipo,
            tiene_urgencias = EXCLUDED.tiene_urgencias,
            municipio_nombre = EXCLUDED.municipio_nombre,
            direccion = EXCLUDED.direccion,
            horario = EXCLUDED.horario,
            telefono = EXCLUDED.telefono,
            latitud = EXCLUDED.latitud,
            longitud = EXCLUDED.longitud,
            geom = EXCLUDED.geom;
    """

    try:
        with conn:
            with conn.cursor() as cur:
                for c in centers:
                    if c["tiene_urgencias"]:
                        urgencias_count += 1
                    cur.execute(
                        upsert_sql,
                        (
                            c["id_centro"],
                            c["nombre"],
                            c["tipo"],
                            bool(c["tiene_urgencias"]),
                            c.get("municipio_nombre"),
                            c.get("direccion"),
                            c.get("horario"),
                            c.get("telefono"),
                            float(c["latitud"]),
                            float(c["longitud"]),
                            float(c["longitud"]),
                            float(c["latitud"]),
                        ),
                    )
                    inserted_count += 1
        return inserted_count, urgencias_count
    finally:
        if own_conn:
            conn.close()


def ingest_centros_for_municipio(
    municipio_nombre: str,
    conn=None,
    force_refresh: bool = False,
) -> int:
    """
    Filtra e inserta bajo demanda los centros sanitarios de un municipio desde la API de la CAM.
    Incluye la red de urgencias solo si la tabla aún no contiene ningún centro con urgencias.
    """
    own_conn = False
    if conn is None:
        conn = get_db_connection()
        own_conn = True

    try:
        include_urgencias = False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM centros_sanitarios WHERE tiene_urgencias = TRUE;"
                )
                row = cur.fetchone()
                if row is not None and isinstance(row[0], int) and row[0] == 0:
                    include_urgencias = True
        except Exception:
            include_urgencias = False

        all_centers = fetch_cam_health_centers_api(force_refresh=force_refresh)
        target_mun = _normalize_text(municipio_nombre)
        filtered = [
            c
            for c in all_centers
            if _normalize_text(c.get("municipio_nombre")) == target_mun
            or (include_urgencias and bool(c.get("tiene_urgencias")))
        ]
        if not filtered:
            return 0

        inserted, _ = upsert_health_centers_to_db(filtered, conn=conn)
        return inserted
    finally:
        if own_conn:
            conn.close()


def run_etl_p3(seed_municipios: Optional[List[str]] = None) -> str:
    """
    Ejecuta la carga inicial del módulo P3 insertando la red de urgencias y los centros
    de los municipios semilla en PostgreSQL. El resto de municipios se hidrata bajo demanda.
    """
    target_seeds = DEFAULT_SEED_MUNICIPIOS if seed_municipios is None else seed_municipios
    seed_set = {_normalize_text(m) for m in target_seeds if m}

    centers = fetch_cam_health_centers_api()
    seed_centers = [
        c
        for c in centers
        if bool(c.get("tiene_urgencias"))
        or _normalize_text(c.get("municipio_nombre")) in seed_set
    ]
    inserted_count, urgencias_count = upsert_health_centers_to_db(seed_centers)
    print(
        f"{GREEN}[ETL P3-CAM] Carga semilla desde API CAM... OK. "
        f"({inserted_count} centros registrados, {urgencias_count} con Urgencias; resto bajo demanda){RESET}"
    )
    return (
        f"{inserted_count} centros sanitarios semilla ({urgencias_count} con Urgencias; "
        f"resto bajo demanda)"
    )


if __name__ == "__main__":
    run_etl_p3()
