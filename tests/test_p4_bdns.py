"""
Suite de pruebas del Módulo P4: BDNS (ETL `etl/p4_bdns/etl_bdns.py`, servicio `backend/services/p4_grants_service.py`,
modelos/esquemas y endpoint `GET /api/convocatorias`).

Capas (todas ejecutables en local sin BD externa ni dependencias web opcionales):
  1. Unidad (sin red ni BD): normalización, fechas en texto, umbral de población, prefiltro y reglas R1/R2/R3.
  2. HTTP simulado: paginación, prefiltro, tope de detalles, caché en memoria y respaldo si la API cae.
  3. Modelos ORM y esquema de respuesta mediante inspección estática y capa de compatibilidad.
  4. Endpoint y servicio asíncrono simulados.
  5. Persistencia ETL simulada con conexión y cursor simulados.
  6. Detalle BDNS con la fixture real `detalle_921084.json` mediante sesión HTTP simulada.

Las fixtures `tests/fixtures/bdns/*.json` son respuestas reales de la API BDNS capturadas el 20/11/2026.
"""

import ast
import copy
import json
import os
import re
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

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
        self.assertIn("/convocatorias/2", fila["url_bases"])  # sin bases, enlaza al portal BDNS


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
# 3. MODELOS ORM (INSPECCIÓN ESTÁTICA + DDL) Y ESQUEMA DE RESPUESTA
# =============================================================================

def _extraer_clase_orm(ruta_modelos: str, nombre_clase: str) -> dict:
    """Inspecciona una clase ORM en `models/domain.py` mediante AST sin importar SQLAlchemy."""
    with open(ruta_modelos, encoding="utf-8") as fh:
        modulo = ast.parse(fh.read(), filename=ruta_modelos)

    for nodo in modulo.body:
        if not isinstance(nodo, ast.ClassDef) or nodo.name != nombre_clase:
            continue
        tabla = None
        columnas = {}
        for stmt in nodo.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__" and isinstance(stmt.value, ast.Constant):
                        tabla = stmt.value.value
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and isinstance(stmt.value, ast.Call):
                col = stmt.target.id
                llamada = stmt.value
                es_pk = any(
                    kw.arg == "primary_key" and isinstance(kw.value, ast.Constant) and kw.value.value is True
                    for kw in llamada.keywords
                )
                fks = []
                computada = None
                for arg in llamada.args:
                    if not isinstance(arg, ast.Call) or not isinstance(arg.func, ast.Name):
                        continue
                    if arg.func.id == "ForeignKey" and arg.args and isinstance(arg.args[0], ast.Constant):
                        ondelete = next(
                            (
                                kw.value.value
                                for kw in arg.keywords
                                if kw.arg == "ondelete" and isinstance(kw.value, ast.Constant)
                            ),
                            None,
                        )
                        fks.append((arg.args[0].value, ondelete))
                    elif arg.func.id == "Computed" and arg.args and isinstance(arg.args[0], ast.Constant):
                        persisted = next(
                            (
                                kw.value.value
                                for kw in arg.keywords
                                if kw.arg == "persisted" and isinstance(kw.value, ast.Constant)
                            ),
                            None,
                        )
                        computada = (arg.args[0].value, persisted)
                columnas[col] = {
                    "primary_key": es_pk,
                    "foreign_keys": fks,
                    "computed": computada,
                }
        return {"tablename": tabla, "columns": columnas}
    raise AssertionError(f"No se encontró la clase {nombre_clase} en {ruta_modelos}")


