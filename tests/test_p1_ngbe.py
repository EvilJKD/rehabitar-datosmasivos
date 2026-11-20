"""
Suite de Pruebas Unitarias del Módulo P1: NGBE/IGN, SETELECO, IDEE, Modelos y Servicio Geográfico
(`etl/p1_ngbe/sources.py`, `etl/p1_ngbe/etl_ngbe.py`, `backend/services/p1_geo_service.py`,
`backend/models/domain.py`, `db/schema.sql`, `InfraestructuraSchema`).
"""

import ast
import io
import json
import os
import re
import sys
import unittest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from openpyxl import Workbook

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(TESTS_DIR, ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
ETL_DIR = os.path.join(REPO_ROOT, "etl")
for ruta in (BACKEND_DIR, ETL_DIR):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

from p1_ngbe import etl_ngbe, sources  # noqa: E402
from schemas import InfraestructuraSchema  # noqa: E402
from services import p1_geo_service  # noqa: E402


def _make_xlsx_bytes(sheet_name: str, rows: list[list[object]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


class TestP1Sources(unittest.TestCase):
    def tearDown(self):
        sources._read_coverage.cache_clear()

    def test_fetch_municipios_ign_api_parses_and_classifies_sierra_norte(self):
        xlsx_bytes = _make_xlsx_bytes(
            "IGN_INFOGEO_MUNICIPIOS",
            [
                ["Identificador", "Nombre", "Ver en mapa"],
                ["28078", "Madarcos", "https://ign.es/map?center=-3.58280,41.04870"],
                ["28069", "Hiruela, La", "https://ign.es/map?center=-3.45110,41.07670"],
                ["28079", "Madrid", "https://ign.es/map?center=-3.70380,40.41680"],
                ["19001", "Abánades", "https://ign.es/map?center=-2.48000,40.89000"],
            ],
        )
        with patch.object(sources, "_download", return_value=xlsx_bytes):
            municipios = sources.fetch_municipios_ign_api()

        self.assertEqual([m["codigo_ine"] for m in municipios], ["28069", "28078", "28079"])
        by_code = {m["codigo_ine"]: m for m in municipios}
        self.assertEqual(by_code["28078"]["comarca"], "Sierra Norte")
        self.assertEqual(by_code["28069"]["comarca"], "Sierra Norte")
        self.assertEqual(by_code["28079"]["comarca"], "Sin clasificar")
        self.assertAlmostEqual(by_code["28078"]["latitud"], 41.04870)
        self.assertAlmostEqual(by_code["28078"]["longitud"], -3.58280)

    def test_fetch_municipios_ign_api_rejects_invalid_coords_or_duplicates(self):
        bad_coords = _make_xlsx_bytes(
            "IGN_INFOGEO_MUNICIPIOS",
            [
                ["Identificador", "Nombre", "Ver en mapa"],
                ["28078", "Madarcos", "https://ign.es/map?sin_coords=1"],
            ],
        )
        with patch.object(sources, "_download", return_value=bad_coords):
            with self.assertRaises(sources.SourceError):
                sources.fetch_municipios_ign_api()

        dup_xlsx = _make_xlsx_bytes(
            "IGN_INFOGEO_MUNICIPIOS",
            [
                ["Identificador", "Nombre", "Ver en mapa"],
                ["28078", "Madarcos", "https://ign.es/map?center=-3.5828,41.0487"],
                ["28078", "Madarcos Dup", "https://ign.es/map?center=-3.5828,41.0487"],
            ],
        )
        with patch.object(sources, "_download", return_value=dup_xlsx):
            with self.assertRaises(sources.SourceError):
                sources.fetch_municipios_ign_api()

    def test_get_coverage_parses_seteleco_proportions(self):
        xlsx_bytes = _make_xlsx_bytes(
            "Municipio_%hogar",
            [
                ["CMUN", "FTTH (junio 2025)", "4G (junio 2025)"],
                ["28078", 1.000001, 0.985],
                ["28069", 0.8543, 0.92],
            ],
        )
        with patch.object(sources, "_download", return_value=xlsx_bytes):
            fibra_mad, movil_mad = sources.get_coverage("28078")
            fibra_hir, movil_hir = sources.get_coverage("28069")
            with self.assertRaises(sources.SourceError):
                sources.get_coverage("28999")

        self.assertEqual((fibra_mad, movil_mad), (100.0, 98.5))
        self.assertEqual((fibra_hir, movil_hir), (85.43, 92.0))

    def test_get_infrastructure_lines_handles_pagination_and_empty_error(self):
        page1 = json.dumps({
            "type": "FeatureCollection",
            "features": [{"geometry": {"type": "LineString", "coordinates": [[-3.58, 41.04], [-3.59, 41.05]]}}],
            "links": [{"rel": "next", "href": "https://api-features.idee.es/next"}],
        }).encode("utf-8")
        page2 = json.dumps({
            "type": "FeatureCollection",
            "features": [{"geometry": {"type": "MultiLineString", "coordinates": [[[-3.6, 41.0], [-3.61, 41.01]]]}}],
            "links": [],
        }).encode("utf-8")
        water = json.dumps({
            "type": "FeatureCollection",
            "features": [{"geometry": {"type": "LineString", "coordinates": [[-3.582, 41.048], [-3.580, 41.049]]}}],
            "links": [],
        }).encode("utf-8")

        with patch.object(sources, "_download", side_effect=[page1, page2, water]):
            road_geojson, water_geojson = sources.get_infrastructure_lines(41.0487, -3.5828)

        road_obj = json.loads(road_geojson)
        water_obj = json.loads(water_geojson)
        self.assertEqual(road_obj["type"], "MultiLineString")
        self.assertEqual(len(road_obj["coordinates"]), 2)
        self.assertEqual(water_obj["type"], "MultiLineString")
        self.assertEqual(len(water_obj["coordinates"]), 1)

        empty = json.dumps({"type": "FeatureCollection", "features": [], "links": []}).encode("utf-8")
        with patch.object(sources, "_download", return_value=empty):
            with self.assertRaises(sources.SourceError):
                sources.get_infrastructure_lines(41.0487, -3.5828)


class TestP1ETLAndGeoService(unittest.IsolatedAsyncioTestCase):
    def test_ingest_infraestructura_municipio_and_validation(self):
        with self.assertRaises(ValueError):
            etl_ngbe.ingest_infraestructura_municipio("19001")

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            {"latitud": 41.0487, "longitud": -3.5828},
            {
                "codigo_ine": "28078",
                "distancia_carretera_km": 0.0,
                "distancia_recurso_hidrico_km": 0.35,
                "cobertura_fibra_pct": 100.0,
                "cobertura_movil_pct": 98.5,
                "fecha_actualizacion": date(2026, 11, 20),
            },
        ]

        with patch.object(etl_ngbe, "get_coverage", return_value=(100.0, 98.5)), patch.object(
            etl_ngbe,
            "get_infrastructure_lines",
            return_value=('{"type":"MultiLineString","coordinates":[]}', '{"type":"MultiLineString","coordinates":[]}'),
        ):
            res = etl_ngbe.ingest_infraestructura_municipio("28078", conn=mock_conn)

        self.assertEqual(res["codigo_ine"], "28078")
        self.assertEqual(res["cobertura_fibra_pct"], 100.0)
        self.assertEqual(res["distancia_recurso_hidrico_km"], 0.35)

    def test_run_etl_p1_rejects_unknown_seed_and_loads_catalog(self):
        catalog = [
            {
                "codigo_ine": "28078",
                "nombre": "Madarcos",
                "provincia": "Madrid",
                "comarca": "Sierra Norte",
                "latitud": 41.0487,
                "longitud": -3.5828,
            }
        ]
        with patch.object(etl_ngbe, "fetch_municipios_ign_api", return_value=catalog):
            with self.assertRaises(ValueError):
                etl_ngbe.run_etl_p1(seed_codes=["28070"])

            mock_conn = MagicMock()
            with patch.object(etl_ngbe, "get_db_connection", return_value=mock_conn), patch.object(
                etl_ngbe, "execute_values"
            ) as mock_exec_vals, patch.object(
                etl_ngbe, "ingest_infraestructura_municipio"
            ) as mock_ingest:
                summary = etl_ngbe.run_etl_p1(seed_codes=["28078", "28078"])

        mock_exec_vals.assert_called_once()
        mock_ingest.assert_called_once_with("28078")
        self.assertIn("1 municipios cargados y 1 con métricas actualizadas", summary)

    async def test_p1_geo_service_queries_and_on_demand_hydration(self):
        cached_row = {
            "codigo_ine": "28078",
            "nombre": "Madarcos",
            "provincia": "Madrid",
            "comarca": "Sierra Norte",
            "latitud": 41.0487,
            "longitud": -3.5828,
            "hidratado": True,
            "fecha_hidratacion": None,
            "distancia_carretera_km": 0.0,
            "distancia_recurso_hidrico_km": 0.35,
            "cobertura_fibra_pct": 100.0,
            "cobertura_movil_pct": 98.5,
            "fecha_actualizacion": date(2026, 11, 20),
        }
        mock_db = AsyncMock()
        res_list = MagicMock()
        res_list.mappings.return_value = [cached_row]
        res_get = MagicMock()
        res_get.mappings.return_value.one_or_none.return_value = cached_row
        res_pending = MagicMock()
        res_pending.mappings.return_value.one_or_none.return_value = {
            **cached_row,
            "codigo_ine": "28069",
            "fecha_actualizacion": None,
        }
        res_missing = MagicMock()
        res_missing.mappings.return_value.one_or_none.return_value = None
        mock_db.execute.side_effect = [res_list, res_get, res_pending, res_missing]

        lista = await p1_geo_service.get_all_municipios_base(mock_db)
        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]["codigo_ine"], "28078")

        # Si ya tiene fecha_actualizacion, reutiliza BD sin invocar ETL
        reused = await p1_geo_service.hydrate_infraestructura_on_demand(mock_db, "28078")
        self.assertEqual(reused["cobertura_fibra_pct"], 100.0)
        schema = InfraestructuraSchema(**{k: v for k, v in reused.items() if k != "codigo_ine"})
        self.assertEqual(schema.cobertura_movil_pct, 98.5)

        # Si falta fecha_actualizacion, delega al ETL
        with patch.object(
            p1_geo_service,
            "ingest_infraestructura_municipio",
            return_value={"codigo_ine": "28069", "cobertura_fibra_pct": 85.0},
        ) as mock_etl:
            hydrated = await p1_geo_service.hydrate_infraestructura_on_demand(mock_db, "28069")
        mock_etl.assert_called_once_with("28069")
        self.assertEqual(hydrated["cobertura_fibra_pct"], 85.0)

        with self.assertRaises(LookupError):
            await p1_geo_service.hydrate_infraestructura_on_demand(mock_db, "99999")


