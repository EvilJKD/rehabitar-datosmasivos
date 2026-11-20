"""
Suite de Pruebas Unitarias del Módulo P2: Demografía INE Tempus (Tabla 2881) y Consulta 3
(`etl/p2_ine/etl_ine.py`, `backend/services/p2_demo_service.py`, `DemografiaSerieResponseSchema`).
"""

import os
import sys
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
from services import p2_demo_service as p2  # noqa: E402


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


class TestP2DemoServiceConsulta3(unittest.IsolatedAsyncioTestCase):
    def test_calcular_variacion_and_inertia_classification(self):
        self.assertEqual(p2.calcular_variacion_pct(47, 51), -7.84)
        self.assertIsNone(p2.calcular_variacion_pct(47, 0))
        self.assertIsNone(p2.calcular_variacion_pct(47, None))

        self.assertEqual(p2.classify_demographic_inertia(None, 2.0, None, 120), p2.SIN_DATOS)
        self.assertEqual(p2.classify_demographic_inertia(-22.0, 5.0, None, 300), p2.COLAPSO)
        self.assertEqual(p2.classify_demographic_inertia(-7.84, 2.17, None, 47), p2.COLAPSO)
        self.assertEqual(p2.classify_demographic_inertia(-10.0, 4.0, None, 200), p2.REPUNTE_RECIENTE)
        self.assertEqual(p2.classify_demographic_inertia(-8.0, -2.0, None, 200), p2.DECLIVE)
        self.assertEqual(p2.classify_demographic_inertia(1.5, -1.0, None, 200), p2.ESTANCAMIENTO)
        self.assertEqual(p2.classify_demographic_inertia(9.0, -1.0, None, 200), p2.ESTANCAMIENTO)
        self.assertEqual(p2.classify_demographic_inertia(9.06, 4.5, None, 2034), p2.RECUPERACION)

        self.assertFalse(p2.preserva_masa_critica(47))
        self.assertFalse(p2.preserva_masa_critica(None))
        self.assertTrue(p2.preserva_masa_critica(100))

    def test_calcular_indicadores_madarcos_reference_case(self):
        # Caso de referencia Madarcos (Sección 7.2): 51 -> 46 -> 47 (-7.84%)
        ind = p2.calcular_indicadores({2015: 51, 2020: 46, 2025: 47})
        self.assertEqual(ind["poblacion_inicial_10a"], 51)
        self.assertEqual(ind["poblacion_actual"], 47)
        self.assertEqual(ind["variacion_10a_pct"], -7.84)
        self.assertFalse(ind["preserva_masa_critica"])
        self.assertEqual(ind["inercia_demografica"], p2.COLAPSO)

    async def test_hydrate_summary_and_serie_services(self):
        # 1) Ya existe en BD -> hydrate devuelve 0 sin invocar ETL
        mock_db = AsyncMock()
        res_exists = MagicMock()
        res_exists.scalar.return_value = True
        mock_db.execute.return_value = res_exists
        self.assertEqual(await p2.hydrate_demografia_on_demand(mock_db, "28078"), 0)

        # 2) No existe -> invoca ETL
        res_missing = MagicMock()
        res_missing.scalar.return_value = False
        mock_db.execute.return_value = res_missing
        with patch("p2_ine.etl_ine.ingest_ine_for_municipio", return_value=11) as mock_ing:
            inserted = await p2.hydrate_demografia_on_demand(mock_db, "28069")
        self.assertEqual(inserted, 11)
        mock_ing.assert_called_once_with("28069")

        # 3) Summary all + serie by municipio
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
        schema = DemografiaSerieResponseSchema(
            **{
                **{k: v for k, v in serie.items() if k != "serie_anual"},
                "serie_anual": [DemografiaPuntoAnualSchema(**p) for p in serie["serie_anual"]],
            }
        )
        self.assertEqual(schema.nombre, "Madarcos")
        self.assertEqual(schema.variacion_10a_pct, -7.84)
        self.assertEqual(schema.cobertura_fibra_pct, 100.0)
        self.assertEqual(len(schema.serie_anual), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
