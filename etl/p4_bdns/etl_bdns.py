#!/usr/bin/env python3
"""
Módulo ETL P4 - API de la Base de Datos Nacional de Subvenciones (BDNS / SNPSAP)
Responsable: Desarrollador P4

Objetivo:
Conectarse a la API REST pública del portal SNPSAP / BDNS
(`https://www.infosubvenciones.es/bdnstrans/api/...`) para extraer las convocatorias
de subvenciones con alcance en la Comunidad de Madrid, almacenarlas en `convocatorias`
y aplicar las reglas de asignación territorial en `convocatoria_municipio`.

Flujo (Extract → Transform → Load):

  1. EXTRACT
     a) Búsqueda paginada:  GET /convocatorias/busqueda?vpd=GE&regiones=<id>&fechaDesde=dd/mm/aaaa
        Devuelve un resumen (número, descripción, órgano nivel1/2/3, fecha de recepción).
        Región 26 = "ES30 - COMUNIDAD DE MADRID", región 27 = "ES300 - Madrid" (provincia).
     b) Prefiltro sobre el resumen (sin pedir nada más a la API):
        - AUTONOMICA solo si el órgano es la COMUNIDAD DE MADRID; ESTADO siempre;
          LOCAL solo si el órgano es uno de nuestros municipios; el resto se descarta.
        - Palabras clave del dominio (rural, municipios, habitantes, vivienda...) configurables.
        - Tope BDNS_MAX_DETALLES de detalles a pedir (la BDNS avisa de que limita el acceso abusivo).
     c) Detalle de cada convocatoria seleccionada: GET /convocatorias?numConv=XXXX&vpd=GE
     d) Caché en memoria RAM (respaldo si la API cae dentro del mismo proceso).

  2. TRANSFORM (normalizar_detalle)
     - Fechas ISO; si la BDNS no publica fechaInicio/FinSolicitud, se interpretan los textos
       libres `textInicio` / `textFin` ("HASTA 30 DE SEPTIEMBRE DE 2026").
     - abierta = campo `abierto` de la BDNS Y fin de plazo no vencido.
     - poblacion_max_objetivo: umbral "menos de / hasta N habitantes" extraído del texto.

  3. LOAD
     - upsert en `convocatorias` (ON CONFLICT (codigo_bdns) DO UPDATE).
     - Reglas de asignación por municipio (asignar_convocatorias), por orden de prioridad:
         R1 organo_local      → la convoca el propio ayuntamiento del municipio, o una ayuda estatal/autonómica
                                 va dirigida a ese ayuntamiento ("Subvención al Ayuntamiento de X para ...").
         R2 umbral_poblacion  → exige < N habitantes y el municipio (padrón INE, P2) está por debajo.
         R3 region_completa   → autonómica de la Comunidad de Madrid o estatal, sin restricciones.
     - upsert en `convocatoria_municipio` (ON CONFLICT (codigo_ine, codigo_bdns) DO UPDATE)
       y `municipios.hidratado = TRUE`.

Ejecución aislada:
    python etl/p4_bdns/etl_bdns.py                       # todos los municipios de la BD
    python etl/p4_bdns/etl_bdns.py 28070 28078           # solo esos municipios
    python etl/p4_bdns/etl_bdns.py --dry-run --nombres "La Hiruela,Madarcos"   # sin BD: descarga y muestra
"""

from __future__ import annotations

import argparse
import copy
import os
import re
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Optional

import requests

# =============================================================================
# Configuración (variables de entorno con valores por defecto)
# =============================================================================

BDNS_API_URL = os.getenv("BDNS_API_URL", "https://www.infosubvenciones.es/bdnstrans/api/convocatorias")
BDNS_PORTAL_URL = "https://www.infosubvenciones.es/bdnstrans/GE/es/convocatorias/{codigo}"

# Regiones BDNS: 26 = ES30 Comunidad de Madrid, 27 = ES300 Madrid (provincia). Ver GET /api/regiones?vpd=GE
BDNS_REGIONES = [int(r) for r in os.getenv("BDNS_REGIONES", "26,27").split(",") if r.strip()]
BDNS_MESES_ATRAS = int(os.getenv("BDNS_MESES_ATRAS", "12"))
BDNS_PAGE_SIZE = int(os.getenv("BDNS_PAGE_SIZE", "50"))
BDNS_MAX_PAGINAS = int(os.getenv("BDNS_MAX_PAGINAS", "40"))
BDNS_MAX_DETALLES = int(os.getenv("BDNS_MAX_DETALLES", "150"))
BDNS_PAUSA_SEG = float(os.getenv("BDNS_PAUSA_SEG", "0.3"))          # cortesía entre peticiones
BDNS_TIMEOUT = float(os.getenv("BDNS_TIMEOUT", "20"))
BDNS_CACHE_HORAS = float(os.getenv("BDNS_CACHE_HORAS", "24"))        # reutiliza la última descarga en RAM

