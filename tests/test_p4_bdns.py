"""
Suite de pruebas del Módulo P4: BDNS (ETL `etl/p4_bdns/etl_bdns.py`, servicio `backend/services/p4_grants_service.py`,
modelos/esquemas y endpoint `GET /api/convocatorias`).

Capas:
  1. Unidad (sin red ni BD): normalización, fechas en texto, umbral de población, prefiltro y reglas R1/R2/R3.
  2. HTTP simulado: paginación, prefiltro, tope de detalles, copia en data/raw y respaldo si la API cae.
  3. Modelos ORM y esquema Pydantic.
  4. Endpoint FastAPI con la sesión de BD sustituida.
  5. Integración con PostgreSQL/PostGIS real (solo si existe TEST_DATABASE_URL).
  6. Prueba en vivo contra la API BDNS (solo si RUN_LIVE_BDNS=1).

Ejecución recomendada (Docker, levanta una BD de prueba desechable):
    docker compose -f tests/docker-compose.p4-test.yml run --rm tests
    docker compose -f tests/docker-compose.p4-test.yml down -v

Los municipios y el padrón de las pruebas de integración son DATOS DE PRUEBA (aproximados o inventados);
las fixtures `tests/fixtures/bdns/*.json` son respuestas reales de la API BDNS capturadas el 20/11/2026.
"""

