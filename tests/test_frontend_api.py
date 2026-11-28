"""
Suite de Pruebas del API REST expuesto al Frontend (`backend/main.py`) y
auditoría de uso exclusivo de APIs HTTP en todas las fuentes (P1-P5).
"""

import os
import re
import sys
import unittest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(TESTS_DIR, ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
ETL_DIR = os.path.join(REPO_ROOT, "etl")
for ruta in (BACKEND_DIR, ETL_DIR):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

import main  # noqa: E402
from services import p5_cartociudad  # noqa: E402


def _registered_endpoints() -> set[tuple[str, str]]:
    endpoints: set[tuple[str, str]] = set()
    for route in getattr(main.app, "routes", []):
        if isinstance(route, dict):
            endpoints.add((route["method"], route["path"]))
        else:
            path = getattr(route, "path", None)
            for method in getattr(route, "methods", set()) or set():
                if path:
                    endpoints.add((method, path))
    return endpoints


class TestFrontendAPIContracts(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        p5_cartociudad._CARTOCIUDAD_MEM_CACHE.clear()

    def tearDown(self):
        p5_cartociudad._CARTOCIUDAD_MEM_CACHE.clear()

    def test_all_expected_frontend_routes_are_registered(self):
        endpoints = _registered_endpoints()
        expected = {
            ("GET", "/api/health"),
            ("GET", "/api/municipios"),
            ("GET", "/api/municipios/{codigo_ine}"),
            ("POST", "/api/municipios/{codigo_ine}/ingest"),
            ("GET", "/api/municipios/{codigo_ine}/demografia"),
            ("GET", "/api/convocatorias"),
            ("GET", "/api/centros-sanitarios"),
        }
        self.assertTrue(expected.issubset(endpoints), f"Faltan rutas: {expected - endpoints}")

    async def test_health_endpoint_contract(self):
        mock_db = AsyncMock()
        res = MagicMock()
        res.mappings.return_value.first.return_value = {"total": 179, "hidratados": 3}
        mock_db.execute.return_value = res

        payload = await main.health_check(db=mock_db)
        self.assertEqual(
            payload,
            {
                "status": "ok",
                "database": "postgresql+postgis",
                "total_municipios": 179,
                "municipios_hidratados": 3,
            },
        )

    async def test_list_municipios_filters_traffic_lights_and_dynamic_weights(self):
        municipios_base = [
            {
                "codigo_ine": "28078",
                "nombre": "Madarcos",
                "provincia": "Madrid",
                "comarca": "Sierra Norte",
                "latitud": 41.0487,
                "longitud": -3.5828,
                "hidratado": True,
                "distancia_carretera_km": 0.0,
                "distancia_recurso_hidrico_km": 0.35,
                "cobertura_fibra_pct": 100.0,
                "cobertura_movil_pct": 98.5,
                "fecha_actualizacion": date(2026, 11, 20),
            },
            {
                "codigo_ine": "28118",
                "nombre": "Puebla de la Sierra",
                "provincia": "Madrid",
                "comarca": "Sierra Norte",
                "latitud": 41.0125,
                "longitud": -3.4445,
                "hidratado": True,
                "distancia_carretera_km": 6.0,
                "distancia_recurso_hidrico_km": 2.0,
                "cobertura_fibra_pct": 25.0,
                "cobertura_movil_pct": 60.0,
                "fecha_actualizacion": date(2026, 11, 20),
            },
            {
                "codigo_ine": "28094",
                "nombre": "Navarredonda y San Mamés",
                "provincia": "Madrid",
                "comarca": "Sierra Norte",
                "latitud": 40.99,
                "longitud": -3.71,
                "hidratado": True,
                "distancia_carretera_km": 14.0,
                "distancia_recurso_hidrico_km": 9.0,
                "cobertura_fibra_pct": 10.0,
                "cobertura_movil_pct": 20.0,
                "fecha_actualizacion": date(2026, 11, 20),
            },
            {
                "codigo_ine": "28069",
                "nombre": "La Hiruela",
                "provincia": "Madrid",
                "comarca": "Sierra Norte",
                "latitud": 41.0767,
                "longitud": -3.4511,
                "hidratado": False,
                "distancia_carretera_km": None,
                "distancia_recurso_hidrico_km": None,
                "cobertura_fibra_pct": None,
                "cobertura_movil_pct": None,
                "fecha_actualizacion": None,
            },
        ]
        demo_summary = {
            "28078": {"poblacion_actual": 47, "variacion_10a_pct": -7.84},
            "28118": {"poblacion_actual": 90, "variacion_10a_pct": -10.0},
            "28094": {"poblacion_actual": 20, "variacion_10a_pct": -35.0},
        }
        health_all = {
            "28078": {"id_centro": "CS-28027", "latitud": 40.9931, "longitud": -3.6384},
            "28118": {"id_centro": "CS-28027", "latitud": 40.9931, "longitud": -3.6384},
            "28094": {"id_centro": "CS-28027", "latitud": 41.35, "longitud": -3.20},
        }
        grants_all = {
            "28078": {"num_ayudas_abiertas": 2, "num_ayudas_total": 2, "presupuesto_abiertas": 500000.0},
            "28118": {"num_ayudas_abiertas": 1, "num_ayudas_total": 1, "presupuesto_abiertas": 100000.0},
        }

        mock_db = AsyncMock()
        with patch.object(main, "get_all_municipios_base", AsyncMock(return_value=municipios_base)), patch.object(
            main, "get_demografia_summary_all", AsyncMock(return_value=demo_summary)
        ), patch.object(
            main, "get_nearest_emergency_all", AsyncMock(return_value=health_all)
        ), patch.object(
            main, "get_grants_summary_all", AsyncMock(return_value=grants_all)
        ):
            todos = await main.list_municipios(db=mock_db)
            verdes = await main.list_municipios(semaforo="VERDE", db=mock_db)
            ambares = await main.list_municipios(semaforo="AMBAR", db=mock_db)
            rojos = await main.list_municipios(semaforo="ROJO", db=mock_db)
            pendientes = await main.list_municipios(semaforo="PENDIENTE", db=mock_db)
            sin_ayuda = await main.list_municipios(con_ayuda_abierta=False, db=mock_db)
            pesos_legacy = await main.list_municipios(
                w_demo=0.5, w_health=0.2, w_grants=0.1, w_infra=0.2, db=mock_db
            )
            pesos_5p = await main.list_municipios(
                w_carretera=0.30,
                w_sanidad=0.25,
                w_conectividad=0.20,
                w_hidrico=0.10,
                w_demografia=0.15,
                db=mock_db,
            )

        self.assertEqual(len(todos), 4)
        self.assertEqual([m.codigo_ine for m in verdes], ["28078"])
        self.assertEqual([m.codigo_ine for m in ambares], ["28118"])
        self.assertEqual([m.codigo_ine for m in rojos], ["28094"])
        self.assertEqual([m.codigo_ine for m in pendientes], ["28069"])
        self.assertEqual({m.codigo_ine for m in sin_ayuda}, {"28094", "28069"})

        mad_legacy = next(m for m in pesos_legacy if m.codigo_ine == "28078")
        self.assertAlmostEqual(sum(mad_legacy.wlc.pesos_aplicados.values()), 1.0, places=3)
        mad_5p = next(m for m in pesos_5p if m.codigo_ine == "28078")
        self.assertAlmostEqual(mad_5p.wlc.pesos_aplicados["carretera"], 0.30, places=3)
        self.assertAlmostEqual(mad_5p.wlc.pesos_aplicados["demografia"], 0.15, places=3)

    async def test_municipio_detail_on_demand_hydration_and_cartociudad_fallback(self):
        mock_db = AsyncMock()
        hiruela_pending = {
            "codigo_ine": "28069",
            "nombre": "La Hiruela",
            "provincia": "Madrid",
            "comarca": "Sierra Norte",
            "latitud": 41.0767,
            "longitud": -3.4511,
            "hidratado": False,
            "fecha_actualizacion": None,
        }
        hiruela_hydrated = {
            **hiruela_pending,
            "hidratado": True,
            "distancia_carretera_km": 0.2,
            "distancia_recurso_hidrico_km": 0.5,
            "cobertura_fibra_pct": 85.0,
            "cobertura_movil_pct": 90.0,
            "fecha_actualizacion": date(2026, 11, 20),
        }
        demo_hir = {
            "codigo_ine": "28069",
            "nombre": "La Hiruela",
            "poblacion_inicial_10a": 54,
            "poblacion_actual": 88,
            "variacion_10a_pct": 62.96,
            "preserva_masa_critica": False,
            "inercia_demografica": "RECUPERACION",
            "serie_anual": [],
        }
        centers_hir = {
            "urgencias": {
                "id_centro": "CS-28027",
                "nombre": "Consultorio Local Buitrago del Lozoya",
                "tipo": "Centro de Salud / Urgencias",
                "tiene_urgencias": True,
                "latitud": 40.9931,
                "longitud": -3.6384,
                "distancia_euclidea_km": 18.24,
            },
            "consultorio": None,
        }

        with patch.object(
            main, "get_municipio_by_ine", AsyncMock(side_effect=[hiruela_pending, hiruela_hydrated])
        ), patch.object(
            main, "hydrate_infraestructura_on_demand", AsyncMock()
        ) as m_p1, patch.object(
            main, "hydrate_demografia_on_demand", AsyncMock()
        ) as m_p2, patch.object(
            main, "hydrate_health_centers_on_demand", AsyncMock()
        ) as m_p3, patch.object(
            main, "hydrate_grants_on_demand", AsyncMock()
        ) as m_p4, patch.object(
            main, "get_demografia_serie_by_municipio", AsyncMock(return_value=demo_hir)
        ), patch.object(
            main, "get_nearest_health_centers_for_municipio", AsyncMock(return_value=centers_hir)
        ), patch.object(
            main, "get_convocatorias", AsyncMock(return_value=[])
        ), patch.object(
            p5_cartociudad, "_request_cartociudad", AsyncMock(side_effect=RuntimeError("Timeout"))
        ):
            detail = await main.get_municipio_detail("28069", db=mock_db)

        m_p1.assert_awaited_once()
        m_p2.assert_awaited_once()
        m_p3.assert_awaited_once()
        m_p4.assert_awaited_once()
        self.assertEqual(detail.origen_datos, "INGESTA_EN_VIVO_GUARDADA_EN_BD")
        self.assertEqual(detail.urgencias_mas_cercana.fuente_ruta, "Fallback Haversine (45 km/h)")
        self.assertGreaterEqual(len(detail.urgencias_mas_cercana.geometria_ruta), 2)
        self.assertGreater(detail.wlc.indice_wlc, 70.0)

        with patch.object(main, "get_municipio_by_ine", AsyncMock(return_value=None)):
            with self.assertRaises(main.HTTPException) as ctx:
                await main.get_municipio_detail("99999", db=mock_db)
            self.assertEqual(ctx.exception.status_code, 404)

    async def test_demografia_convocatorias_and_centros_sanitarios_endpoints(self):
        mock_db = AsyncMock()

        with patch.object(main, "ensure_municipio_hydrated", AsyncMock(return_value="CACHE_POSTGRESQL")), patch.object(
            main, "get_municipio_by_ine", AsyncMock(return_value={"codigo_ine": "28078", "cobertura_fibra_pct": 100.0})
        ), patch.object(
            main, "get_nearest_health_centers_for_municipio", AsyncMock(return_value={"urgencias": None, "consultorio": None})
        ), patch.object(
            main, "get_num_ayudas_abiertas", AsyncMock(return_value=0)
        ), patch.object(
            main, "get_demografia_serie_by_municipio", AsyncMock(return_value=None)
        ):
            with self.assertRaises(main.HTTPException) as ctx:
                await main.get_municipio_demografia("28078", db=mock_db)
            self.assertEqual(ctx.exception.status_code, 404)

        with patch.object(main, "get_convocatorias", AsyncMock(return_value=[])) as m_conv:
            await main.list_convocatorias(
                codigo_ine="28078", categoria="Vivienda", solo_abiertas=True, abierta=False, db=mock_db
            )
        m_conv.assert_awaited_once_with(
            mock_db, codigo_ine="28078", categoria="Vivienda", solo_abiertas=False
        )

        with patch.object(
            main, "list_centros_sanitarios_service", AsyncMock(return_value=[{"id_centro": "CS-28027"}])
        ) as m_cs:
            centros = await main.list_centros_sanitarios(
                solo_urgencias=True, municipio_nombre="Buitrago", force_refresh=True, db=mock_db
            )
        self.assertEqual(centros[0]["id_centro"], "CS-28027")
        m_cs.assert_awaited_once_with(
            mock_db, solo_urgencias=True, municipio_nombre="Buitrago", force_refresh=True
        )

    async def test_trigger_municipio_ingestion_and_demografia_happy_path_contract(self):
        mock_db = AsyncMock()
        sentinel_detail = MagicMock(name="MunicipioDetailSchema")
        with patch.object(
            main, "get_municipio_detail", AsyncMock(return_value=sentinel_detail)
        ) as m_detail:
            result = await main.trigger_municipio_ingestion("28078", db=mock_db)

        self.assertIs(result, sentinel_detail)
        m_detail.assert_awaited_once_with(
            codigo_ine="28078",
            force_refresh=True,
            w_demo=None,
            w_health=None,
            w_grants=None,
            w_infra=None,
            db=mock_db,
        )

        serie_payload = {
            "codigo_ine": "28078",
            "nombre": "Madarcos",
            "poblacion_inicial_10a": 51,
            "poblacion_actual": 47,
            "variacion_10a_pct": -7.84,
            "cobertura_fibra_pct": 100.0,
            "distancia_urgencias_km": 7.73,
            "num_ayudas_abiertas": 2,
            "serie_anual": [
                {
                    "anio": 2015,
                    "poblacion": 51,
                    "poblacion_mayor_65": None,
                    "poblacion_menor_15": None,
                    "tasa_envejecimiento": None,
                },
                {
                    "anio": 2025,
                    "poblacion": 47,
                    "poblacion_mayor_65": 18,
                    "poblacion_menor_15": 4,
                    "tasa_envejecimiento": 38.3,
                },
            ],
        }
        with patch.object(
            main, "ensure_municipio_hydrated", AsyncMock(return_value="CACHE_POSTGRESQL")
        ), patch.object(
            main,
            "get_municipio_by_ine",
            AsyncMock(return_value={"codigo_ine": "28078", "cobertura_fibra_pct": 100.0}),
        ), patch.object(
            main,
            "get_nearest_health_centers_for_municipio",
            AsyncMock(return_value={"urgencias": {"distancia_euclidea_km": 7.73}, "consultorio": None}),
        ), patch.object(
            main, "get_num_ayudas_abiertas", AsyncMock(return_value=2)
        ), patch.object(
            main, "get_demografia_serie_by_municipio", AsyncMock(return_value=serie_payload)
        ):
            demografia = await main.get_municipio_demografia("28078", db=mock_db)

        self.assertEqual(demografia.codigo_ine, "28078")
        self.assertEqual(demografia.poblacion_actual, 47)
        self.assertEqual(demografia.cobertura_fibra_pct, 100.0)
        self.assertEqual(demografia.distancia_urgencias_km, 7.73)
        self.assertEqual(demografia.num_ayudas_abiertas, 2)
        self.assertEqual(len(demografia.serie_anual), 2)
        self.assertEqual(demografia.serie_anual[1].tasa_envejecimiento, 38.3)


class TestAllSourcesUseHTTPAPIsOnly(unittest.TestCase):
    def test_all_sources_use_http_apis_without_local_text_files(self):
        source_files = {
            os.path.join(ETL_DIR, "p1_ngbe", "sources.py"): (
                "https://www.ign.es/",
                "https://digital.gob.es/",
                "https://api-features.idee.es/collections",
            ),
            os.path.join(ETL_DIR, "p2_ine", "etl_ine.py"): (
                "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA",
            ),
            os.path.join(ETL_DIR, "p3_cam", "etl_sanidad.py"): (
                "https://datos.comunidad.madrid/catalogo/api/3/action/",
            ),
            os.path.join(ETL_DIR, "p4_bdns", "etl_bdns.py"): (
                "https://www.infosubvenciones.es/bdnstrans/api/convocatorias",
            ),
            os.path.join(BACKEND_DIR, "services", "p5_cartociudad.py"): (
                "https://www.cartociudad.es/services/api/route",
            ),
        }
        forbidden_patterns = (
            (r"\bopen\(", "open("),
            (r"\bread_bytes\(", "read_bytes("),
            (r"\bread_text\(", "read_text("),
            (r"data/raw", "data/raw"),
            (r"\bP1_IGN_FILE\b", "P1_IGN_FILE"),
            (r"\bP1_COBERTURA_FILE\b", "P1_COBERTURA_FILE"),
        )

        for path, required_urls in source_files.items():
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            for url in required_urls:
                self.assertIn(url, content, f"Falta endpoint API {url} en {path}")
            for pattern, label in forbidden_patterns:
                self.assertIsNone(
                    re.search(pattern, content),
                    f"La fuente {path} no debe leer ficheros locales de texto ({label})",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