# Caché en memoria RAM (sin ficheros locales en disco)
_BDNS_MEM_CACHE: Optional[dict] = None

# Palabras clave del dominio (reto demográfico / medio rural). Vacío o "*" desactiva el filtro.
_PALABRAS_CLAVE_DEFECTO = (
    "rural,municipio,habitantes,despobla,reto demografico,vivienda,camino,emprend,autonom,"
    "agrari,agricol,ganad,forestal,pyme,empleo,entidades locales,ayuntamiento,sierra,comercio,"
    "rehabilit,digital,conectividad,banda ancha,transporte,infraestructura,turismo"
)
BDNS_PALABRAS_CLAVE_RAW = os.getenv("BDNS_PALABRAS_CLAVE", _PALABRAS_CLAVE_DEFECTO)

REGLA_ORGANO_LOCAL = "organo_local"
REGLA_UMBRAL_POBLACION = "umbral_poblacion"
REGLA_REGION_COMPLETA = "region_completa"

COMUNIDAD_MADRID = "COMUNIDAD DE MADRID"

_MESES = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6, "JULIO": 7,
    "AGOSTO": 8, "SEPTIEMBRE": 9, "SETIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12,
}


def log(msg: str) -> None:
    print(f"[ETL P4-BDNS] {msg}", flush=True)


# =============================================================================
# Conexión a PostgreSQL (mismo criterio que P2: DATABASE_URL_SYNC o variables POSTGRES_*)
# =============================================================================

def get_db_connection():
    """
    Crea y devuelve una conexión `psycopg2` a PostgreSQL.
    Usa DATABASE_URL_SYNC si existe (docker-compose la define); si no, las variables POSTGRES_*.
    Desde el propio PC (fuera de Docker) POSTGRES_HOST debe valer `localhost`.
    """
    import psycopg2  # import diferido: el modo --dry-run y las pruebas unitarias no lo necesitan

    url = os.getenv("DATABASE_URL_SYNC")
    if url:
        return psycopg2.connect(url)
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "rehabitar"),
        password=os.getenv("POSTGRES_PASSWORD", "rehabitar_pwd"),
        dbname=os.getenv("POSTGRES_DB", "rehabitar_db"),
    )


# =============================================================================
# TRANSFORM: utilidades puras de normalización (sin red ni BD → fáciles de probar)
# =============================================================================