def _extraer_tabla_sql(ruta_schema: str, nombre_tabla: str) -> dict:
    """Extrae columnas y restricciones de una sentencia `CREATE TABLE` en `db/schema.sql`."""
    with open(ruta_schema, encoding="utf-8") as fh:
        sql = re.sub(r"--[^\n]*", "", fh.read())

    m = re.search(rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{re.escape(nombre_tabla)}\s*\(", sql, re.IGNORECASE)
    if not m:
        raise AssertionError(f"No se encontró la tabla {nombre_tabla} en {ruta_schema}")

    inicio = m.end()
    profundidad = 1
    en_comillas = False
    pos = inicio
    while pos < len(sql) and profundidad > 0:
        ch = sql[pos]
        if ch == "'":
            en_comillas = not en_comillas
        elif not en_comillas:
            if ch == "(":
                profundidad += 1
            elif ch == ")":
                profundidad -= 1
        pos += 1
    cuerpo = sql[inicio:pos - 1]

    elementos = []
    actual = []
    profundidad = 0
    en_comillas = False
    for ch in cuerpo:
        if ch == "'":
            en_comillas = not en_comillas
        elif not en_comillas:
            if ch == "(":
                profundidad += 1
            elif ch == ")":
                profundidad -= 1
            elif ch == "," and profundidad == 0:
                elementos.append("".join(actual).strip())
                actual = []
                continue
        actual.append(ch)
    if "".join(actual).strip():
        elementos.append("".join(actual).strip())

    columnas = {}
    restricciones = []
    for elem in elementos:
        if re.match(r"^(CONSTRAINT|PRIMARY\s+KEY|FOREIGN\s+KEY|CHECK|UNIQUE)\b", elem, re.IGNORECASE):
            restricciones.append(elem)
        else:
            nombre_col = elem.split()[0]
            columnas[nombre_col] = elem
    return {"body": cuerpo, "columns": columnas, "constraints": restricciones}


class TestModelosYEsquemas(unittest.TestCase):

    def test_modelos_orm_y_esquema_sql(self):
        ruta_modelos = os.path.join(BACKEND_DIR, "models", "domain.py")
        ruta_schema = os.path.join(REPO_ROOT, "db", "schema.sql")

        conv_orm = _extraer_clase_orm(ruta_modelos, "Convocatoria")
        conv_mun_orm = _extraer_clase_orm(ruta_modelos, "ConvocatoriaMunicipio")
        conv_sql = _extraer_tabla_sql(ruta_schema, "convocatorias")
        conv_mun_sql = _extraer_tabla_sql(ruta_schema, "convocatoria_municipio")

        self.assertEqual(conv_orm["tablename"], "convocatorias")
        self.assertEqual(conv_mun_orm["tablename"], "convocatoria_municipio")

        self.assertEqual(set(conv_orm["columns"].keys()), set(conv_sql["columns"].keys()))
        self.assertTrue(
            {"codigo_bdns", "finalidad", "poblacion_max_objetivo", "organo_convocante"}
            <= set(conv_orm["columns"].keys())
        )
        self.assertTrue(conv_orm["columns"]["codigo_bdns"]["primary_key"])
        self.assertEqual(
            conv_orm["columns"]["organo_convocante"]["computed"],
            ("COALESCE(organo_nivel3, organo_nivel2, organo_nivel1)", True),
        )
        self.assertIn("PRIMARY KEY", conv_sql["columns"]["codigo_bdns"].upper())
        self.assertIn("GENERATED ALWAYS AS", conv_sql["columns"]["organo_convocante"].upper())
        self.assertIn("STORED", conv_sql["columns"]["organo_convocante"].upper())

        self.assertEqual(set(conv_mun_orm["columns"].keys()), set(conv_mun_sql["columns"].keys()))
        pks_orm = [col for col, meta in conv_mun_orm["columns"].items() if meta["primary_key"]]
        self.assertEqual(pks_orm, ["codigo_ine", "codigo_bdns"])
        self.assertEqual(conv_mun_orm["columns"]["codigo_ine"]["foreign_keys"], [("municipios.codigo_ine", "CASCADE")])
        self.assertEqual(
            conv_mun_orm["columns"]["codigo_bdns"]["foreign_keys"],
            [("convocatorias.codigo_bdns", "CASCADE")],
        )
        self.assertTrue(
            any("PRIMARY KEY (codigo_ine, codigo_bdns)" in c for c in conv_mun_sql["constraints"])
        )
        self.assertIn("REFERENCES municipios (codigo_ine) ON DELETE CASCADE", conv_mun_sql["columns"]["codigo_ine"])
        self.assertIn(
            "REFERENCES convocatorias (codigo_bdns) ON DELETE CASCADE",
            conv_mun_sql["columns"]["codigo_bdns"],
        )
        for regla in ("organo_local", "umbral_poblacion", "region_completa"):
            self.assertIn(f"'{regla}'", conv_mun_sql["columns"]["regla_asignacion"])

    def test_esquema_acepta_fila_normalizada(self):
        from schemas import ConvocatoriaMunicipioItemSchema

        fila = etl_bdns.normalizar_detalle(cargar_fixture("detalle_921084.json"), hoy=date(2026, 8, 1))
        item = ConvocatoriaMunicipioItemSchema(
            **fila, organo_convocante=fila["organo_nivel3"], regla_asignacion="umbral_poblacion"
        )
        dumped = item.model_dump(mode="json")
        self.assertEqual(dumped["fin_solicitud"], "2026-09-30")
        self.assertEqual(dumped["fecha_recepcion"], "2026-07-23")
        self.assertEqual(dumped["inicio_solicitud"], "2025-10-01")
        self.assertEqual(dumped["codigo_bdns"], "921084")
        self.assertEqual(dumped["organo_convocante"], ORGANO_921084)
        self.assertEqual(dumped["regla_asignacion"], "umbral_poblacion")

        item_catalogo = ConvocatoriaMunicipioItemSchema(**fila, organo_convocante=fila["organo_nivel3"])
        self.assertIsNone(item_catalogo.regla_asignacion)
        self.assertEqual(item_catalogo.model_dump()["presupuesto_total"], 935762.86)


# =============================================================================
# 4. ENDPOINT Y SERVICIO ASÍNCRONO (simulados sin BD ni FastAPI/SQLAlchemy)
# =============================================================================

class TestEndpointConvocatorias(unittest.IsolatedAsyncioTestCase):

    @classmethod
    def setUpClass(cls):
        import main

        cls.main = main

    async def test_get_convocatorias_por_municipio(self):
        fila = etl_bdns.normalizar_detalle(cargar_fixture("detalle_921084.json"), hoy=date(2026, 8, 1))
        respuesta = [{**fila, "organo_convocante": fila["organo_nivel3"], "regla_asignacion": "umbral_poblacion"}]
        db_simulada = MagicMock()

        with patch.object(self.main, "get_convocatorias", AsyncMock(return_value=respuesta)) as servicio:
            cuerpo = await self.main.list_convocatorias(
                codigo_ine="28078",
                categoria="infra",
                solo_abiertas=True,
                abierta=None,
                db=db_simulada,
            )

        servicio.assert_awaited_once_with(db_simulada, codigo_ine="28078", categoria="infra", solo_abiertas=True)
        self.assertEqual(len(cuerpo), 1)
        self.assertEqual(cuerpo[0]["codigo_bdns"], "921084")
        self.assertEqual(cuerpo[0]["regla_asignacion"], "umbral_poblacion")
        self.assertEqual(cuerpo[0]["fin_solicitud"], date(2026, 9, 30))

    async def test_alias_abierta_sobrescribe_solo_abiertas(self):
        db_simulada = MagicMock()
        with patch.object(self.main, "get_convocatorias", AsyncMock(return_value=[])) as servicio:
            cuerpo = await self.main.list_convocatorias(
                codigo_ine=None,
                categoria="vivienda",
                solo_abiertas=True,
                abierta=False,
                db=db_simulada,
            )

        self.assertEqual(cuerpo, [])
        servicio.assert_awaited_once_with(db_simulada, codigo_ine=None, categoria="vivienda", solo_abiertas=False)


class TestServicioConsulta4(unittest.IsolatedAsyncioTestCase):
    """Pruebas del servicio asíncrono P4 con la sesión de BD simulada."""

    @classmethod
    def setUpClass(cls):
        from schemas import ConvocatoriaMunicipioItemSchema
        from services import p4_grants_service

        cls.servicio = p4_grants_service
        cls.schema_item = ConvocatoriaMunicipioItemSchema

    def _crear_sesion(self, *, mappings_all=None, scalar=None):
        resultado = MagicMock()
        resultado.mappings.return_value.all.return_value = mappings_all if mappings_all is not None else []
        resultado.scalar.return_value = scalar
        db = MagicMock()
        db.execute = AsyncMock(return_value=resultado)
        return db

    async def test_get_convocatorias_con_y_sin_filtros(self):
        fila = etl_bdns.normalizar_detalle(cargar_fixture("detalle_921084.json"), hoy=date(2026, 8, 1))
        fila_sql = {
            **fila,
            "organo_convocante": fila["organo_nivel3"],
            "presupuesto_total": Decimal("935762.86"),
            "regla_asignacion": "umbral_poblacion",
        }
        db = self._crear_sesion(mappings_all=[fila_sql])

        filas = await self.servicio.get_convocatorias(db, codigo_ine="28070", categoria=" infra ", solo_abiertas=True)
        self.assertEqual(len(filas), 1)
        self.assertIsInstance(filas[0]["presupuesto_total"], float)
        self.assertEqual(filas[0]["presupuesto_total"], 935762.86)
        self.assertEqual(
            self.schema_item(**filas[0]).model_dump(mode="json")["fin_solicitud"],
            "2026-09-30",
        )

        stmt, params = db.execute.await_args.args
        sql = getattr(stmt, "text", str(stmt))
        self.assertIn("JOIN convocatorias c ON c.codigo_bdns = cm.codigo_bdns", sql)
        self.assertIn("cm.codigo_ine = :codigo_ine", sql)
        self.assertIn("c.finalidad ILIKE :categoria", sql)
        self.assertIn("CURRENT_DATE", sql)
        self.assertEqual(params, {"codigo_ine": "28070", "categoria": "%infra%"})

        db_catalogo = self._crear_sesion(mappings_all=[{**fila_sql, "regla_asignacion": None}])
        catalogo = await self.servicio.get_convocatorias(db_catalogo, solo_abiertas=False)
        self.assertIsNone(catalogo[0]["regla_asignacion"])
        stmt_cat, params_cat = db_catalogo.execute.await_args.args
        sql_cat = getattr(stmt_cat, "text", str(stmt_cat))
        self.assertIn("FROM convocatorias c", sql_cat)
        self.assertIn("NULL::varchar AS regla_asignacion", sql_cat)
        self.assertNotIn("WHERE", sql_cat)
        self.assertEqual(params_cat, {})

    async def test_get_grants_summary_all(self):
        db = self._crear_sesion(
            mappings_all=[
                {
                    "codigo_ine": "28070",
                    "num_ayudas_abiertas": 3,
                    "num_ayudas_total": 4,
                    "presupuesto_abiertas": Decimal("5945762.86"),
                },
                {
                    "codigo_ine": "28079",
                    "num_ayudas_abiertas": 1,
                    "num_ayudas_total": 2,
                    "presupuesto_abiertas": Decimal("5000000.00"),
                },
            ]
        )

        resumen = await self.servicio.get_grants_summary_all(db)
        self.assertEqual(
            resumen,
            {
                "28070": {
                    "num_ayudas_abiertas": 3,
                    "num_ayudas_total": 4,
                    "presupuesto_abiertas": 5945762.86,
                },
                "28079": {
                    "num_ayudas_abiertas": 1,
                    "num_ayudas_total": 2,
                    "presupuesto_abiertas": 5000000.0,
                },
            },
        )
        stmt = db.execute.await_args.args[0]
        sql = getattr(stmt, "text", str(stmt))
        self.assertIn("GROUP BY cm.codigo_ine", sql)

    async def test_get_num_ayudas_abiertas(self):
        db = self._crear_sesion(scalar=2)
        total = await self.servicio.get_num_ayudas_abiertas(db, "28078")
        self.assertEqual(total, 2)
        _, params = db.execute.await_args.args
        self.assertEqual(params, {"codigo_ine": "28078"})

        db_vacio = self._crear_sesion(scalar=None)
        self.assertEqual(await self.servicio.get_num_ayudas_abiertas(db_vacio, "99999"), 0)

    async def test_hydrate_grants_on_demand(self):
        db = self._crear_sesion()
        with patch.object(self.servicio.etl_bdns, "ingest_bdns_for_municipio", return_value=3) as ingesta:
            asignadas = await self.servicio.hydrate_grants_on_demand(db, "28078")

        self.assertEqual(asignadas, 3)
        ingesta.assert_called_once_with("28078")


# =============================================================================
# 5. PERSISTENCIA ETL SIMULADA (MagicMock de conexión y cursor)
# =============================================================================

class TestPersistenciaETLSimulada(unittest.TestCase):

    @staticmethod
    def _mock_conexion():
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cur
        conn.cursor.return_value.__exit__.return_value = False
        return conn, cur

    @staticmethod
    def _convocatorias_normalizadas():
        hoy = date(2026, 8, 1)
        detalles = [
            cargar_fixture("detalle_921084.json"),
            detalle_sintetico("L1", "Ayudas natalidad", "LOCAL", "HIRUELA (LA)", "AYUNTAMIENTO DE LA HIRUELA"),
            detalle_sintetico("E1", "Programa vivienda rural", "ESTADO", "MINISTERIO DE VIVIENDA"),
            detalle_sintetico("L2", "Asociaciones", "LOCAL", "MÓSTOLES", "AYUNTAMIENTO DE MÓSTOLES"),
        ]
        return [etl_bdns.normalizar_detalle(d, hoy=hoy) for d in detalles]

    @staticmethod
    def _filas_bd_convocatorias(convocatorias):
        columnas = ("codigo_bdns", "descripcion", "organo_nivel1", "organo_nivel2", "organo_nivel3", "poblacion_max_objetivo")
        descripcion = [(col,) for col in columnas]
        filas = [tuple(c[col] for col in columnas) for c in convocatorias]
        return descripcion, filas

    def test_upsert_convocatorias(self):
        conn, cur = self._mock_conexion()
        self.assertEqual(etl_bdns.upsert_convocatorias(conn, []), 0)
        conn.cursor.assert_not_called()

        convocatorias = self._convocatorias_normalizadas()[:2]
        guardadas = etl_bdns.upsert_convocatorias(conn, convocatorias)

        self.assertEqual(guardadas, 2)
        cur.executemany.assert_called_once()
        sql, filas = cur.executemany.call_args.args
        self.assertIn("INSERT INTO convocatorias", sql)
        self.assertIn("ON CONFLICT (codigo_bdns) DO UPDATE SET", sql)
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[0][0], "921084")
        self.assertEqual(filas[1][0], "L1")
        conn.commit.assert_not_called()

    def test_ingest_bdns_for_municipio_existente(self):
        conn, cur = self._mock_conexion()
        convocatorias = self._convocatorias_normalizadas()
        desc, filas_conv = self._filas_bd_convocatorias(convocatorias)

        cur.fetchone.side_effect = [("Hiruela, La",), (True,), (60,)]
        cur.description = desc
        cur.fetchall.return_value = filas_conv

        asignadas = etl_bdns.ingest_bdns_for_municipio("28070", conn=conn)

        self.assertEqual(asignadas, 3)  # 921084 (umbral), L1 (local) y E1 (region_completa); L2 descartada
        sentencias = [(c.args[0], c.args[1] if len(c.args) > 1 else None) for c in cur.execute.call_args_list]
        self.assertTrue(
            any(
                "DELETE FROM convocatoria_municipio" in sql and params == ("28070", ["921084", "L1", "E1"])
                for sql, params in sentencias
            )
        )
        self.assertTrue(
            any(
                "UPDATE municipios SET hidratado = TRUE" in sql and params == ("28070",)
                for sql, params in sentencias
            )
        )
        cur.executemany.assert_called_once_with(
            etl_bdns._SQL_UPSERT_ASIGNACION,
            [
                ("28070", "921084", "umbral_poblacion"),
                ("28070", "L1", "organo_local"),
                ("28070", "E1", "region_completa"),
            ],
        )
        conn.commit.assert_not_called()
        conn.close.assert_not_called()

    def test_ingest_bdns_for_municipio_ausente(self):
        conn, cur = self._mock_conexion()
        cur.fetchone.return_value = None

        asignadas = etl_bdns.ingest_bdns_for_municipio("99999", conn=conn)

        self.assertEqual(asignadas, 0)
        cur.executemany.assert_not_called()
        sentencias = [c.args[0] for c in cur.execute.call_args_list]
        self.assertFalse(any("UPDATE municipios" in sql for sql in sentencias))
        self.assertFalse(any("DELETE FROM convocatoria_municipio" in sql for sql in sentencias))

    def test_run_etl_p4(self):
        conn, cur = self._mock_conexion()
        convocatorias = self._convocatorias_normalizadas()
        desc, filas_conv = self._filas_bd_convocatorias(convocatorias)

        cur.fetchone.side_effect = [
            (True,),            # to_regclass('public.municipios')
            ("Hiruela, La",),   # SELECT nombre para 28070
            (True,),            # to_regclass('public.demografia_anual') para 28070
            (60,),              # poblacion de 28070
            ("Madarcos",),      # SELECT nombre para 28078
            (True,),            # to_regclass('public.demografia_anual') para 28078
            (47,),              # poblacion de 28078
        ]
        cur.description = desc
        cur.fetchall.side_effect = [
            [("28070", "Hiruela, La"), ("28078", "Madarcos")],
            filas_conv,
            filas_conv,
        ]

        with patch.object(etl_bdns, "get_db_connection", return_value=conn), \
             patch.object(etl_bdns, "fetch_bdns_convocatorias_api", return_value=convocatorias) as fetch_api:
            mensaje = etl_bdns.run_etl_p4(target_codes=["28070", "28078"], force_refresh=True)

        self.assertIn("OK", mensaje)
        self.assertIn("(4 convocatorias, 5 asignaciones en 2 municipios)", mensaje)
        self.assertEqual(fetch_api.call_count, 1)
        self.assertEqual(list(fetch_api.call_args.args[0]), ["Hiruela, La", "Madarcos"])
        self.assertTrue(fetch_api.call_args.kwargs["force_refresh"])
        self.assertEqual(conn.commit.call_count, 2)
        conn.close.assert_called_once()

        updates = [
            c.args[1]
            for c in cur.execute.call_args_list
            if "UPDATE municipios SET hidratado = TRUE" in c.args[0]
        ]
        self.assertEqual(updates, [("28070",), ("28078",)])


# =============================================================================
# 6. DETALLE BDNS CON FIXTURE REAL (sesión HTTP simulada)
# =============================================================================

class TestBDNSEnVivo(unittest.TestCase):

    def test_detalle_921084(self):
        sesion = MagicMock()
        sesion.get.return_value = _RespuestaFalsa(cargar_fixture("detalle_921084.json"))

        detalle = etl_bdns.obtener_detalle(sesion, "921084")
        fila = etl_bdns.normalizar_detalle(detalle, hoy=date(2026, 8, 1))

        sesion.get.assert_called_once_with(
            etl_bdns.BDNS_API_URL,
            params={"numConv": "921084", "vpd": "GE"},
            timeout=etl_bdns.BDNS_TIMEOUT,
        )
        self.assertEqual(fila["codigo_bdns"], "921084")
        self.assertEqual(fila["organo_nivel2"], "COMUNIDAD DE MADRID")
        self.assertEqual(fila["organo_nivel3"], ORGANO_921084)
        self.assertEqual(fila["poblacion_max_objetivo"], 20000)
        self.assertEqual(fila["fin_solicitud"], date(2026, 9, 30))
        self.assertTrue(fila["abierta"])


if __name__ == "__main__":
    unittest.main()
