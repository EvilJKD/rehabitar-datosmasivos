"""
Suite de pruebas unitarias del modulo P2: Demografia INE Tempus (Tabla 2881) y Consulta 3
(`etl/p2_ine/etl_ine.py`, `backend/models/domain.py`, `db/schema.sql`,
`backend/services/p2_demo_service.py`, `backend/schemas/domain.py`).
"""

import ast
import os
import re
import sys
import threading
import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(TESTS_DIR, ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
ETL_DIR = os.path.join(REPO_ROOT, "etl")
for ruta in (BACKEND_DIR, ETL_DIR):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

from p2_ine import etl_ine  # noqa: E402
from schemas import DemografiaPuntoAnualSchema, DemografiaSerieResponseSchema  # noqa: E402
from schemas._compat import BaseModel as CompatBaseModel  # noqa: E402
from services import p2_demo_service as p2  # noqa: E402


def _call_name(node: ast.AST) -> str:
    """Devuelve el nombre simple de una llamada o atributo AST."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _split_sql_top_level(body: str) -> list[str]:
    """Divide elementos de un bloque CREATE TABLE respetando parentesis."""
    partes: list[str] = []
    actual: list[str] = []
    nivel = 0
    for ch in body:
        if ch == "(":
            nivel += 1
        elif ch == ")":
            nivel -= 1
        if ch == "," and nivel == 0:
            trozo = " ".join("".join(actual).split())
            if trozo:
                partes.append(trozo)
            actual = []
        else:
            actual.append(ch)
    ultimo = " ".join("".join(actual).split())
    if ultimo:
        partes.append(ultimo)
    return partes


def _fake_ine_series() -> list[dict]:
    return [
        {
            "Nombre": "Madarcos. Total. Total habitantes.",
            "MetaData": [
                {"T3_Variable": "Municipios", "Nombre": "Madarcos", "Codigo": "28078"},
                {"T3_Variable": "Sexo", "Nombre": "Total", "Codigo": "0"},
            ],
            "Data": [
                {"Anyo": 2026, "Valor": 49.0},  # Fuera de rango 2015-2025
                {"Anyo": 2025, "Valor": 47.0},
                {"Anyo": 2020, "Valor": 46.0},
                {"Anyo": 2015, "Valor": 51.0},
                {"Anyo": 2014, "Valor": 52.0},  # Fuera de rango 2015-2025
                {"Anyo": 2018, "Valor": None},  # Protegido / vacío
            ],
        },
        {
            "Nombre": "Madarcos. Hombres. Total habitantes.",
            "MetaData": [
                {"T3_Variable": "Municipios", "Nombre": "Madarcos", "Codigo": "28078"},
                {"T3_Variable": "Sexo", "Nombre": "Hombres", "Codigo": "1"},
            ],
            "Data": [{"Anyo": 2025, "Valor": 25.0}],
        },
        {
            "Nombre": "Total Provincial. Total.",
            "MetaData": [
                {"T3_Variable": "Provincias", "Nombre": "Madrid", "Codigo": "28"},
                {"T3_Variable": "Sexo", "Nombre": "Total", "Codigo": "0"},
            ],
            "Data": [{"Anyo": 2025, "Valor": 7000000.0}],
        },
    ]


class TestP2ETL(unittest.TestCase):
    def setUp(self):
        etl_ine._CACHE_TABLAS.clear()

    def tearDown(self):
        etl_ine._CACHE_TABLAS.clear()

    def test_serie_transform_and_fetch_filters_sex_and_years(self):
        series = _fake_ine_series()
        self.assertTrue(etl_ine._es_del_municipio(series[0], "28078"))
        self.assertTrue(etl_ine._es_sexo_total(series[0]))
        self.assertFalse(etl_ine._es_sexo_total(series[1]))

        dicc = etl_ine._serie_a_diccionario(series[0])
        self.assertEqual(dicc, {2015: 51, 2020: 46, 2025: 47})

        with patch.object(etl_ine, "_download_tabla", return_value=series):
            filas_mad = etl_ine.fetch_ine_series_api("28078")
            filas_all = etl_ine.fetch_ine_series_api(None)

        self.assertEqual([f["anio"] for f in filas_mad], [2015, 2020, 2025])
        self.assertEqual([f["poblacion"] for f in filas_mad], [51, 46, 47])
        self.assertTrue(all(f["tasa_envejecimiento"] is None for f in filas_mad))
        # El total provincial ('28') no debe colarse como municipio 28xxx
        self.assertEqual({f["codigo_ine"] for f in filas_all}, {"28078"})

    def test_ingest_ine_for_municipio_and_run_etl_p2(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        # Primer intento: existe municipio; segundo intento: no existe
        mock_cursor.fetchone.side_effect = [(1,), None]

        with patch.object(etl_ine, "_download_tabla", return_value=_fake_ine_series()):
            count_ok = etl_ine.ingest_ine_for_municipio("28078", conn=mock_conn)
            count_missing = etl_ine.ingest_ine_for_municipio("28999", conn=mock_conn)

        self.assertEqual(count_ok, 3)
        self.assertEqual(count_missing, 0)
        mock_cursor.executemany.assert_called_once()
        sql_arg, rows_arg = mock_cursor.executemany.call_args[0]
        self.assertIn("INSERT INTO demografia_anual", sql_arg)
        self.assertIn("ON CONFLICT (codigo_ine, anio) DO UPDATE", sql_arg)
        self.assertEqual(len(rows_arg), 3)
        mock_conn.commit.assert_called_once()


class TestP2ModeloYEsquema(unittest.TestCase):
    """Valida el modelo ORM, el DDL SQL y los esquemas sin depender de BD ni de librerias externas."""

    COLUMNAS_ESPERADAS = [
        "codigo_ine",
        "anio",
        "poblacion",
        "poblacion_mayor_65",
        "poblacion_menor_15",
        "tasa_envejecimiento",
    ]
    CLAVE_PRIMARIA_ESPERADA = ["codigo_ine", "anio"]

    def test_modelo_demografia_anual_ast(self):
        """Inspecciona por AST la definicion de DemografiaAnual en backend/models/domain.py."""
        ruta_modelos = os.path.join(BACKEND_DIR, "models", "domain.py")
        with open(ruta_modelos, "r", encoding="utf-8") as fh:
            arbol = ast.parse(fh.read(), filename=ruta_modelos)

        clase = next(
            (n for n in arbol.body if isinstance(n, ast.ClassDef) and n.name == "DemografiaAnual"),
            None,
        )
        self.assertIsNotNone(clase)
        self.assertIn("Base", [_call_name(b) for b in clase.bases])

        tablename = None
        columnas: dict[str, dict] = {}
        orden_columnas: list[str] = []

        for stmt in clase.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                objetivo = stmt.targets[0]
                if isinstance(objetivo, ast.Name) and objetivo.id == "__tablename__":
                    if isinstance(stmt.value, ast.Constant):
                        tablename = stmt.value.value
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                llamada = stmt.value
                if isinstance(llamada, ast.Call) and _call_name(llamada.func) in ("mapped_column", "Column"):
                    nombre_col = stmt.target.id
                    orden_columnas.append(nombre_col)
                    keywords = {
                        kw.arg: ast.unparse(kw.value)
                        for kw in llamada.keywords
                        if kw.arg is not None
                    }
                    columnas[nombre_col] = {
                        "anotacion": ast.unparse(stmt.annotation),
                        "args": llamada.args,
                        "args_texto": [ast.unparse(a) for a in llamada.args],
                        "keywords": keywords,
                    }

        self.assertEqual(tablename, "demografia_anual")
        self.assertEqual(orden_columnas, self.COLUMNAS_ESPERADAS)

        pk_cols = [
            nombre
            for nombre in orden_columnas
            if columnas[nombre]["keywords"].get("primary_key") == "True"
        ]
        self.assertEqual(pk_cols, self.CLAVE_PRIMARIA_ESPERADA)

        # codigo_ine: String(5), FK a municipios.codigo_ine con CASCADE y no opcional
        col_codigo = columnas["codigo_ine"]
        self.assertEqual(col_codigo["anotacion"], "Mapped[str]")
        self.assertIn("String(5)", col_codigo["args_texto"])
        fk_node = next(
            (a for a in col_codigo["args"] if isinstance(a, ast.Call) and _call_name(a.func) == "ForeignKey"),
            None,
        )
        self.assertIsNotNone(fk_node)
        self.assertGreaterEqual(len(fk_node.args), 1)
        self.assertIsInstance(fk_node.args[0], ast.Constant)
        self.assertEqual(fk_node.args[0].value, "municipios.codigo_ine")
        fk_ondelete = {kw.arg: ast.unparse(kw.value) for kw in fk_node.keywords if kw.arg}.get("ondelete")
        self.assertIn(fk_ondelete, ("'CASCADE'", '"CASCADE"'))

        # anio y poblacion: tipos esperados y no nulables
        self.assertEqual(columnas["anio"]["anotacion"], "Mapped[int]")
        self.assertIn("SmallInteger", columnas["anio"]["args_texto"])

        self.assertEqual(columnas["poblacion"]["anotacion"], "Mapped[int]")
        self.assertIn("Integer", columnas["poblacion"]["args_texto"])
        self.assertEqual(columnas["poblacion"]["keywords"].get("nullable"), "False")

        # Las 3 columnas de edad deben admitir NULL
        self.assertEqual(columnas["poblacion_mayor_65"]["anotacion"], "Mapped[Optional[int]]")
        self.assertIn("Integer", columnas["poblacion_mayor_65"]["args_texto"])
        self.assertNotEqual(columnas["poblacion_mayor_65"]["keywords"].get("nullable"), "False")

        self.assertEqual(columnas["poblacion_menor_15"]["anotacion"], "Mapped[Optional[int]]")
        self.assertIn("Integer", columnas["poblacion_menor_15"]["args_texto"])
        self.assertNotEqual(columnas["poblacion_menor_15"]["keywords"].get("nullable"), "False")

        self.assertEqual(columnas["tasa_envejecimiento"]["anotacion"], "Mapped[Optional[Decimal]]")
        self.assertIn("Numeric(5, 2)", columnas["tasa_envejecimiento"]["args_texto"])
        self.assertNotEqual(columnas["tasa_envejecimiento"]["keywords"].get("nullable"), "False")

    def test_ddl_demografia_anual_schema_sql(self):
        """Inspecciona en db/schema.sql la tabla demografia_anual, su PK compuesta y columnas."""
        ruta_sql = os.path.join(REPO_ROOT, "db", "schema.sql")
        with open(ruta_sql, "r", encoding="utf-8") as fh:
            ddl = fh.read()

        match_tabla = re.search(
            r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+demografia_anual\s*\((.*?)\)\s*;",
            ddl,
            re.DOTALL | re.IGNORECASE,
        )
        self.assertIsNotNone(match_tabla)

        elementos = _split_sql_top_level(match_tabla.group(1))
        definiciones_col: dict[str, str] = {}
        orden_cols: list[str] = []
        restricciones: list[str] = []

        for elem in elementos:
            primera_palabra = elem.split(None, 1)[0].upper()
            if primera_palabra in ("CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "CHECK"):
                restricciones.append(elem)
            else:
                nombre_col = elem.split(None, 1)[0]
                orden_cols.append(nombre_col)
                definiciones_col[nombre_col] = elem

        self.assertEqual(orden_cols, self.COLUMNAS_ESPERADAS)

        # Clave primaria compuesta (codigo_ine, anio)
        pk_match = re.search(
            r"PRIMARY\s+KEY\s*\(\s*([^)]+?)\s*\)",
            " ".join(restricciones),
            re.IGNORECASE,
        )
        self.assertIsNotNone(pk_match)
        pk_cols = [c.strip() for c in pk_match.group(1).split(",")]
        self.assertEqual(pk_cols, self.CLAVE_PRIMARIA_ESPERADA)

        # Restricciones por columna: nulabilidad, tipos y clave foranea
        self.assertRegex(definiciones_col["codigo_ine"], r"\bVARCHAR\s*\(\s*5\s*\)")
        self.assertRegex(definiciones_col["codigo_ine"], r"\bNOT\s+NULL\b")
        self.assertRegex(
            definiciones_col["codigo_ine"],
            r"REFERENCES\s+municipios\s*\(\s*codigo_ine\s*\)\s+ON\s+DELETE\s+CASCADE",
        )

        self.assertRegex(definiciones_col["anio"], r"\bSMALLINT\b")
        self.assertRegex(definiciones_col["anio"], r"\bNOT\s+NULL\b")

        self.assertRegex(definiciones_col["poblacion"], r"\bINTEGER\b")
        self.assertRegex(definiciones_col["poblacion"], r"\bNOT\s+NULL\b")

        for col_edad in ("poblacion_mayor_65", "poblacion_menor_15", "tasa_envejecimiento"):
            self.assertNotRegex(definiciones_col[col_edad], r"\bNOT\s+NULL\b")
        self.assertRegex(definiciones_col["tasa_envejecimiento"], r"\bNUMERIC\s*\(\s*5\s*,\s*2\s*\)")

        # Indice para consultas transversales por anio y codigo
        ddl_normalizado = " ".join(ddl.split())
        self.assertIn(
            "CREATE INDEX IF NOT EXISTS idx_demografia_anio_codigo ON demografia_anual (anio, codigo_ine)",
            ddl_normalizado,
        )

    def test_schemas_demografia_compat(self):
        """Comprueba los esquemas demograficos en schemas/domain.py y mediante _compat.py."""
        ruta_schemas = os.path.join(BACKEND_DIR, "schemas", "domain.py")
        with open(ruta_schemas, "r", encoding="utf-8") as fh:
            arbol = ast.parse(fh.read(), filename=ruta_schemas)

        anotaciones_por_clase: dict[str, dict[str, str]] = {}
        for nodo in arbol.body:
            if isinstance(nodo, ast.ClassDef) and nodo.name in (
                "DemografiaPuntoAnualSchema",
                "DemografiaSerieResponseSchema",
            ):
                anotaciones_por_clase[nodo.name] = {
                    stmt.target.id: ast.unparse(stmt.annotation)
                    for stmt in nodo.body
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
                }

        self.assertIn("DemografiaPuntoAnualSchema", anotaciones_por_clase)
        self.assertIn("DemografiaSerieResponseSchema", anotaciones_por_clase)
        self.assertEqual(
            anotaciones_por_clase["DemografiaSerieResponseSchema"]["variacion_10a_pct"],
            "Optional[float]",
        )
        self.assertEqual(
            anotaciones_por_clase["DemografiaSerieResponseSchema"]["poblacion_inicial_10a"],
            "Optional[int]",
        )

        self.assertTrue(DemografiaPuntoAnualSchema.model_config.get("from_attributes"))

        punto = DemografiaPuntoAnualSchema(anio=2025, poblacion=88)
        self.assertEqual(punto.anio, 2025)
        self.assertEqual(punto.poblacion, 88)
        self.assertIsNone(punto.poblacion_mayor_65)
        self.assertIsNone(punto.poblacion_menor_15)
        self.assertIsNone(punto.tasa_envejecimiento)

        serie = DemografiaSerieResponseSchema(
            codigo_ine="28027",
            nombre="Buitrago del Lozoya",
            poblacion_inicial_10a=None,
            poblacion_actual=2034,
            variacion_10a_pct=None,
            serie_anual=[punto],
        )
        self.assertIsInstance(serie, CompatBaseModel)
        self.assertIsNone(serie.poblacion_inicial_10a)
        self.assertIsNone(serie.variacion_10a_pct)
        self.assertIsNone(serie.cobertura_fibra_pct)
        self.assertIsNone(serie.distancia_urgencias_km)
        self.assertIsNone(serie.num_ayudas_abiertas)
        serializado = serie.model_dump(mode="json")
        self.assertIsNone(serializado["variacion_10a_pct"])
        self.assertEqual(len(serializado["serie_anual"]), 1)


class TestP2DemoServiceConsulta3(unittest.IsolatedAsyncioTestCase):
    def test_calcular_variacion_and_inertia_classification(self):
        self.assertEqual(p2.calcular_variacion_pct(47, 51), -7.84)
        self.assertEqual(p2.calcular_variacion_pct(2034, 1865), 9.06)
        self.assertEqual(p2.calcular_variacion_pct(0, 50), -100.0)
        self.assertIsNone(p2.calcular_variacion_pct(47, 0))
        self.assertIsNone(p2.calcular_variacion_pct(47, None))
        self.assertIsNone(p2.calcular_variacion_pct(None, 100))

        casos_frontera = [
            (None, 3.0, 500, p2.SIN_DATOS, "sin dato a 10 anos"),
            (-20.0, 5.0, 500, p2.COLAPSO, "limite exacto -20% es COLAPSO"),
            (-19.99, -1.0, 500, p2.DECLIVE, "-19.99% ya no es COLAPSO"),
            (-1.0, -1.0, 49, p2.COLAPSO, "menos de 50 hab y bajando es COLAPSO"),
            (-1.0, 10.0, 49, p2.COLAPSO, "COLAPSO tiene prioridad sobre REPUNTE"),
            (-1.0, -1.0, 50, p2.ESTANCAMIENTO, "50 hab ya no cuenta como menos de 50"),
            (0.0, -1.0, 30, p2.ESTANCAMIENTO, "menos de 50 hab con var_10a igual a 0"),
            (-10.0, 0.01, 500, p2.REPUNTE_RECIENTE, "baja a 10 anos pero sube a 5 anos"),
            (-10.0, 0.0, 500, p2.DECLIVE, "var_5a igual a 0 no es repunte"),
            (-10.0, None, 500, p2.DECLIVE, "var_5a ausente no es repunte"),
            (-2.0, 1.0, 500, p2.REPUNTE_RECIENTE, "REPUNTE tiene prioridad sobre ESTANCAMIENTO"),
            (-5.0, -1.0, 500, p2.DECLIVE, "limite exacto -5% es DECLIVE"),
            (-4.99, -1.0, 500, p2.ESTANCAMIENTO, "-4.99% es ESTANCAMIENTO"),
            (4.99, 3.0, 500, p2.ESTANCAMIENTO, "+4.99% es ESTANCAMIENTO"),
            (5.0, 0.01, 500, p2.RECUPERACION, "limite exacto +5% y var_5a positiva es RECUPERACION"),
            (12.0, 0.0, 500, p2.ESTANCAMIENTO, "sube +12% pero var_5a igual a 0"),
            (12.0, -3.0, 500, p2.ESTANCAMIENTO, "sube +12% pero var_5a negativa"),
        ]
        for var_10a, var_5a, pob, esperado, motivo in casos_frontera:
            with self.subTest(motivo=motivo):
                self.assertEqual(p2.classify_demographic_inertia(var_10a, var_5a, None, pob), esperado)

        # tasa_envejecimiento no debe alterar la clasificacion actual
        self.assertEqual(
            p2.classify_demographic_inertia(-10.0, 1.0, 35.5, 500),
            p2.classify_demographic_inertia(-10.0, 1.0, None, 500),
        )

        self.assertFalse(p2.preserva_masa_critica(47))
        self.assertFalse(p2.preserva_masa_critica(99))
        self.assertFalse(p2.preserva_masa_critica(None))
        self.assertTrue(p2.preserva_masa_critica(100))

    def test_calcular_indicadores_madarcos_reference_case(self):
        # Caso de referencia Madarcos (Seccion 7.2): 51 -> 46 -> 47 (-7.84%)
        ind = p2.calcular_indicadores({2015: 51, 2020: 46, 2025: 47})
        self.assertEqual(ind["poblacion_inicial_10a"], 51)
        self.assertEqual(ind["poblacion_actual"], 47)
        self.assertEqual(ind["variacion_10a_pct"], -7.84)
        self.assertFalse(ind["preserva_masa_critica"])
        self.assertEqual(ind["inercia_demografica"], p2.COLAPSO)

        # Sin anio base a 10 anos: variacion_10a_pct es None e inercia SIN_DATOS
        sin_base_10a = p2.calcular_indicadores({2025: 88, 2020: 65})
        self.assertIsNone(sin_base_10a["variacion_10a_pct"])
        self.assertEqual(sin_base_10a["variacion_5a_pct"], 35.38)
        self.assertEqual(sin_base_10a["inercia_demografica"], p2.SIN_DATOS)
        self.assertFalse(sin_base_10a["preserva_masa_critica"])

        # Serie vacia devuelve None
        self.assertIsNone(p2.calcular_indicadores({}))

    async def test_hydrate_summary_and_serie_services(self):
        # 1) Ya existe en BD: hydrate devuelve 0 sin invocar ETL
        mock_db = AsyncMock()
        res_exists = MagicMock()
        res_exists.scalar.return_value = True
        mock_db.execute.return_value = res_exists
        self.assertEqual(await p2.hydrate_demografia_on_demand(mock_db, "28078"), 0)

        # 2) No existe: invoca ETL en un hilo secundario mediante asyncio.to_thread
        hilo_principal = threading.get_ident()
        hilo_ingesta = None

        def _fake_ingest(codigo_ine: str) -> int:
            nonlocal hilo_ingesta
            hilo_ingesta = threading.get_ident()
            return 11

        res_missing = MagicMock()
        res_missing.scalar.return_value = False
        mock_db.execute.return_value = res_missing
        with patch("p2_ine.etl_ine.ingest_ine_for_municipio", side_effect=_fake_ingest) as mock_ing:
            inserted = await p2.hydrate_demografia_on_demand(mock_db, "28069")
        self.assertEqual(inserted, 11)
        self.assertIsNotNone(hilo_ingesta)
        self.assertNotEqual(hilo_ingesta, hilo_principal)
        mock_ing.assert_called_once_with("28069")

        # 3) Municipio inexistente en catalogo: devuelve None sin lanzar excepcion
        res_no_existe = MagicMock()
        res_no_existe.scalar.return_value = False
        res_serie_vacia = MagicMock()
        res_serie_vacia.mappings.return_value.all.return_value = []
        mock_db.execute.side_effect = [res_no_existe, res_serie_vacia]
        with patch("p2_ine.etl_ine.ingest_ine_for_municipio", return_value=0) as mock_ing_vacio:
            self.assertIsNone(await p2.get_demografia_serie_by_municipio(mock_db, "28070"))
        mock_ing_vacio.assert_called_once_with("28070")

        # 4) Summary all + serie by municipio
        res_summary = MagicMock()
        res_summary.mappings.return_value = [
            {
                "codigo_ine": "28078",
                "anio_actual": 2025,
                "pob_actual": 47,
                "pob_5a": 46,
                "pob_10a": 51,
                "tasa_env": Decimal("28.50"),
            }
        ]
        res_exists_2 = MagicMock()
        res_exists_2.scalar.return_value = True
        res_serie = MagicMock()
        res_serie.mappings.return_value.all.return_value = [
            {
                "nombre": "Madarcos",
                "anio": 2015,
                "poblacion": 51,
                "poblacion_mayor_65": None,
                "poblacion_menor_15": None,
                "tasa_envejecimiento": None,
            },
            {
                "nombre": "Madarcos",
                "anio": 2020,
                "poblacion": 46,
                "poblacion_mayor_65": None,
                "poblacion_menor_15": None,
                "tasa_envejecimiento": None,
            },
            {
                "nombre": "Madarcos",
                "anio": 2025,
                "poblacion": 47,
                "poblacion_mayor_65": None,
                "poblacion_menor_15": None,
                "tasa_envejecimiento": Decimal("28.50"),
            },
        ]
        mock_db.execute.side_effect = [res_summary, res_exists_2, res_serie]

        summary = await p2.get_demografia_summary_all(mock_db)
        self.assertEqual(summary["28078"]["variacion_10a_pct"], -7.84)

        serie = await p2.get_demografia_serie_by_municipio(
            mock_db,
            "28078",
            cobertura_fibra_pct=100.0,
            distancia_urgencias_km=7.75,
            num_ayudas_abiertas=1,
        )
        self.assertEqual(summary["28078"]["variacion_10a_pct"], serie["variacion_10a_pct"])
        self.assertEqual(summary["28078"]["variacion_5a_pct"], serie["variacion_5a_pct"])
        self.assertEqual(summary["28078"]["inercia_demografica"], serie["inercia_demografica"])

        schema = DemografiaSerieResponseSchema(
            **{
                **{k: v for k, v in serie.items() if k != "serie_anual"},
                "serie_anual": [DemografiaPuntoAnualSchema(**p) for p in serie["serie_anual"]],
            }
        )
        self.assertEqual(schema.nombre, "Madarcos")
        self.assertEqual(schema.variacion_10a_pct, -7.84)
        self.assertEqual(schema.cobertura_fibra_pct, 100.0)
        self.assertEqual(schema.distancia_urgencias_km, 7.75)
        self.assertEqual(schema.num_ayudas_abiertas, 1)
        self.assertEqual(len(schema.serie_anual), 3)

    async def test_serie_y_resumen_sin_anio_base_2015(self):
        """
        Simula una serie historica sin el anio base 2015 (solo 2016 a 2025).
        Comprueba que variacion_10a_pct sea None, inercia_demografica sea SIN_DATOS,
        variacion_5a_pct se siga calculando y DemografiaSerieResponseSchema acepte None.
        """
        poblaciones_sin_2015 = {
            2016: 1870,
            2017: 1885,
            2018: 1900,
            2019: 1920,
            2020: 1946,
            2021: 1960,
            2022: 1980,
            2023: 2000,
            2024: 2015,
            2025: 2034,
        }
        filas_serie = [
            {
                "nombre": "Buitrago del Lozoya",
                "anio": anio,
                "poblacion": pob,
                "poblacion_mayor_65": None,
                "poblacion_menor_15": None,
                "tasa_envejecimiento": None,
            }
            for anio, pob in poblaciones_sin_2015.items()
        ]

        res_summary = MagicMock()
        res_summary.mappings.return_value = [
            {
                "codigo_ine": "28027",
                "anio_actual": 2025,
                "pob_actual": 2034,
                "pob_5a": 1946,
                "pob_10a": None,
                "tasa_env": None,
            }
        ]
        res_exists = MagicMock()
        res_exists.scalar.return_value = True
        res_serie = MagicMock()
        res_serie.mappings.return_value.all.return_value = filas_serie

        mock_db = AsyncMock()
        mock_db.execute.side_effect = [res_summary, res_exists, res_serie]

        with patch("p2_ine.etl_ine.ingest_ine_for_municipio") as mock_ing:
            resumen = await p2.get_demografia_summary_all(mock_db)
            serie = await p2.get_demografia_serie_by_municipio(mock_db, "28027")

        # Ya hay filas en la serie (2016-2025): no debe relanzar la ingesta
        mock_ing.assert_not_called()

        # Validacion en get_demografia_summary_all
        self.assertIn("28027", resumen)
        item_resumen = resumen["28027"]
        self.assertIsNone(item_resumen["poblacion_inicial_10a"])
        self.assertIsNone(item_resumen["variacion_10a_pct"])
        self.assertEqual(item_resumen["inercia_demografica"], "SIN_DATOS")
        self.assertEqual(item_resumen["variacion_5a_pct"], 4.52)
        self.assertTrue(item_resumen["preserva_masa_critica"])

        # Validacion en get_demografia_serie_by_municipio
        self.assertIsNotNone(serie)
        self.assertIsNone(serie["poblacion_inicial_10a"])
        self.assertIsNone(serie["variacion_10a_pct"])
        self.assertEqual(serie["inercia_demografica"], "SIN_DATOS")
        self.assertEqual(serie["variacion_5a_pct"], 4.52)
        self.assertEqual(len(serie["serie_anual"]), 10)
        self.assertEqual([p["anio"] for p in serie["serie_anual"]], list(range(2016, 2026)))

        # Validacion de DemografiaSerieResponseSchema via _compat.py con variacion_10a_pct=None
        schema = DemografiaSerieResponseSchema(
            **{
                **{k: v for k, v in serie.items() if k != "serie_anual"},
                "serie_anual": [DemografiaPuntoAnualSchema(**p) for p in serie["serie_anual"]],
            }
        )
        self.assertIsInstance(schema, CompatBaseModel)
        self.assertIsNone(schema.poblacion_inicial_10a)
        self.assertIsNone(schema.variacion_10a_pct)
        self.assertEqual(schema.poblacion_actual, 2034)
        self.assertEqual(len(schema.serie_anual), 10)
        self.assertIsNone(schema.model_dump(mode="json")["variacion_10a_pct"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