def normalizar_texto(valor: Any) -> str:
    """Mayúsculas, sin tildes, sin signos de puntuación y con espacios simples."""
    if valor is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(c for c in texto if not unicodedata.combining(c)).upper()
    texto = re.sub(r"[^A-Z0-9 ]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def normalizar_nombre_municipio(nombre: Any) -> str:
    """
    Normaliza nombres de municipio para poder compararlos entre fuentes:
    'Hiruela, La' (INE) == 'HIRUELA (LA)' == 'La Hiruela' == 'LA HIRUELA' (BDNS).
    """
    if nombre is None:
        return ""
    bruto = str(nombre).strip()
    # Artículo pospuesto: "Hiruela, La" o "Hiruela (La)"
    m = re.match(r"^(.*?)\s*(?:,\s*|\(\s*)(la|el|los|las)\s*\)?\s*$", bruto, flags=re.IGNORECASE)
    if m:
        bruto = f"{m.group(2)} {m.group(1)}"
    return normalizar_texto(bruto)


def _municipio_de_organo_local(nivel2: Any, nivel3: Any) -> set[str]:
    """Nombres de municipio candidatos para una convocatoria LOCAL (nivel2 = municipio, nivel3 = 'AYUNTAMIENTO DE X')."""
    candidatos = set()
    if nivel2:
        candidatos.add(normalizar_nombre_municipio(nivel2))
    n3 = normalizar_texto(nivel3)
    if n3.startswith("AYUNTAMIENTO DEL "):
        candidatos.add(normalizar_nombre_municipio("EL " + n3[len("AYUNTAMIENTO DEL "):]))
    elif n3.startswith("AYUNTAMIENTO DE "):
        candidatos.add(normalizar_nombre_municipio(n3[len("AYUNTAMIENTO DE "):]))
    candidatos.discard("")
    return candidatos


# Palabras que cierran el nombre de un municipio en "AYUNTAMIENTO DE <nombre> PARA ..."
_FIN_NOMBRE = {"PARA", "POR", "EN", "CON", "A", "Y", "E", "QUE", "SOBRE", "DESTINADA", "DESTINADO", "AL", "CORRESPONDIENTE"}


def municipios_destinatarios(descripcion: Any) -> set[str]:
    """
    Municipios concretos a los que va dirigida una convocatoria según su descripción, p. ej.
    'Subvención al Ayuntamiento de Colmenar Viejo para ...' (BDNS 933369) → {'COLMENAR VIEJO'}.
    'Ayudas a los ayuntamientos de la Comunidad' (plural) no nombra ninguno → set().
    """
    palabras = normalizar_texto(descripcion).split()
    encontrados = set()
    for i in range(len(palabras) - 2):
        if palabras[i] != "AYUNTAMIENTO" or palabras[i + 1] not in ("DE", "DEL"):
            continue
        nombre = ["EL"] if palabras[i + 1] == "DEL" else []
        for palabra in palabras[i + 2:i + 8]:
            if palabra in _FIN_NOMBRE or palabra.isdigit():
                break
            nombre.append(palabra)
        if nombre and nombre != ["EL"]:
            encontrados.add(" ".join(nombre))
    return encontrados


def _nombre_coincide(nombre_norm: str, destinatarios: set[str]) -> bool:
    """'LA HIRUELA' coincide con 'LA HIRUELA' y con 'LA HIRUELA MADRID' (texto que sigue al nombre)."""
    return any(d == nombre_norm or d.startswith(nombre_norm + " ") for d in destinatarios)


def parse_fecha_iso(valor: Any) -> Optional[date]:
    """'2026-07-23' (o '2026-07-23T00:00:00') → date. None si no es una fecha ISO."""
    if not valor:
        return None
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_fecha_texto(texto: Any) -> Optional[date]:
    """
    Interpreta el plazo en texto libre de la BDNS (`textInicio` / `textFin`):
      'HASTA 30 DE SEPTIEMBRE DE 2026' → 2026-09-30
      'DESDE 1 DE OCTUBRE DE 2025'     → 2025-10-01
      '15/11/2026' o '15-11-2026'      → 2026-11-15
    Textos sin fecha concreta ('15 DÍAS HÁBILES DESDE LA PUBLICACIÓN') → None.
    """
    if not texto:
        return None
    m = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b", str(texto))
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    m = re.search(r"\b(\d{1,2}) DE ([A-Z]+) DE (\d{4})\b", normalizar_texto(texto))
    if m and m.group(2) in _MESES:
        try:
            return date(int(m.group(3)), _MESES[m.group(2)], int(m.group(1)))
        except ValueError:
            return None
    return None


# Tras normalizar_texto, "20.000" queda como "20 000"; por eso los miles admiten espacio.
_RE_UMBRAL = re.compile(
    r"(?:MENOS DE|MENOR(?:ES)? DE|INFERIOR(?:ES)? A|NO SUPERIOR(?:ES)? A|"
    r"QUE NO (?:SUPEREN?|EXCEDAN?)|HASTA)\s+(?:LOS\s+)?"
    r"(\d{1,3}(?: \d{3})+|\d+)\s*(?:HAB[A-Z]*|HB)\b"
)


def extraer_umbral_poblacion(*textos: Any) -> Optional[int]:
    """
    Busca un umbral de población en los textos, por orden (el primero que lo tenga gana):
      'CAMINOS RURALES MUNICIP DE MENOS DE 20.000 HB'          → 20000
      'municipios ... hasta 20000 habitantes'                  → 20000
      'población inferior a 5.000 habitantes'                  → 5000
    Devuelve None si ningún texto menciona un umbral.
    """
    for texto in textos:
        m = _RE_UMBRAL.search(normalizar_texto(texto))
        if m:
            valor = int(m.group(1).replace(" ", ""))
            if 0 < valor < 10_000_000:
                return valor
    return None


def _truncar(valor: Any, longitud: int) -> Optional[str]:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto[:longitud] if texto else None


def palabras_clave() -> list[str]:
    raw = (BDNS_PALABRAS_CLAVE_RAW or "").strip()
    if raw in ("", "*"):
        return []
    return [normalizar_texto(p) for p in raw.split(",") if p.strip()]


def es_relevante_resumen(
    resumen: dict, nombres_municipios_norm: set[str], claves: Optional[list[str]] = None
) -> bool:
    """
    Prefiltro sobre el resultado de la búsqueda (antes de pedir el detalle):
      - LOCAL      → solo si el órgano es uno de nuestros municipios (no se exigen palabras clave).
      - AUTONOMICA → solo la Comunidad de Madrid, y con alguna palabra clave del dominio.
      - ESTADO     → con alguna palabra clave del dominio.
      - Dirigida a un ayuntamiento concreto que no es de los nuestros → descartada.
      - Resto (OTROS, otras autonomías) → descartado.
    """
    claves = palabras_clave() if claves is None else claves
    nivel1 = normalizar_texto(resumen.get("nivel1"))
    if nivel1 == "LOCAL":
        return bool(_municipio_de_organo_local(resumen.get("nivel2"), resumen.get("nivel3")) & nombres_municipios_norm)
    if nivel1 == "AUTONOMICA":
        if normalizar_texto(resumen.get("nivel2")) != COMUNIDAD_MADRID:
            return False
    elif nivel1 != "ESTADO":
        return False
    destinatarios = municipios_destinatarios(resumen.get("descripcion"))
    if destinatarios:
        return any(_nombre_coincide(n, destinatarios) for n in nombres_municipios_norm)
    if not claves:
        return True
    descripcion = normalizar_texto(resumen.get("descripcion"))
    return any(clave in descripcion for clave in claves)


def normalizar_detalle(detalle: dict, hoy: Optional[date] = None) -> Optional[dict]:
    """
    Convierte el JSON de detalle de la BDNS al formato unificado de la tabla `convocatorias`.
    Devuelve None si el registro no trae código o descripción.
    """
    hoy = hoy or date.today()
    codigo = detalle.get("codigoBDNS") or detalle.get("numeroConvocatoria")
    descripcion = (detalle.get("descripcion") or "").strip()
    if not codigo or not descripcion:
        return None

    organo = detalle.get("organo") or {}
    nivel1 = _truncar(organo.get("nivel1") or detalle.get("nivel1"), 150) or "DESCONOCIDO"

    inicio = parse_fecha_iso(detalle.get("fechaInicioSolicitud")) or parse_fecha_texto(detalle.get("textInicio"))
    fin = parse_fecha_iso(detalle.get("fechaFinSolicitud")) or parse_fecha_texto(detalle.get("textFin"))

    flag_abierto = detalle.get("abierto")
    if flag_abierto is None:
        abierta = fin is not None and fin >= hoy
    else:
        abierta = bool(flag_abierto) and (fin is None or fin >= hoy)

    beneficiarios = [
        (b.get("descripcion") or "").strip()
        for b in (detalle.get("tiposBeneficiarios") or [])
        if isinstance(b, dict) and b.get("descripcion")
    ]

    try:
        presupuesto = max(float(detalle.get("presupuestoTotal") or 0), 0.0)
    except (TypeError, ValueError):
        presupuesto = 0.0

    return {
        "codigo_bdns": str(codigo).strip(),
        "descripcion": descripcion,
        "organo_nivel1": nivel1,
        "organo_nivel2": _truncar(organo.get("nivel2") or detalle.get("nivel2"), 150),
        "organo_nivel3": _truncar(organo.get("nivel3") or detalle.get("nivel3"), 150),
        "fecha_recepcion": parse_fecha_iso(detalle.get("fechaRecepcion")) or hoy,
        "inicio_solicitud": inicio,
        "fin_solicitud": fin,
        "abierta": abierta,
        "presupuesto_total": round(presupuesto, 2),
        "tipo_beneficiario": _truncar("; ".join(beneficiarios), 150),
        "finalidad": _truncar(detalle.get("descripcionFinalidad"), 150),
        # El título manda; si no menciona umbral se mira el texto de las bases reguladoras
        "poblacion_max_objetivo": extraer_umbral_poblacion(descripcion, detalle.get("descripcionBasesReguladoras")),
        "url_bases": detalle.get("urlBasesReguladoras") or BDNS_PORTAL_URL.format(codigo=codigo),
    }


# =============================================================================
# Reglas de asignación convocatoria → municipio (función pura)
# =============================================================================

def regla_para_municipio(convocatoria: dict, nombre_municipio_norm: str, poblacion: Optional[int]) -> Optional[str]:
    """
    Decide si una convocatoria aplica a un municipio y por qué regla (prioridad R1 > R2 > R3).
    Devuelve 'organo_local' | 'umbral_poblacion' | 'region_completa' o None si no aplica.
    """
    nivel1 = normalizar_texto(convocatoria.get("organo_nivel1"))

    # R1: convocatorias de entidades locales → solo al propio municipio (nunca a los demás)
    if nivel1 == "LOCAL":
        candidatos = _municipio_de_organo_local(convocatoria.get("organo_nivel2"), convocatoria.get("organo_nivel3"))
        return REGLA_ORGANO_LOCAL if nombre_municipio_norm in candidatos else None

    es_regional = nivel1 == "ESTADO" or (
        nivel1 == "AUTONOMICA" and normalizar_texto(convocatoria.get("organo_nivel2")) == COMUNIDAD_MADRID
    )
    if not es_regional:
        return None

    # R1 (variante): ayuda estatal/autonómica dirigida a un ayuntamiento concreto
    # ("Subvención al Ayuntamiento de Colmenar Viejo para ...") → solo a ese municipio, nunca a toda la región
    destinatarios = municipios_destinatarios(convocatoria.get("descripcion"))
    if destinatarios:
        return REGLA_ORGANO_LOCAL if _nombre_coincide(nombre_municipio_norm, destinatarios) else None

    # R2: umbral de población → necesita el padrón; sin dato no se puede afirmar que aplique
    umbral = convocatoria.get("poblacion_max_objetivo")
    if umbral:
        return REGLA_UMBRAL_POBLACION if poblacion is not None and poblacion < int(umbral) else None

    # R3: ámbito autonómico/estatal sin restricciones
    return REGLA_REGION_COMPLETA


def asignar_convocatorias(
    nombre_municipio: str, poblacion: Optional[int], convocatorias: Iterable[dict]
) -> list[tuple[str, str]]:
    """Lista de (codigo_bdns, regla_asignacion) que aplican al municipio."""
    nombre_norm = normalizar_nombre_municipio(nombre_municipio)
    asignaciones = []
    for conv in convocatorias:
        regla = regla_para_municipio(conv, nombre_norm, poblacion)
        if regla:
            asignaciones.append((conv["codigo_bdns"], regla))
    return asignaciones


# =============================================================================
# EXTRACT: cliente HTTP de la API BDNS + caché en memoria RAM
# =============================================================================

def _nueva_sesion() -> requests.Session:
    sesion = requests.Session()
    sesion.headers.update({"Accept": "application/json", "User-Agent": "ReHabitar-PoC/1.0 (proyecto academico)"})
    return sesion


def _get_json(sesion: requests.Session, url: str, params: dict) -> Any:
    """GET con un reintento ante timeout, error de conexión o 5xx (los 4xx no se reintentan)."""
    ultimo_error: Optional[Exception] = None
    for intento in range(2):
        try:
            resp = sesion.get(url, params=params, timeout=BDNS_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            ultimo_error = exc
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and status < 500:
                break
            if intento == 0:
                time.sleep(max(BDNS_PAUSA_SEG, 1.0))
    raise ultimo_error  # type: ignore[misc]


def buscar_convocatorias(sesion: requests.Session, fecha_desde: date) -> list[dict]:
    """Recorre las páginas de la búsqueda para cada región y devuelve los resúmenes sin duplicados."""
    vistos: dict[str, dict] = {}
    for region in BDNS_REGIONES:
        pagina = 0
        while pagina < BDNS_MAX_PAGINAS:
            datos = _get_json(
                sesion,
                f"{BDNS_API_URL}/busqueda",
                {
                    "vpd": "GE",
                    "regiones": region,
                    "fechaDesde": fecha_desde.strftime("%d/%m/%Y"),
                    "page": pagina,
                    "pageSize": BDNS_PAGE_SIZE,
                },
            )
            for resumen in datos.get("content") or []:
                numero = str(resumen.get("numeroConvocatoria") or "").strip()
                if numero and numero not in vistos:
                    vistos[numero] = resumen
            total_paginas = int(datos.get("totalPages") or 0)
            if datos.get("last", True) or pagina + 1 >= total_paginas:
                break
            pagina += 1
            time.sleep(BDNS_PAUSA_SEG)
    return list(vistos.values())


def obtener_detalle(sesion: requests.Session, numero: str) -> dict:
    return _get_json(sesion, BDNS_API_URL, {"numConv": numero, "vpd": "GE"})


def cargar_cache() -> Optional[dict]:
    return copy.deepcopy(_BDNS_MEM_CACHE) if _BDNS_MEM_CACHE is not None else None


def guardar_cache(payload: dict) -> None:
    global _BDNS_MEM_CACHE
    _BDNS_MEM_CACHE = copy.deepcopy(payload)


def _cache_vigente(payload: Optional[dict]) -> bool:
    if not payload or not payload.get("detalles"):
        return False
    try:
        extraido = datetime.fromisoformat(payload["fecha_extraccion"])
    except (KeyError, TypeError, ValueError):
        return False
    return datetime.now(timezone.utc) - extraido < timedelta(hours=BDNS_CACHE_HORAS)


def fetch_bdns_convocatorias_api(
    nombres_municipios: Optional[Iterable[str]] = None,
    force_refresh: bool = False,
    sesion: Optional[requests.Session] = None,
    hoy: Optional[date] = None,
) -> list[dict]:
    """
    Descarga de la API BDNS las convocatorias con alcance en la Comunidad de Madrid y las devuelve
    normalizadas (campos de la Sección 7.1.5 + `finalidad`).

    - `nombres_municipios`: municipios del sistema; se usan para no descartar las convocatorias
      LOCALES de sus ayuntamientos.
    - Si hay una descarga en memoria de menos de BDNS_CACHE_HORAS y no se fuerza, se reutiliza.
    - Si la API falla, se usa la última copia guardada (aunque sea antigua); si no hay, devuelve [].
    """
    hoy = hoy or date.today()
    cache = cargar_cache()
    if not force_refresh and _cache_vigente(cache):
        log(f"Usando descarga reciente de {cache['fecha_extraccion']} ({len(cache['detalles'])} convocatorias).")
        return _normalizar_lista(cache["detalles"], hoy)

    nombres_norm = {normalizar_nombre_municipio(n) for n in (nombres_municipios or [])} - {""}
    sesion = sesion or _nueva_sesion()
    fecha_desde = hoy - timedelta(days=round(BDNS_MESES_ATRAS * 30.44))

    try:
        resumenes = buscar_convocatorias(sesion, fecha_desde)
    except (requests.RequestException, ValueError) as exc:
        log(f"AVISO: la búsqueda en la API BDNS ha fallado ({exc}).")
        if cache and cache.get("detalles"):
            log(f"Usando la copia guardada de {cache.get('fecha_extraccion')} como respaldo.")
            return _normalizar_lista(cache["detalles"], hoy)
        log("No hay copia de respaldo: se continúa sin convocatorias.")
        return []

    claves = palabras_clave()
    seleccion = [r for r in resumenes if es_relevante_resumen(r, nombres_norm, claves)]
    # Las convocatorias locales de nuestros municipios son las más específicas: van primero
    seleccion.sort(key=lambda r: normalizar_texto(r.get("nivel1")) != "LOCAL")
    omitidas = max(len(seleccion) - BDNS_MAX_DETALLES, 0)
    seleccion = seleccion[:BDNS_MAX_DETALLES]
    log(
        f"Búsqueda: {len(resumenes)} convocatorias en regiones {BDNS_REGIONES} desde {fecha_desde:%d/%m/%Y}; "
        f"{len(seleccion)} seleccionadas para detalle"
        + (f" ({omitidas} omitidas por el tope BDNS_MAX_DETALLES)" if omitidas else "")
        + "."
    )

    detalles = []
    for resumen in seleccion:
        numero = str(resumen.get("numeroConvocatoria"))
        try:
            detalles.append(obtener_detalle(sesion, numero))
        except (requests.RequestException, ValueError) as exc:
            log(f"AVISO: detalle {numero} no disponible ({exc}); se omite.")
        time.sleep(BDNS_PAUSA_SEG)

    guardar_cache(
        {
            "fuente": "BDNS / SNPSAP - https://www.infosubvenciones.es/bdnstrans/api",
            "fecha_extraccion": datetime.now(timezone.utc).isoformat(),
            "parametros": {
                "regiones": BDNS_REGIONES,
                "fecha_desde": fecha_desde.isoformat(),
                "palabras_clave": claves,
                "max_detalles": BDNS_MAX_DETALLES,
                "municipios": sorted(nombres_norm),
            },
            "total_busqueda": len(resumenes),
            "resumenes_seleccionados": seleccion,
            "detalles": detalles,
        }
    )
    return _normalizar_lista(detalles, hoy)


def _normalizar_lista(detalles: Iterable[dict], hoy: date) -> list[dict]:
    resultado: dict[str, dict] = {}
    for detalle in detalles:
        fila = normalizar_detalle(detalle, hoy=hoy)
        if fila:
            resultado[fila["codigo_bdns"]] = fila
    return list(resultado.values())


# =============================================================================
# LOAD: PostgreSQL
# =============================================================================

_COLUMNAS_CONVOCATORIA = (
    "codigo_bdns", "descripcion", "organo_nivel1", "organo_nivel2", "organo_nivel3",
    "fecha_recepcion", "inicio_solicitud", "fin_solicitud", "abierta", "presupuesto_total",
    "tipo_beneficiario", "finalidad", "poblacion_max_objetivo", "url_bases",
)

_SQL_UPSERT_CONVOCATORIA = f"""
    INSERT INTO convocatorias ({", ".join(_COLUMNAS_CONVOCATORIA)}, fecha_extraccion)
    VALUES ({", ".join(["%s"] * len(_COLUMNAS_CONVOCATORIA))}, CURRENT_TIMESTAMP)
    ON CONFLICT (codigo_bdns) DO UPDATE SET
        {", ".join(f"{c} = EXCLUDED.{c}" for c in _COLUMNAS_CONVOCATORIA[1:])},
        fecha_extraccion = CURRENT_TIMESTAMP
"""

_SQL_UPSERT_ASIGNACION = """
    INSERT INTO convocatoria_municipio (codigo_ine, codigo_bdns, regla_asignacion, fecha_asignacion)
    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
    ON CONFLICT (codigo_ine, codigo_bdns) DO UPDATE SET
        regla_asignacion = EXCLUDED.regla_asignacion,
        fecha_asignacion = CURRENT_TIMESTAMP
"""


def upsert_convocatorias(conn, convocatorias: list[dict]) -> int:
    """Inserta o actualiza las convocatorias normalizadas. No hace commit (lo decide quien llama)."""
    if not convocatorias:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            _SQL_UPSERT_CONVOCATORIA,
            [tuple(c[col] for col in _COLUMNAS_CONVOCATORIA) for c in convocatorias],
        )
    return len(convocatorias)


def _tabla_existe(cur, tabla: str) -> bool:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{tabla}",))
    return bool(cur.fetchone()[0])


def _cargar_municipios(conn) -> dict[str, str]:
    """{codigo_ine: nombre} de la tabla `municipios` (de P1). Vacío si la tabla aún no existe."""
    with conn.cursor() as cur:
        if not _tabla_existe(cur, "municipios"):
            log("AVISO: la tabla `municipios` (P1) no existe todavía.")
            return {}
        cur.execute("SELECT codigo_ine, nombre FROM municipios ORDER BY codigo_ine")
        return {codigo: nombre for codigo, nombre in cur.fetchall()}


def _poblacion_actual(cur, codigo_ine: str) -> Optional[int]:
    """Población del último año disponible en `demografia_anual` (de P2). None si no hay dato."""
    if not _tabla_existe(cur, "demografia_anual"):
        return None
    cur.execute(
        "SELECT poblacion FROM demografia_anual WHERE codigo_ine = %s ORDER BY anio DESC LIMIT 1",
        (codigo_ine,),
    )
    fila = cur.fetchone()
    return int(fila[0]) if fila else None


def _cargar_convocatorias_bd(cur) -> list[dict]:
    cur.execute(
        "SELECT codigo_bdns, descripcion, organo_nivel1, organo_nivel2, organo_nivel3, poblacion_max_objetivo "
        "FROM convocatorias"
    )
    columnas = [d[0] for d in cur.description]
    return [dict(zip(columnas, fila)) for fila in cur.fetchall()]


def ingest_bdns_for_municipio(codigo_ine: str, conn=None) -> int:
    """
    Fase 2 (bajo demanda): asigna al municipio `codigo_ine` las convocatorias de la tabla `convocatorias`.
      1. Lee el nombre del municipio y su última población (`demografia_anual`).
      2. Aplica las reglas R1/R2/R3 (`asignar_convocatorias`).
      3. Sustituye sus filas en `convocatoria_municipio` (upsert + borra las que ya no aplican).
      4. Marca `municipios.hidratado = TRUE` y `fecha_hidratacion = CURRENT_TIMESTAMP`.
    Devuelve el número de convocatorias asignadas. Si se pasa `conn`, el commit lo hace quien llama.
    """
    propia = conn is None
    if propia:
        conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT nombre FROM municipios WHERE codigo_ine = %s", (codigo_ine,))
            fila = cur.fetchone()
            if not fila:
                log(f"AVISO: {codigo_ine} no existe en `municipios` (¿se ejecutó P1?). Se omite.")
                return 0
            nombre = fila[0]
            poblacion = _poblacion_actual(cur, codigo_ine)
            convocatorias = _cargar_convocatorias_bd(cur)
            if poblacion is None and any(c.get("poblacion_max_objetivo") for c in convocatorias):
                log(f"AVISO: sin padrón para {codigo_ine} ({nombre}); no se aplica la regla de umbral de población.")

            asignaciones = asignar_convocatorias(nombre, poblacion, convocatorias)
            codigos = [codigo for codigo, _ in asignaciones]
            cur.execute(
                "DELETE FROM convocatoria_municipio WHERE codigo_ine = %s AND NOT (codigo_bdns = ANY(%s::varchar[]))",
                (codigo_ine, codigos),
            )
            if asignaciones:
                cur.executemany(
                    _SQL_UPSERT_ASIGNACION, [(codigo_ine, codigo, regla) for codigo, regla in asignaciones]
                )
            cur.execute(
                "UPDATE municipios SET hidratado = TRUE, fecha_hidratacion = CURRENT_TIMESTAMP WHERE codigo_ine = %s",
                (codigo_ine,),
            )
        if propia:
            conn.commit()
        return len(asignaciones)
    except Exception:
        if propia:
            conn.rollback()
        raise
    finally:
        if propia:
            conn.close()


def run_etl_p4(target_codes: list[str] | None = None, force_refresh: bool = False) -> str:
    """
    Fase 1 (carga inicial):
      1. Descarga las convocatorias de la API BDNS y las guarda en `convocatorias`.
      2. Las asigna a los municipios `target_codes` (por defecto, a todos los de la tabla `municipios`).
    """
    conn = get_db_connection()
    try:
        municipios = _cargar_municipios(conn)
        convocatorias = fetch_bdns_convocatorias_api(municipios.values(), force_refresh=force_refresh)
        guardadas = upsert_convocatorias(conn, convocatorias)
        conn.commit()

        codigos = list(target_codes) if target_codes is not None else list(municipios)
        asignadas = 0
        for codigo in codigos:
            asignadas += ingest_bdns_for_municipio(codigo, conn=conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    mensaje = (
        "[ETL P4-BDNS] Asignando convocatorias rurales desde API BDNS... OK. "
        f"({guardadas} convocatorias, {asignadas} asignaciones en {len(codigos)} municipios)"
    )
    print(mensaje, flush=True)
    return mensaje


def _main() -> None:
    parser = argparse.ArgumentParser(description="ETL P4: convocatorias BDNS → PostgreSQL")
    parser.add_argument("codigos", nargs="*", help="Códigos INE a asignar (por defecto, todos los de la BD)")
    parser.add_argument("--force-refresh", action="store_true", help="Ignora la caché reciente en memoria")
    parser.add_argument("--dry-run", action="store_true", help="Solo descarga y muestra; no toca la BD")
    parser.add_argument("--nombres", default="", help="(dry-run) Municipios separados por comas")
    args = parser.parse_args()

    if args.dry_run:
        nombres = [n for n in args.nombres.split(",") if n.strip()]
        convocatorias = fetch_bdns_convocatorias_api(nombres, force_refresh=args.force_refresh)
        abiertas = [c for c in convocatorias if c["abierta"]]
        log(f"{len(convocatorias)} convocatorias normalizadas ({len(abiertas)} abiertas) desde API BDNS.")
        for c in convocatorias[:10]:
            log(
                f"  {c['codigo_bdns']} | {c['organo_nivel1']} | fin={c['fin_solicitud']} | "
                f"umbral={c['poblacion_max_objetivo']} | {c['descripcion'][:70]}"
            )
        return
    run_etl_p4(target_codes=args.codigos or None, force_refresh=args.force_refresh)


if __name__ == "__main__":
    _main()
