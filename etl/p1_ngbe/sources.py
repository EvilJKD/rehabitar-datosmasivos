"""Fuentes públicas del catálogo municipal y de las métricas de P1."""

import json
import os
import re
from functools import lru_cache
from io import BytesIO
from math import cos, radians
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

from openpyxl import load_workbook


# Obra derivada de NGMEP, CC-BY 4.0 Instituto Geográfico Nacional.
IGN_MUNICIPIOS_URL = (
    "https://www.ign.es/resources/ane/Informacion_Geografica_Destacada/"
    "IGN_INFOGEO_MUNICIPIOS.xlsx"
)
COBERTURA_URL = (
    "https://digital.gob.es/content/dam/portal-mtdfp/avance-digital/"
    "telecomunicacion-e-infraestructuras-digitales/areas_interes/banda-ancha/"
    "cobertura/documents/Cobertura_BA_Espa%C3%B1a_2021-2025_MUN_PROV_CCAA_Nacional_datosgob_DEF.xlsx"
)
IDEE_COLLECTIONS = "https://api-features.idee.es/collections"

# Municipios de la Mancomunidad de Interés General de Servicios Sierra Norte (CAM).
SIERRA_NORTE = frozenset("""
    28001 28003 28016 28020 28021 28024 28027 28028 28029 28030 28034
    28039 28062 28063 28064 28069 28070 28071 28076 28078 28088 28094
    28097 28107 28112 28114 28117 28118 28120 28121 28124 28126 28138
    28143 28151 28153 28158 28168 28169 28182 28901 28902
""".split())

class SourceError(RuntimeError):
    """Una fuente no pudo proporcionar los datos esperados."""


def _download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "ReHabitar-P1/1.0"})
    try:
        with urlopen(request, timeout=float(os.getenv("P1_HTTP_TIMEOUT", "30"))) as response:
            return response.read()
    except OSError as exc:
        source = urlsplit(url).netloc
        raise SourceError(f"No se pudo consultar {source}: {exc}") from exc


def _open_workbook(url: str, file: str | None):
    content = Path(file).read_bytes() if file else _download(url)
    return load_workbook(BytesIO(content), read_only=True, data_only=True, keep_links=False)


def fetch_municipios_ign_api() -> list[dict]:
    """Lee la publicación municipal del IGN derivada del NGMEP."""
    book = _open_workbook(IGN_MUNICIPIOS_URL, os.getenv("P1_IGN_FILE"))
    municipios = {}
    try:
        rows = book["IGN_INFOGEO_MUNICIPIOS"].values
        headers = next(rows)
        code_col, name_col, map_col = (
            headers.index(label) for label in ("Identificador", "Nombre", "Ver en mapa")
        )
        for row in rows:
            codigo = str(row[code_col]).strip()
            if not re.fullmatch(r"28[0-9]{3}", codigo):
                continue
            nombre = str(row[name_col] or "").strip()
            query = parse_qs(urlsplit(row[map_col] or "").query)
            try:
                longitud, latitud = map(float, query["center"][0].split(","))
            except (KeyError, ValueError) as exc:
                raise SourceError(f"El IGN no publicó coordenadas válidas para {codigo}.") from exc
            if not nombre or not (-180 <= longitud <= 180 and -90 <= latitud <= 90):
                raise SourceError(f"Registro municipal del IGN inválido para {codigo}.")
            if codigo in municipios:
                raise SourceError(f"Código municipal duplicado en el IGN: {codigo}.")
            municipios[codigo] = {
                "codigo_ine": codigo,
                "nombre": nombre,
                "provincia": "Madrid",
                "comarca": "Sierra Norte" if codigo in SIERRA_NORTE else "Sin clasificar",
                "latitud": latitud,
                "longitud": longitud,
            }
    finally:
        book.close()
    if not municipios:
        raise SourceError("El catálogo del IGN no contiene municipios de Madrid.")
    return [municipios[codigo] for codigo in sorted(municipios)]


def _percentage(value, codigo: str) -> float:
    # La hoja expresa proporciones y contiene desviaciones numéricas mínimas de 1.
    if not isinstance(value, (int, float)) or not -0.00001 <= value <= 1.00001:
        raise SourceError(f"Cobertura municipal no disponible para {codigo}.")
    return round(max(0, min(1, value)) * 100, 2)


@lru_cache(maxsize=1)
def _read_coverage(file: str | None) -> dict[str, tuple[object, object]]:
    book = _open_workbook(COBERTURA_URL, file)
    try:
        rows = book["Municipio_%hogar"].values
        headers = [" ".join(str(cell).split()) for cell in next(rows)]
        code_col, fiber_col, mobile_col = (
            headers.index(label) for label in ("CMUN", "FTTH (junio 2025)", "4G (junio 2025)")
        )
        return {
            str(row[code_col]): (row[fiber_col], row[mobile_col])
            for row in rows if re.fullmatch(r"28[0-9]{3}", str(row[code_col]))
        }
    finally:
        book.close()


def get_coverage(codigo_ine: str) -> tuple[float, float]:
    coverage = _read_coverage(os.getenv("P1_COBERTURA_FILE"))
    try:
        fiber, mobile = coverage[codigo_ine]
    except KeyError as exc:
        raise SourceError(f"SETELECO no tiene cobertura publicada para {codigo_ine}.") from exc
    return _percentage(fiber, codigo_ine), _percentage(mobile, codigo_ine)


def _ide_lines(collection: str, filters: dict[str, str], latitud: float, longitud: float) -> str:
    for radius_km in (1, 5, 15):
        lat_delta = radius_km / 110.5
        lon_delta = radius_km / (111.3 * cos(radians(latitud)))
        bounds = (longitud - lon_delta, latitud - lat_delta, longitud + lon_delta, latitud + lat_delta)
        params = {"bbox": ",".join(map(str, bounds)), "limit": 1000, "f": "json", **filters}
        url = f"{IDEE_COLLECTIONS}/{collection}/items?{urlencode(params)}"
        lines = []
        while url:
            payload = json.loads(_download(url))
            if payload.get("type") != "FeatureCollection":
                raise SourceError(f"Respuesta geográfica no válida para {collection}.")
            for feature in payload["features"]:
                geometry = feature.get("geometry") or {}
                if geometry.get("type") == "LineString":
                    lines.append(geometry["coordinates"])
                elif geometry.get("type") == "MultiLineString":
                    lines.extend(geometry["coordinates"])
            url = next(
                (link["href"] for link in payload.get("links", []) if link["rel"] == "next"),
                None,
            )
        if lines:
            return json.dumps({"type": "MultiLineString", "coordinates": lines})
    raise SourceError(f"El IGN no devolvió líneas de {collection} en el área de búsqueda.")


def get_infrastructure_lines(latitud: float, longitud: float) -> tuple[str, str]:
    """Devuelve tramos pavimentados y cursos naturales permanentes del IGN."""
    return (
        _ide_lines(
            "roadlink", {"surfacecategory": "paved", "fictitious": "false"}, latitud, longitud
        ),
        _ide_lines(
            "watercourse", {"persistd": "Permanente", "tipo_cursod": "Curso natural"},
            latitud, longitud,
        ),
    )