import copy
import importlib.util
import json
import os
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import requests

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(TESTS_DIR, ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
ETL_DIR = os.path.join(REPO_ROOT, "etl")
FIXTURES_DIR = os.path.join(TESTS_DIR, "fixtures")
for ruta in (BACKEND_DIR, ETL_DIR):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

from p4_bdns import etl_bdns  # noqa: E402

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
RUN_LIVE = os.getenv("RUN_LIVE_BDNS") == "1"
ORGANO_921084 = "CONSEJERÍA DE PRESIDENCIA, JUSTICIA Y ADMINISTRACIÓN LOCAL"


def cargar_fixture(nombre: str) -> dict:
    with open(os.path.join(FIXTURES_DIR, "bdns", nombre), encoding="utf-8") as fh:
        return json.load(fh)


def detalle_sintetico(
    codigo, descripcion, nivel1, nivel2=None, nivel3=None, abierto=True, fin=None,
    presupuesto=10000.0, finalidad="Infraestructuras", bases=None,
):
    """Detalle con la misma forma que la API BDNS (datos inventados para casos que la fixture real no cubre)."""
    return {
        "codigoBDNS": codigo,
        "descripcion": descripcion,
        "organo": {"nivel1": nivel1, "nivel2": nivel2, "nivel3": nivel3},
        "fechaRecepcion": "2026-10-01",
        "abierto": abierto,
        "fechaInicioSolicitud": None,
        "fechaFinSolicitud": fin,
        "textInicio": None,
        "textFin": None,
        "presupuestoTotal": presupuesto,
        "tiposBeneficiarios": [{"descripcion": "PERSONAS FÍSICAS QUE NO DESARROLLAN ACTIVIDAD ECONÓMICA"}],
        "descripcionFinalidad": finalidad,
        "descripcionBasesReguladoras": None,
        "urlBasesReguladoras": bases,
    }


# =============================================================================
# 1. UNIDAD: normalización y transformación
# =============================================================================

class TestNormalizacion(unittest.TestCase):

    def test_normalizar_texto_quita_tildes_y_puntuacion(self):
        self.assertEqual(etl_bdns.normalizar_texto("  Consejería de  Presidencia, Justicia "),
                         "CONSEJERIA DE PRESIDENCIA JUSTICIA")
        self.assertEqual(etl_bdns.normalizar_texto(None), "")

    def test_nombre_municipio_equivalente_entre_fuentes(self):
        for variante in ("Hiruela, La", "HIRUELA (LA)", "La Hiruela", "LA HIRUELA", "la  hiruela"):
            self.assertEqual(etl_bdns.normalizar_nombre_municipio(variante), "LA HIRUELA", variante)
        self.assertEqual(etl_bdns.normalizar_nombre_municipio("Buitrago del Lozoya"), "BUITRAGO DEL LOZOYA")

    def test_parse_fecha_texto(self):
        self.assertEqual(etl_bdns.parse_fecha_texto("HASTA 30 DE SEPTIEMBRE DE 2026"), date(2026, 9, 30))
        self.assertEqual(etl_bdns.parse_fecha_texto("DESDE 1 DE OCTUBRE DE 2025"), date(2025, 10, 1))
        self.assertEqual(etl_bdns.parse_fecha_texto("Hasta el 15/11/2026"), date(2026, 11, 15))
        self.assertIsNone(etl_bdns.parse_fecha_texto("15 DÍAS HÁBILES DESDE LA PUBLICACIÓN"))
        self.assertIsNone(etl_bdns.parse_fecha_texto("31 DE FEBRERO DE 2026"))  # fecha imposible
        self.assertIsNone(etl_bdns.parse_fecha_texto(None))

    def test_extraer_umbral_poblacion(self):
        casos = {
            "ORDEN DE DISP CRÉDITO 2026 CAMINOS RURALES MUNICIP DE MENOS DE 20.000 HB": 20000,
            "caminos rurales de los municipios ... hasta 20000 habitantes": 20000,
            "Ayudas a municipios con población inferior a 5.000 habitantes": 5000,
            "Entidades locales que no superen los 1.000 habitantes": 1000,
            "Subvenciones para actividades deportivas 2026": None,
            "Premios de 20.000 euros para startups": None,
        }
        for texto, esperado in casos.items():
            self.assertEqual(etl_bdns.extraer_umbral_poblacion(texto), esperado, texto)

    def test_umbral_se_busca_en_bases_si_el_titulo_no_lo_tiene(self):
        self.assertEqual(
            etl_bdns.extraer_umbral_poblacion("Ayudas caminos", "municipios de menos de 10.000 habit."), 10000
        )

    def test_normalizar_detalle_real_921084(self):
        fila = etl_bdns.normalizar_detalle(cargar_fixture("detalle_921084.json"), hoy=date(2026, 8, 1))
        self.assertEqual(fila["codigo_bdns"], "921084")
        self.assertEqual(fila["organo_nivel1"], "AUTONOMICA")
        self.assertEqual(fila["organo_nivel2"], "COMUNIDAD DE MADRID")
        self.assertEqual(fila["fecha_recepcion"], date(2026, 7, 23))
        # La BDNS no publica fechaFinSolicitud: se interpreta textFin "HASTA 30 DE SEPTIEMBRE DE 2026"
        self.assertEqual(fila["inicio_solicitud"], date(2025, 10, 1))
        self.assertEqual(fila["fin_solicitud"], date(2026, 9, 30))
        self.assertTrue(fila["abierta"])
        self.assertEqual(fila["poblacion_max_objetivo"], 20000)  # del título, no de las bases (10.000)
        self.assertAlmostEqual(fila["presupuesto_total"], 935762.86)
        self.assertEqual(fila["finalidad"], "Infraestructuras")
        self.assertTrue(fila["url_bases"].startswith("https://www.bocm.es/"))

    def test_plazo_vencido_cierra_aunque_bdns_diga_abierto(self):
        fila = etl_bdns.normalizar_detalle(cargar_fixture("detalle_921084.json"), hoy=date(2026, 11, 20))
        self.assertFalse(fila["abierta"])

    def test_normalizar_detalle_casos_limite(self):
        sin_flag = detalle_sintetico("1", "Ayuda", "ESTADO", abierto=None)
        self.assertFalse(etl_bdns.normalizar_detalle(sin_flag)["abierta"])  # sin flag ni fecha: no se afirma
        self.assertIsNone(etl_bdns.normalizar_detalle({"descripcion": "sin código"}))
        raro = detalle_sintetico("2", "Ayuda", "ESTADO", nivel2="M" * 300, presupuesto="no-numero")
        fila = etl_bdns.normalizar_detalle(raro)
        self.assertEqual(fila["presupuesto_total"], 0.0)
        self.assertEqual(len(fila["organo_nivel2"]), 150)
        self.assertIn("/convocatorias/2", fila["url_bases"])  # sin bases → enlace al portal BDNS


# =============================================================================
# 1b. UNIDAD: prefiltro y reglas de asignación
# =============================================================================

class TestPrefiltro(unittest.TestCase):
    NOMBRES = {"LA HIRUELA", "MADARCOS"}

    def test_local_solo_de_nuestros_municipios(self):
        hiruela = {"nivel1": "LOCAL", "nivel2": "HIRUELA (LA)", "descripcion": "Fiestas patronales"}
        self.assertTrue(etl_bdns.es_relevante_resumen(hiruela, self.NOMBRES, ["RURAL"]))
        mostoles_real = cargar_fixture("busqueda_madrid_pagina0.json")["content"][0]
        self.assertEqual(mostoles_real["nivel2"], "MÓSTOLES")
        self.assertFalse(etl_bdns.es_relevante_resumen(mostoles_real, self.NOMBRES, []))

    def test_autonomica_solo_comunidad_de_madrid_y_con_palabras_clave(self):
        madrid = {"nivel1": "AUTONOMICA", "nivel2": "COMUNIDAD DE MADRID", "descripcion": "Caminos rurales"}
        valencia = {"nivel1": "AUTONOMICA", "nivel2": "COMUNITAT VALENCIANA", "descripcion": "Caminos rurales"}
        madrid_otro_tema = {"nivel1": "AUTONOMICA", "nivel2": "COMUNIDAD DE MADRID", "descripcion": "Premio literario"}
        claves = etl_bdns.palabras_clave()
        self.assertTrue(etl_bdns.es_relevante_resumen(madrid, set(), claves))
        self.assertFalse(etl_bdns.es_relevante_resumen(valencia, set(), claves))
        self.assertFalse(etl_bdns.es_relevante_resumen(madrid_otro_tema, set(), claves))
        self.assertTrue(etl_bdns.es_relevante_resumen(madrid_otro_tema, set(), []))  # filtro desactivado

    def test_dirigida_a_ayuntamiento_ajeno_no_se_descarga(self):
        colmenar = {"nivel1": "ESTADO", "nivel2": "MINISTERIO DEL INTERIOR",
                    "descripcion": "Subvención al Ayuntamiento de Colmenar Viejo para la realización de actuaciones"}
        self.assertFalse(etl_bdns.es_relevante_resumen(colmenar, self.NOMBRES, []))
        self.assertTrue(etl_bdns.es_relevante_resumen(colmenar, self.NOMBRES | {"COLMENAR VIEJO"}, []))

    def test_otros_niveles_descartados(self):
        self.assertFalse(etl_bdns.es_relevante_resumen({"nivel1": "OTROS", "descripcion": "rural"}, set(), []))


class TestReglasAsignacion(unittest.TestCase):

    def setUp(self):
        hoy = date(2026, 8, 1)
        sinteticos = [
            detalle_sintetico("L1", "Ayudas natalidad", "LOCAL", "HIRUELA (LA)", "AYUNTAMIENTO DE LA HIRUELA"),
            detalle_sintetico("L2", "Asociaciones", "LOCAL", "MÓSTOLES", "AYUNTAMIENTO DE MÓSTOLES"),
            detalle_sintetico("E1", "Programa de vivienda rural", "ESTADO", "MINISTERIO DE VIVIENDA"),
            detalle_sintetico("V1", "Caminos rurales", "AUTONOMICA", "COMUNITAT VALENCIANA"),
        ]
        self.catalogo = [etl_bdns.normalizar_detalle(cargar_fixture("detalle_921084.json"), hoy=hoy)]
        self.catalogo += [etl_bdns.normalizar_detalle(d, hoy=hoy) for d in sinteticos]

    def asignar(self, nombre, poblacion):
        return dict(etl_bdns.asignar_convocatorias(nombre, poblacion, self.catalogo))

    def test_municipio_pequeno_con_ayuntamiento_propio(self):
        self.assertEqual(self.asignar("Hiruela, La", 60),
                         {"L1": "organo_local", "921084": "umbral_poblacion", "E1": "region_completa"})

    def test_municipio_pequeno_sin_ayudas_locales(self):
        self.assertEqual(self.asignar("Madarcos", 47), {"921084": "umbral_poblacion", "E1": "region_completa"})

    def test_municipio_grande_no_recibe_ayuda_con_umbral(self):
        self.assertEqual(self.asignar("Madrid", 3_400_000), {"E1": "region_completa"})

    def test_umbral_es_estricto(self):
        self.assertNotIn("921084", self.asignar("Madarcos", 20000))
        self.assertIn("921084", self.asignar("Madarcos", 19999))

    def test_sin_padron_no_se_aplica_umbral(self):
        self.assertEqual(self.asignar("Buitrago del Lozoya", None), {"E1": "region_completa"})

    def test_local_de_otro_municipio_nunca_se_asigna(self):
        for nombre in ("Madarcos", "Hiruela, La", "Madrid"):
            self.assertNotIn("L2", self.asignar(nombre, 100))
        self.assertEqual(self.asignar("Móstoles", 210000).get("L2"), "organo_local")

    def test_ayuda_estatal_dirigida_a_un_ayuntamiento_concreto(self):
        # Descripción real de la BDNS 933369 (ESTADO): no debe aplicarse a toda la región
        self.catalogo.append(etl_bdns.normalizar_detalle(detalle_sintetico(
            "933369", "Subvención al Ayuntamiento de Colmenar Viejo para la realización de actuaciones",
            "ESTADO", "MINISTERIO DEL INTERIOR")))
        self.assertNotIn("933369", self.asignar("Madarcos", 47))
        self.assertEqual(self.asignar("Colmenar Viejo", 50000).get("933369"), "organo_local")

    def test_municipios_destinatarios(self):
        f = etl_bdns.municipios_destinatarios
        self.assertEqual(f("Subvención al Ayuntamiento de Colmenar Viejo para obras"), {"COLMENAR VIEJO"})
        self.assertEqual(f("Concesión al AYUNTAMIENTO DE LA HIRUELA, 2026"), {"LA HIRUELA"})
        self.assertEqual(f("Convenio con el Ayuntamiento del Molar"), {"EL MOLAR"})
        self.assertEqual(f("Ayudas a los ayuntamientos de la Comunidad de Madrid"), set())  # plural: genérica
        self.assertEqual(f("Caminos rurales municipios de menos de 20.000 hab"), set())


# =============================================================================
# 2. HTTP SIMULADO: extracción, prefiltro, tope, copia en data/raw y respaldo
# =============================================================================

class _RespuestaFalsa:
    def __init__(self, datos, status=200):
        self._datos, self.status_code = datos, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def json(self):
        return copy.deepcopy(self._datos)


class _SesionFalsa:
    """Imita requests.Session: 2 páginas de búsqueda y un detalle por convocatoria."""

    PAGINAS = [
        {"content": [
            {"numeroConvocatoria": "A", "nivel1": "AUTONOMICA", "nivel2": "COMUNIDAD DE MADRID",
             "descripcion": "Caminos rurales municipios"},
            {"numeroConvocatoria": "B", "nivel1": "LOCAL", "nivel2": "MÓSTOLES", "descripcion": "rural"},
            {"numeroConvocatoria": "C", "nivel1": "ESTADO", "nivel2": "MINISTERIO", "descripcion": "Vivienda"},
        ], "last": False, "totalPages": 2},
        {"content": [
            {"numeroConvocatoria": "D", "nivel1": "LOCAL", "nivel2": "HIRUELA (LA)", "descripcion": "Fiestas"},
            {"numeroConvocatoria": "E", "nivel1": "OTROS", "nivel2": "FUNDACIÓN", "descripcion": "rural"},
            {"numeroConvocatoria": "A", "nivel1": "AUTONOMICA", "nivel2": "COMUNIDAD DE MADRID",
             "descripcion": "duplicada"},
        ], "last": True, "totalPages": 2},
    ]
    DETALLES = {"A": ("AUTONOMICA", "COMUNIDAD DE MADRID"), "C": ("ESTADO", "MINISTERIO"), "D": ("LOCAL", "HIRUELA (LA)")}

    def __init__(self, fallar=False):
        self.llamadas = []
        self.fallar = fallar

    def get(self, url, params=None, timeout=None):
        self.llamadas.append((url, dict(params or {})))
        if self.fallar:
            raise requests.ConnectionError("API caída")
        if url.endswith("/busqueda"):
            return _RespuestaFalsa(self.PAGINAS[params["page"]])
        numero = params["numConv"]
        nivel1, nivel2 = self.DETALLES[numero]
        return _RespuestaFalsa(detalle_sintetico(numero, f"Convocatoria {numero}", nivel1, nivel2))

    def detalles_pedidos(self):
        return [p["numConv"] for _, p in self.llamadas if "numConv" in p]


class TestExtraccionHTTP(unittest.TestCase):

    def setUp(self):
        etl_bdns._BDNS_MEM_CACHE = None
        self.parches = [
            patch.object(etl_bdns, "BDNS_PAUSA_SEG", 0),
            patch.object(etl_bdns, "BDNS_REGIONES", [26]),
            patch.object(etl_bdns, "BDNS_MAX_DETALLES", 150),
            patch.object(etl_bdns.time, "sleep", lambda *_: None),
        ]
        for p in self.parches:
            p.start()

    def tearDown(self):
        for p in self.parches:
            p.stop()
        etl_bdns._BDNS_MEM_CACHE = None

    def test_pagina_filtra_y_pide_solo_detalles_relevantes(self):
        sesion = _SesionFalsa()
        resultado = etl_bdns.fetch_bdns_convocatorias_api(["La Hiruela"], force_refresh=True, sesion=sesion)
        busquedas = [p for url, p in sesion.llamadas if url.endswith("/busqueda")]
        self.assertEqual([p["page"] for p in busquedas], [0, 1])
        self.assertEqual(busquedas[0]["regiones"], 26)
        # D (local propio) primero; B (local ajeno) y E (OTROS) descartados; A deduplicada
        self.assertEqual(sesion.detalles_pedidos(), ["D", "A", "C"])
        self.assertEqual(sorted(c["codigo_bdns"] for c in resultado), ["A", "C", "D"])

    def test_guarda_copia_en_memoria(self):
        etl_bdns.fetch_bdns_convocatorias_api(["La Hiruela"], force_refresh=True, sesion=_SesionFalsa())
        copia = etl_bdns.cargar_cache()
        self.assertIsNotNone(copia)
        self.assertEqual(copia["total_busqueda"], 5)
        self.assertEqual(len(copia["detalles"]), 3)
        self.assertIn("fecha_extraccion", copia)

    def test_tope_de_detalles(self):
        sesion = _SesionFalsa()
        with patch.object(etl_bdns, "BDNS_MAX_DETALLES", 1):
            etl_bdns.fetch_bdns_convocatorias_api(["La Hiruela"], force_refresh=True, sesion=sesion)
        self.assertEqual(sesion.detalles_pedidos(), ["D"])

    def test_copia_reciente_evita_llamar_a_la_api(self):
        etl_bdns.fetch_bdns_convocatorias_api(["La Hiruela"], force_refresh=True, sesion=_SesionFalsa())
        sesion = _SesionFalsa()
        resultado = etl_bdns.fetch_bdns_convocatorias_api(["La Hiruela"], sesion=sesion)
        self.assertEqual(sesion.llamadas, [])
        self.assertEqual(len(resultado), 3)

    def test_api_caida_usa_copia_antigua(self):
        etl_bdns.guardar_cache({
            "fecha_extraccion": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "detalles": [cargar_fixture("detalle_921084.json")],
        })
        resultado = etl_bdns.fetch_bdns_convocatorias_api([], sesion=_SesionFalsa(fallar=True))
        self.assertEqual([c["codigo_bdns"] for c in resultado], ["921084"])

    def test_api_caida_sin_copia_devuelve_lista_vacia(self):
        self.assertEqual(etl_bdns.fetch_bdns_convocatorias_api([], sesion=_SesionFalsa(fallar=True)), [])


# =============================================================================
# 3. MODELOS ORM Y ESQUEMA PYDANTIC
# =============================================================================

HAS_SQLALCHEMY = importlib.util.find_spec("sqlalchemy") is not None
HAS_PYDANTIC = importlib.util.find_spec("pydantic") is not None
HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None and HAS_SQLALCHEMY


class TestModelosYEsquemas(unittest.TestCase):

    @unittest.skipUnless(HAS_SQLALCHEMY, "Requiere sqlalchemy instalado (ejecutar en Docker)")
    def test_modelos_orm(self):
        from sqlalchemy.orm import configure_mappers
        from models.domain import Convocatoria, ConvocatoriaMunicipio

        configure_mappers()
        columnas = set(Convocatoria.__table__.columns.keys())
        self.assertTrue({"codigo_bdns", "finalidad", "poblacion_max_objetivo", "organo_convocante"} <= columnas)
        self.assertIsNotNone(Convocatoria.__table__.c.organo_convocante.computed)
        self.assertEqual([c.name for c in ConvocatoriaMunicipio.__table__.primary_key.columns],
                         ["codigo_ine", "codigo_bdns"])

    @unittest.skipUnless(HAS_PYDANTIC, "Requiere pydantic instalado (ejecutar en Docker)")
    def test_esquema_acepta_fila_normalizada(self):
        from pydantic import ValidationError
        from schemas import ConvocatoriaMunicipioItemSchema

        fila = etl_bdns.normalizar_detalle(cargar_fixture("detalle_921084.json"), hoy=date(2026, 8, 1))
        item = ConvocatoriaMunicipioItemSchema(
            **fila, organo_convocante=fila["organo_nivel3"], regla_asignacion="umbral_poblacion")
        self.assertEqual(item.model_dump(mode="json")["fin_solicitud"], "2026-09-30")
        with self.assertRaises(ValidationError):
            ConvocatoriaMunicipioItemSchema(**{**fila, "presupuesto_total": -1}, organo_convocante="X")


# =============================================================================
# 4. ENDPOINT FastAPI (sesión de BD sustituida, servicio simulado)
# =============================================================================

@unittest.skipUnless(HAS_FASTAPI, "Requiere fastapi y sqlalchemy instalados (ejecutar en Docker)")
class TestEndpointConvocatorias(unittest.TestCase):

    def test_get_convocatorias_por_municipio(self):
        from fastapi.testclient import TestClient
        import main
        from core.database import get_db

        async def bd_falsa():
            yield None

        fila = etl_bdns.normalizar_detalle(cargar_fixture("detalle_921084.json"), hoy=date(2026, 8, 1))
        respuesta = [{**fila, "organo_convocante": fila["organo_nivel3"], "regla_asignacion": "umbral_poblacion"}]

        main.app.dependency_overrides[get_db] = bd_falsa
        try:
            with patch.object(main, "get_convocatorias", AsyncMock(return_value=respuesta)) as servicio:
                resp = TestClient(main.app).get("/api/convocatorias",
                                                params={"codigo_ine": "28078", "categoria": "infra"})
        finally:
            main.app.dependency_overrides.clear()

        self.assertEqual(resp.status_code, 200, resp.text)
        servicio.assert_awaited_once_with(None, codigo_ine="28078", categoria="infra", solo_abiertas=True)
        cuerpo = resp.json()
        self.assertEqual(cuerpo[0]["codigo_bdns"], "921084")
        self.assertEqual(cuerpo[0]["regla_asignacion"], "umbral_poblacion")
        self.assertEqual(cuerpo[0]["fin_solicitud"], "2026-09-30")


# =============================================================================
# 5. INTEGRACIÓN con PostgreSQL + PostGIS (TEST_DATABASE_URL)
# =============================================================================

MUNICIPIOS_PRUEBA = [  # (codigo_ine, nombre, lat, lon, poblacion_reciente o None) — DATOS DE PRUEBA
    ("28078", "Madarcos", 41.0487, -3.5828, 47),
    ("28070", "Hiruela, La", 41.0767, -3.4511, 60),
    ("28027", "Buitrago del Lozoya", 40.9931, -3.6384, None),  # sin padrón: no aplica la regla de umbral
    ("28079", "Madrid", 40.4168, -3.7038, 3_400_000),
]


def catalogo_prueba(hoy: date) -> list[dict]:
    """921084 real (con el plazo movido al futuro para no depender del día) + casos sintéticos."""
    real = etl_bdns.normalizar_detalle(cargar_fixture("detalle_921084.json"), hoy=hoy)
    real.update(fin_solicitud=hoy + timedelta(days=60), abierta=True)
    sinteticos = [
        detalle_sintetico("L1", "Ayudas natalidad", "LOCAL", "HIRUELA (LA)", "AYUNTAMIENTO DE LA HIRUELA",
                          fin=(hoy + timedelta(days=30)).isoformat(), finalidad="Bienestar social"),
        detalle_sintetico("L2", "Asociaciones", "LOCAL", "MÓSTOLES", "AYUNTAMIENTO DE MÓSTOLES"),
        detalle_sintetico("E1", "Programa vivienda rural", "ESTADO", "MINISTERIO DE VIVIENDA",
                          fin=(hoy + timedelta(days=90)).isoformat(), finalidad="Vivienda", presupuesto=5e6),
        detalle_sintetico("E2", "Programa cerrado", "ESTADO", "MINISTERIO DE VIVIENDA",
                          fin=(hoy - timedelta(days=10)).isoformat(), finalidad="Vivienda"),
    ]
    return [real] + [etl_bdns.normalizar_detalle(d, hoy=hoy) for d in sinteticos]


def preparar_esquema(conn) -> None:
    """Crea las tablas: schema.sql completo si ya incluye P1/P2; si no, tablas mínimas de prueba + sección P4."""
    import psycopg2

    with open(os.path.join(REPO_ROOT, "db", "schema.sql"), encoding="utf-8") as fh:
        schema = fh.read()
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    conn.commit()
    try:
        with conn.cursor() as cur:
            cur.execute(schema)
        conn.commit()
    except psycopg2.Error:
        conn.rollback()
        with open(os.path.join(FIXTURES_DIR, "p4_schema_stub.sql"), encoding="utf-8") as fh:
            stub = fh.read()
        with conn.cursor() as cur:
            cur.execute(stub)
            cur.execute(schema[schema.index("-- 5. AYUDAS Y SUBVENCIONES"):])
        conn.commit()


def cargar_datos_prueba(conn, hoy: date) -> None:
    """Vacía las tablas y carga los municipios, el padrón y el catálogo de prueba."""
    with conn.cursor() as cur:
        cur.execute("TRUNCATE convocatoria_municipio, convocatorias, demografia_anual, municipios CASCADE")
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'municipios'")
        columnas = {r[0] for r in cur.fetchall()}
        for codigo, nombre, lat, lon, poblacion in MUNICIPIOS_PRUEBA:
            if "geom" in columnas:  # tabla real de P1
                cur.execute(
                    "INSERT INTO municipios (codigo_ine, nombre, latitud, longitud, geom) "
                    "VALUES (%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))",
                    (codigo, nombre, lat, lon, lon, lat))
            else:
                cur.execute("INSERT INTO municipios (codigo_ine, nombre) VALUES (%s, %s)", (codigo, nombre))
            if poblacion is not None:
                cur.executemany(
                    "INSERT INTO demografia_anual (codigo_ine, anio, poblacion) VALUES (%s, %s, %s)",
                    [(codigo, 2015, poblacion + 4), (codigo, 2025, poblacion)])
    etl_bdns.upsert_convocatorias(conn, catalogo_prueba(hoy))
    conn.commit()


@unittest.skipUnless(TEST_DATABASE_URL, "Define TEST_DATABASE_URL para las pruebas con PostgreSQL")
class TestIntegracionBD(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import psycopg2

        cls.conn = psycopg2.connect(TEST_DATABASE_URL)
        preparar_esquema(cls.conn)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def setUp(self):
        self.hoy = date.today()
        cargar_datos_prueba(self.conn, self.hoy)

    def _asignaciones(self, codigo_ine):
        with self.conn.cursor() as cur:
            cur.execute("SELECT codigo_bdns, regla_asignacion FROM convocatoria_municipio WHERE codigo_ine = %s",
                        (codigo_ine,))
            return dict(cur.fetchall())

    def test_columnas_bd_coinciden_con_modelo_orm(self):
        from models.domain import Convocatoria, ConvocatoriaMunicipio

        for modelo in (Convocatoria, ConvocatoriaMunicipio):
            with self.conn.cursor() as cur:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                            (modelo.__tablename__,))
                self.assertEqual({r[0] for r in cur.fetchall()}, set(modelo.__table__.columns.keys()))

    def test_upsert_es_idempotente_y_columna_generada(self):
        etl_bdns.upsert_convocatorias(self.conn, catalogo_prueba(self.hoy))
        self.conn.commit()
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM convocatorias")
            self.assertEqual(cur.fetchone()[0], 5)
            cur.execute("SELECT organo_convocante, poblacion_max_objetivo FROM convocatorias WHERE codigo_bdns='921084'")
            self.assertEqual(cur.fetchone(), (ORGANO_921084, 20000))

    def test_reglas_aplicadas_en_bd(self):
        for codigo, *_ in MUNICIPIOS_PRUEBA:
            etl_bdns.ingest_bdns_for_municipio(codigo, conn=self.conn)
        self.conn.commit()
        regionales = {"E1": "region_completa", "E2": "region_completa"}
        self.assertEqual(self._asignaciones("28070"),
                         {"L1": "organo_local", "921084": "umbral_poblacion", **regionales})
        self.assertEqual(self._asignaciones("28078"), {"921084": "umbral_poblacion", **regionales})
        self.assertEqual(self._asignaciones("28027"), regionales)
        self.assertEqual(self._asignaciones("28079"), regionales)
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM municipios WHERE hidratado AND fecha_hidratacion IS NOT NULL")
            self.assertEqual(cur.fetchone()[0], 4)

    def test_reingesta_idempotente_y_borra_asignaciones_obsoletas(self):
        self.assertEqual(etl_bdns.ingest_bdns_for_municipio("28078", conn=self.conn), 3)
        self.assertEqual(etl_bdns.ingest_bdns_for_municipio("28078", conn=self.conn), 3)
        with self.conn.cursor() as cur:  # la convocatoria pasa a exigir < 10 habitantes
            cur.execute("UPDATE convocatorias SET poblacion_max_objetivo = 10 WHERE codigo_bdns = '921084'")
        etl_bdns.ingest_bdns_for_municipio("28078", conn=self.conn)
        self.conn.commit()
        self.assertNotIn("921084", self._asignaciones("28078"))

    def test_municipio_inexistente(self):
        self.assertEqual(etl_bdns.ingest_bdns_for_municipio("99999", conn=self.conn), 0)

    def test_run_etl_p4_completo_con_api_simulada(self):
        with patch.dict(os.environ, {"DATABASE_URL_SYNC": TEST_DATABASE_URL}), \
             patch.object(etl_bdns, "fetch_bdns_convocatorias_api", return_value=catalogo_prueba(self.hoy)):
            mensaje = etl_bdns.run_etl_p4(target_codes=["28070", "28078"])
        self.assertIn("OK", mensaje)
        self.assertEqual(len(self._asignaciones("28070")), 4)
        self.assertEqual(self._asignaciones("28027"), {})  # no estaba entre los códigos pedidos


@unittest.skipUnless(TEST_DATABASE_URL, "Define TEST_DATABASE_URL para las pruebas con PostgreSQL")
class TestServicioConsulta4(unittest.IsolatedAsyncioTestCase):
    """Servicio asíncrono (SQLAlchemy + asyncpg) contra la misma BD de prueba."""

    async def asyncSetUp(self):
        import psycopg2
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from services import p4_grants_service

        conn = psycopg2.connect(TEST_DATABASE_URL)
        try:
            preparar_esquema(conn)
            cargar_datos_prueba(conn, date.today())
            for codigo, *_ in MUNICIPIOS_PRUEBA:
                etl_bdns.ingest_bdns_for_municipio(codigo, conn=conn)
            conn.commit()
        finally:
            conn.close()

        self.engine = create_async_engine(TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
        self.session = AsyncSession(self.engine)
        self.servicio = p4_grants_service

    async def asyncTearDown(self):
        await self.session.close()
        await self.engine.dispose()

    async def test_consulta4_abiertas_del_municipio(self):
        from schemas import ConvocatoriaMunicipioItemSchema

        filas = await self.servicio.get_convocatorias(self.session, codigo_ine="28070")
        self.assertEqual([f["codigo_bdns"] for f in filas], ["L1", "921084", "E1"])  # por fin de plazo; E2 cerrada
        self.assertEqual(filas[0]["regla_asignacion"], "organo_local")
        self.assertEqual(filas[1]["organo_convocante"], ORGANO_921084)
        for fila in filas:
            ConvocatoriaMunicipioItemSchema(**fila)  # el resultado encaja en el esquema del endpoint

    async def test_incluir_cerradas_y_filtrar_por_categoria(self):
        todas = await self.servicio.get_convocatorias(self.session, codigo_ine="28070", solo_abiertas=False)
        self.assertIn("E2", [f["codigo_bdns"] for f in todas])
        vivienda = await self.servicio.get_convocatorias(self.session, categoria="vivienda", solo_abiertas=False)
        self.assertEqual(sorted(f["codigo_bdns"] for f in vivienda), ["E1", "E2"])
        self.assertTrue(all(f["regla_asignacion"] is None for f in vivienda))

    async def test_resumen_por_municipio(self):
        resumen = await self.servicio.get_grants_summary_all(self.session)
        self.assertEqual(resumen["28070"]["num_ayudas_abiertas"], 3)
        self.assertEqual(resumen["28070"]["num_ayudas_total"], 4)
        self.assertEqual(resumen["28079"]["num_ayudas_abiertas"], 1)
        self.assertEqual(await self.servicio.get_num_ayudas_abiertas(self.session, "28078"), 2)

    async def test_hidratacion_bajo_demanda(self):
        with patch.dict(os.environ, {"DATABASE_URL_SYNC": TEST_DATABASE_URL}):
            asignadas = await self.servicio.hydrate_grants_on_demand(self.session, "28078")
        self.assertEqual(asignadas, 3)


# =============================================================================
# 6. EN VIVO contra la API BDNS (opcional: RUN_LIVE_BDNS=1). Hace 1 petición.
# =============================================================================

@unittest.skipUnless(RUN_LIVE, "Define RUN_LIVE_BDNS=1 para consultar la API BDNS real")
class TestBDNSEnVivo(unittest.TestCase):

    def test_detalle_921084(self):
        fila = etl_bdns.normalizar_detalle(etl_bdns.obtener_detalle(etl_bdns._nueva_sesion(), "921084"))
        self.assertEqual(fila["codigo_bdns"], "921084")
        self.assertEqual(fila["organo_nivel2"], "COMUNIDAD DE MADRID")
        self.assertEqual(fila["poblacion_max_objetivo"], 20000)


if __name__ == "__main__":
    unittest.main()