def _call_name(node: ast.AST) -> str | None:
    """Devuelve el nombre corto de una llamada AST de funcion o atributo."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _extract_orm_models(models_path: str) -> dict[str, dict[str, object]]:
    """Extrae clases ORM, nombre de tabla y columnas desde el AST sin requerir SQLAlchemy."""
    with open(models_path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=models_path)

    models: dict[str, dict[str, object]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        bases = [base.id if isinstance(base, ast.Name) else ast.unparse(base) for base in node.bases]
        tablename = None
        columns: dict[str, ast.Call] = {}
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
            ):
                target_name = stmt.targets[0].id
                if (
                    target_name == "__tablename__"
                    and isinstance(stmt.value, ast.Constant)
                    and isinstance(stmt.value.value, str)
                ):
                    tablename = stmt.value.value
                elif isinstance(stmt.value, ast.Call) and _call_name(stmt.value.func) == "Column":
                    columns[target_name] = stmt.value
            elif (
                isinstance(stmt, ast.AnnAssign)
                and isinstance(stmt.target, ast.Name)
                and isinstance(stmt.value, ast.Call)
                and _call_name(stmt.value.func) == "mapped_column"
            ):
                columns[stmt.target.id] = stmt.value
        models[node.name] = {"bases": bases, "tablename": tablename, "columns": columns}
    return models


def _split_top_level_sql(body: str) -> list[str]:
    """Divide el cuerpo de un CREATE TABLE por comas externas sin romper tipos con parentesis."""
    items: list[str] = []
    current: list[str] = []
    depth = 0
    in_quote = False
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "'":
            # Dos comillas simples seguidas representan una comilla literal en SQL.
            if in_quote and i + 1 < len(body) and body[i + 1] == "'":
                current.append("''")
                i += 2
                continue
            in_quote = not in_quote
        elif not in_quote:
            if ch == "(":
                depth += 1
            elif ch == ")" and depth > 0:
                depth -= 1
            elif ch == "," and depth == 0:
                items.append("".join(current).strip())
                current = []
                i += 1
                continue
        current.append(ch)
        i += 1
    tail = "".join(current).strip()
    if tail:
        items.append(tail)
    return items


def _extract_sql_table_columns(schema_path: str, table_name: str) -> dict[str, str]:
    """Extrae las columnas y definiciones SQL de una tabla en db/schema.sql."""
    with open(schema_path, encoding="utf-8") as fh:
        raw_sql = fh.read()
    clean_sql = re.sub(r"--[^\n]*", "", raw_sql)

    header = re.search(
        rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{re.escape(table_name)}\s*\(",
        clean_sql,
        re.IGNORECASE,
    )
    if header is None:
        raise AssertionError(f"No se encontro CREATE TABLE para {table_name} en {schema_path}.")

    pos = header.end()
    depth = 1
    in_quote = False
    while pos < len(clean_sql) and depth > 0:
        ch = clean_sql[pos]
        if ch == "'":
            if in_quote and pos + 1 < len(clean_sql) and clean_sql[pos + 1] == "'":
                pos += 2
                continue
            in_quote = not in_quote
        elif not in_quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
        pos += 1

    if depth != 0:
        raise AssertionError(f"Definicion SQL incompleta para la tabla {table_name}.")

    body = clean_sql[header.end() : pos - 1]
    columns: dict[str, str] = {}
    for entry in _split_top_level_sql(body):
        normalized = " ".join(entry.split())
        if not normalized:
            continue
        if normalized.upper().startswith(("CONSTRAINT ", "PRIMARY KEY", "FOREIGN KEY", "UNIQUE ", "CHECK ")):
            continue
        col_match = re.match(r'^"?([a-zA-Z_][a-zA-Z0-9_]*)"?\b', normalized)
        if col_match:
            columns[col_match.group(1)] = normalized
    return columns


class TestP1ModelsAndSchema(unittest.TestCase):
    """Pruebas estructurales de los modelos ORM de P1 frente al esquema SQL."""

    def test_p1_models_and_schema_structure(self):
        """Verifica por AST y DDL que Municipio y MetricaInfraestructura coinciden con schema.sql sin SQLAlchemy."""
        models_path = os.path.join(BACKEND_DIR, "models", "domain.py")
        schema_path = os.path.join(REPO_ROOT, "db", "schema.sql")

        models = _extract_orm_models(models_path)
        self.assertIn("Municipio", models)
        self.assertIn("MetricaInfraestructura", models)

        municipio_orm = models["Municipio"]
        metrica_orm = models["MetricaInfraestructura"]
        self.assertIn("Base", municipio_orm["bases"])
        self.assertIn("Base", metrica_orm["bases"])
        self.assertEqual(municipio_orm["tablename"], "municipios")
        self.assertEqual(metrica_orm["tablename"], "metricas_infraestructura")

        municipios_sql = _extract_sql_table_columns(schema_path, "municipios")
        metricas_sql = _extract_sql_table_columns(schema_path, "metricas_infraestructura")

        expected_municipios_cols = {
            "codigo_ine",
            "nombre",
            "provincia",
            "comarca",
            "latitud",
            "longitud",
            "geom",
            "hidratado",
            "fecha_hidratacion",
            "created_at",
        }
        expected_metricas_cols = {
            "codigo_ine",
            "distancia_carretera_km",
            "distancia_recurso_hidrico_km",
            "cobertura_fibra_pct",
            "cobertura_movil_pct",
            "fecha_actualizacion",
        }

        municipio_orm_cols = municipio_orm["columns"]
        metrica_orm_cols = metrica_orm["columns"]
        self.assertTrue(expected_municipios_cols.issubset(municipio_orm_cols.keys()))
        self.assertTrue(expected_metricas_cols.issubset(metrica_orm_cols.keys()))
        self.assertEqual(set(municipio_orm_cols.keys()), set(municipios_sql.keys()))
        self.assertEqual(set(metrica_orm_cols.keys()), set(metricas_sql.keys()))

        def _has_true_kw(call: ast.Call, kw_name: str) -> bool:
            return any(
                kw.arg == kw_name and isinstance(kw.value, ast.Constant) and kw.value.value is True
                for kw in call.keywords
            )

        self.assertTrue(_has_true_kw(municipio_orm_cols["codigo_ine"], "primary_key"))
        self.assertIn("PRIMARY KEY", municipios_sql["codigo_ine"].upper())
        self.assertTrue(
            any(
                isinstance(arg, ast.Call) and _call_name(arg.func) == "PuntoWGS84"
                for arg in municipio_orm_cols["geom"].args
            )
        )
        self.assertRegex(municipios_sql["geom"], r"geometry\(\s*Point\s*,\s*4326\s*\)")

        self.assertTrue(_has_true_kw(metrica_orm_cols["codigo_ine"], "primary_key"))
        self.assertIn("PRIMARY KEY", metricas_sql["codigo_ine"].upper())
        self.assertTrue(
            any(
                isinstance(arg, ast.Call)
                and _call_name(arg.func) == "ForeignKey"
                and arg.args
                and isinstance(arg.args[0], ast.Constant)
                and arg.args[0].value == "municipios.codigo_ine"
                for arg in metrica_orm_cols["codigo_ine"].args
            )
        )
        self.assertRegex(
            metricas_sql["codigo_ine"],
            r"(?i)REFERENCES\s+municipios\s*\(\s*codigo_ine\s*\)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
