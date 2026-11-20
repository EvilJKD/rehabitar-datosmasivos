"""
Suite de Pruebas de Integración de la PoC Re-Habitar (P1 + P2 + P3 + P4 + P5 + Mediador + Esquema).
Verifica:
  1. Estructura DDL completa en `db/schema.sql` (6 tablas Sección 7.1, PKs Citus, índices GiST).
  2. Orquestador híbrido inicial `etl/run_all.py` (códigos semilla y flujo P1 -> P2 -> P3 -> P4).
  3. Mediador `backend/main.py`: hidratación bajo demanda, fusión en memoria (Sección 7.3)
     con el caso real de referencia de Madarcos (`28078`, WLC = 96.05 VERDE) y las 4 Consultas (Sección 6.5).
"""

import os
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
import run_all  # noqa: E402
from services import p5_cartociudad  # noqa: E402


class TestSchemaAndOrchestrator(unittest.TestCase):
    def test_schema_sql_contains_all_6_citus_ready_tables_and_gist_indexes(self):
        schema_path = os.path.join(REPO_ROOT, "db", "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as fh:
            ddl = fh.read()

        self.assertIn("CREATE EXTENSION IF NOT EXISTS postgis;", ddl)
        for tabla in (
            "CREATE TABLE IF NOT EXISTS municipios",
            "CREATE TABLE IF NOT EXISTS demografia_anual",
            "CREATE TABLE IF NOT EXISTS metricas_infraestructura",
            "CREATE TABLE IF NOT EXISTS centros_sanitarios",
            "CREATE TABLE IF NOT EXISTS convocatorias",
            "CREATE TABLE IF NOT EXISTS convocatoria_municipio",
        ):
            self.assertIn(tabla, ddl)

        # Claves primarias compuestas Citus-Ready con codigo_ine primero
        self.assertIn("PRIMARY KEY (codigo_ine, anio)", ddl)
        self.assertIn("PRIMARY KEY (codigo_ine, codigo_bdns)", ddl)
        # Índices espaciales GiST
        self.assertIn("idx_municipios_geom", ddl)
        self.assertIn("idx_centros_sanitarios_geom", ddl)
        self.assertIn("idx_centros_urgencias_geom", ddl)
        # Regla estricta Sección 7.3: nunca almacenar tiempos de conducción de CartoCiudad en BD
        self.assertNotIn("tiempo_urg_min", ddl)
        self.assertNotIn("geometria_ruta_json", ddl)

    def test_run_all_seed_codes_aliases_and_pipeline_order(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("INITIAL_SEED_CODES", None)
            self.assertEqual(run_all.get_initial_seed_codes(), ["28078", "28069", "28027"])

        with patch.dict(os.environ, {"INITIAL_SEED_CODES": "28070, 28027, 28069, 28078"}):
            self.assertEqual(run_all.get_initial_seed_codes(), ["28069", "28027", "28078"])

        call_order: list[str] = []
        with patch.object(run_all, "wait_for_db"), patch.object(
            run_all, "get_initial_seed_codes", return_value=["28078", "28069"]
        ), patch.object(
            run_all,
            "run_etl_p1",
            side_effect=lambda seed_codes=None: call_order.append(f"p1:{seed_codes}") or "p1 ok",
        ), patch.object(
            run_all,
            "run_etl_p2",
            side_effect=lambda target_codes=None: call_order.append(f"p2:{target_codes}") or "p2 ok",
        ), patch.object(
            run_all,
            "run_etl_p3",
            side_effect=lambda: call_order.append("p3") or "p3 ok",
        ), patch.object(
            run_all,
            "run_etl_p4",
            side_effect=lambda target_codes=None: call_order.append(f"p4:{target_codes}") or "p4 ok",
        ):
            run_all.main()

        self.assertEqual(
            call_order,
            [
                "p1:['28078', '28069']",
                "p2:['28078', '28069']",
                "p3",
                "p4:['28078', '28069']",
            ],
        )


class TestMediatorAndPoCQueries(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        p5_cartociudad._CARTOCIUDAD_MEM_CACHE.clear()

    def tearDown(self):
        p5_cartociudad._CARTOCIUDAD_MEM_CACHE.clear()

    async def test_ensure_municipio_hydrated_cache_live_and_404(self):
        mock_db = AsyncMock()

        with patch.object(main, "get_municipio_by_ine", AsyncMock(return_value=None)):
            with self.assertRaises(main.HTTPException) as ctx:
                await main.ensure_municipio_hydrated(mock_db, "99999")
            self.assertEqual(ctx.exception.status_code, 404)

        cached_mun = {"codigo_ine": "28078", "hidratado": True, "fecha_actualizacion": date(2026, 11, 20)}
        with patch.object(main, "get_municipio_by_ine", AsyncMock(return_value=cached_mun)), patch.object(
            main, "hydrate_infraestructura_on_demand", AsyncMock()
        ) as m_p1:
            origen = await main.ensure_municipio_hydrated(mock_db, "28078", force_refresh=False)
        self.assertEqual(origen, "CACHE_POSTGRESQL")
        m_p1.assert_not_awaited()

        pending_mun = {"codigo_ine": "28069", "hidratado": False, "fecha_actualizacion": None}
        order: list[str] = []

        def rec(tag):
            order.append(tag)
            return 1

        with patch.object(main, "get_municipio_by_ine", AsyncMock(return_value=pending_mun)), patch.object(
            main, "hydrate_infraestructura_on_demand", AsyncMock(side_effect=lambda db, c: rec("P1"))
        ), patch.object(
            main, "hydrate_demografia_on_demand", AsyncMock(side_effect=lambda db, c: rec("P2"))
        ), patch.object(
            main,
            "hydrate_health_centers_on_demand",
            AsyncMock(side_effect=lambda db, codigo_ine=None, force_refresh=False: rec("P3")),
        ), patch.object(
            main, "hydrate_grants_on_demand", AsyncMock(side_effect=lambda db, c: rec("P4"))
        ):
            origen_live = await main.ensure_municipio_hydrated(mock_db, "28069")

        self.assertEqual(origen_live, "INGESTA_EN_VIVO_GUARDADA_EN_BD")
        self.assertEqual(order, ["P1", "P2", "P3", "P4"])

    async def test_consulta2_and_memory_fusion_madarcos_reference_case(self):
        """
        Verifica Consulta 2 y Fusión en Memoria (Sección 7.2 y 7.3) para Madarcos (28078):
        WLC = 96.05 (VERDE), ruta CartoCiudad a CS-28027 (12.2 min, 11.4 km), ayuda BDNS 921084.
        """
        madarcos = {
            "codigo_ine": "28078",
            "nombre": "Madarcos",
            "provincia": "Madrid",
            "comarca": "Sierra Norte",
            "latitud": 41.04870,
            "longitud": -3.58280,
            "hidratado": True,
            "fecha_hidratacion": None,
            "distancia_carretera_km": 0.00,
            "distancia_recurso_hidrico_km": 0.35,
            "cobertura_fibra_pct": 100.00,
            "cobertura_movil_pct": 98.50,
            "fecha_actualizacion": date(2026, 11, 20),
        }
        demo_mad = {
            "codigo_ine": "28078",
            "nombre": "Madarcos",
            "anio_actual": 2025,
            "poblacion_inicial_10a": 51,
            "poblacion_actual": 47,
            "variacion_10a_pct": -7.84,
            "variacion_5a_pct": 2.17,
            "preserva_masa_critica": False,
            "inercia_demografica": "COLAPSO",
            "serie_anual": [],
        }
        centers_mad = {
            "urgencias": {
                "id_centro": "CS-28027",
                "nombre": "Consultorio Local Buitrago del Lozoya",
                "tipo": "Centro de Salud / Urgencias",
                "tiene_urgencias": True,
                "municipio_nombre": "Buitrago del Lozoya",
                "direccion": "C/ Real 14",
                "horario": "24 Horas",
                "telefono": "918680116",
                "latitud": 40.99310,
                "longitud": -3.63840,
                "distancia_euclidea_km": 7.75,
            },
            "consultorio": None,
        }
        conv_mad = [
            {
                "codigo_bdns": "921084",
                "descripcion": "ORDEN DE DISP CRÉDITO 2026 CAMINOS RURALES MUNICIP DE MENOS DE 20.000 HB",
                "organo_nivel1": "AUTONOMICA",
                "organo_nivel2": "COMUNIDAD DE MADRID",
                "organo_nivel3": "CONSEJERÍA DE PRESIDENCIA",
                "organo_convocante": "CONSEJERÍA DE PRESIDENCIA",
                "fecha_recepcion": date(2026, 7, 23),
                "inicio_solicitud": None,
                "fin_solicitud": date(2026, 12, 31),
                "abierta": True,
                "presupuesto_total": 500000.0,
                "tipo_beneficiario": "AYUNTAMIENTOS",
                "finalidad": "Infraestructuras",
                "poblacion_max_objetivo": 20000,
                "url_bases": "https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/921084",
                "regla_asignacion": "umbral_poblacion",
            }
        ]
        route_mad = {
            "distancia_euclidea_km": 7.75,
            "distancia_carretera_km": 11.4,
            "tiempo_estimado_min": 12.2,
            "fuente_ruta": "API CartoCiudad IGN (Tiempo Real)",
            "geometria_ruta": [[41.0487, -3.5828], [40.9931, -3.6384]],
        }

        mock_db = AsyncMock()
        with patch.object(main, "get_municipio_by_ine", AsyncMock(return_value=madarcos)), patch.object(
            main, "get_demografia_serie_by_municipio", AsyncMock(return_value=demo_mad)
        ), patch.object(
            main, "get_nearest_health_centers_for_municipio", AsyncMock(return_value=centers_mad)
        ), patch.object(
            main, "get_convocatorias", AsyncMock(return_value=conv_mad)
        ), patch.object(
            main, "calculate_route_cartociudad", AsyncMock(return_value=route_mad)
        ):
            detail = await main.get_municipio_detail("28078", force_refresh=False, db=mock_db)

        self.assertEqual(detail.codigo_ine, "28078")
        self.assertEqual(detail.origen_datos, "CACHE_POSTGRESQL")
        self.assertAlmostEqual(detail.wlc.indice_wlc, 96.05, places=2)
        self.assertEqual(detail.wlc.semaforo, "VERDE")
        self.assertEqual(detail.urgencias_mas_cercana.id_centro, "CS-28027")
        self.assertEqual(detail.urgencias_mas_cercana.tiempo_estimado_min, 12.2)
        self.assertEqual(detail.urgencias_mas_cercana.distancia_carretera_km, 11.4)
        self.assertEqual(detail.convocatorias[0].codigo_bdns, "921084")
        self.assertEqual(detail.convocatorias[0].regla_asignacion, "umbral_poblacion")

    async def test_consulta1_consulta3_consulta4_and_health_check(self):
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
                "distancia_carretera_km": 0.5,
                "distancia_recurso_hidrico_km": 0.4,
                "cobertura_fibra_pct": 15.0,  # Baja fibra: excluido en Consulta 1
                "cobertura_movil_pct": 80.0,
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
            "28118": {"poblacion_actual": 90, "variacion_10a_pct": -4.0},
        }
        health_all = {
            "28078": {"id_centro": "CS-28027", "latitud": 40.9931, "longitud": -3.6384},
            "28118": {"id_centro": "CS-28027", "latitud": 40.9931, "longitud": -3.6384},
        }
        grants_all = {
            "28078": {"num_ayudas_abiertas": 2, "num_ayudas_total": 2, "presupuesto_abiertas": 500000.0}
        }

        mock_db = AsyncMock()
        res_health = MagicMock()
        res_health.mappings.return_value.first.return_value = {"total": 179, "hidratados": 2}
        mock_db.execute.return_value = res_health

        hc = await main.health_check(db=mock_db)
        self.assertEqual(hc["total_municipios"], 179)
        self.assertEqual(hc["municipios_hidratados"], 2)

        with patch.object(main, "get_all_municipios_base", AsyncMock(return_value=municipios_base)), patch.object(
            main, "get_demografia_summary_all", AsyncMock(return_value=demo_summary)
        ), patch.object(
            main, "get_nearest_emergency_all", AsyncMock(return_value=health_all)
        ), patch.object(
            main, "get_grants_summary_all", AsyncMock(return_value=grants_all)
        ):
            # Consulta 1: WLC >= 75 y fibra >= 50%
            c1 = await main.list_municipios(min_wlc=75.0, requiere_fibra=True, min_fibra_pct=50.0, db=mock_db)
            pendientes = await main.list_municipios(semaforo="PENDIENTE", db=mock_db)
            con_ayuda = await main.list_municipios(con_ayuda_abierta=True, db=mock_db)

        self.assertEqual([m.codigo_ine for m in c1], ["28078"])
        self.assertEqual([m.codigo_ine for m in pendientes], ["28069"])
        self.assertEqual([m.codigo_ine for m in con_ayuda], ["28078"])

        # Consulta 3: demografía enriquecida con P1, P3 y P4
        with patch.object(main, "ensure_municipio_hydrated", AsyncMock(return_value="CACHE_POSTGRESQL")), patch.object(
            main, "get_municipio_by_ine", AsyncMock(return_value=municipios_base[0])
        ), patch.object(
            main,
            "get_nearest_health_centers_for_municipio",
            AsyncMock(return_value={"urgencias": {"distancia_euclidea_km": 7.75}, "consultorio": None}),
        ), patch.object(
            main, "get_num_ayudas_abiertas", AsyncMock(return_value=2)
        ), patch.object(
            main,
            "get_demografia_serie_by_municipio",
            AsyncMock(
                return_value={
                    "codigo_ine": "28078",
                    "nombre": "Madarcos",
                    "poblacion_inicial_10a": 51,
                    "poblacion_actual": 47,
                    "variacion_10a_pct": -7.84,
                    "cobertura_fibra_pct": 100.0,
                    "distancia_urgencias_km": 7.75,
                    "num_ayudas_abiertas": 2,
                    "serie_anual": [{"anio": 2015, "poblacion": 51}, {"anio": 2025, "poblacion": 47}],
                }
            ),
        ):
            c3 = await main.get_municipio_demografia("28078", db=mock_db)

        self.assertEqual(c3.codigo_ine, "28078")
        self.assertEqual(c3.cobertura_fibra_pct, 100.0)
        self.assertEqual(c3.distancia_urgencias_km, 7.75)
        self.assertEqual(c3.num_ayudas_abiertas, 2)
        self.assertEqual(len(c3.serie_anual), 2)

        # Consulta 4 y trigger POST ingest
        with patch.object(main, "get_convocatorias", AsyncMock(return_value=[{"codigo_bdns": "921084"}])) as m_c4:
            c4 = await main.list_convocatorias(codigo_ine="28078", categoria="Infra", solo_abiertas=True, db=mock_db)
        self.assertEqual(c4[0]["codigo_bdns"], "921084")
        m_c4.assert_awaited_once_with(mock_db, codigo_ine="28078", categoria="Infra", solo_abiertas=True)

        with patch.object(main, "get_municipio_detail", AsyncMock(return_value="detail_ok")) as m_det:
            ing = await main.trigger_municipio_ingestion("28078", db=mock_db)
        self.assertEqual(ing, "detail_ok")
        m_det.assert_awaited_once_with(
            codigo_ine="28078",
            force_refresh=True,
            w_demo=None,
            w_health=None,
            w_grants=None,
            w_infra=None,
            db=mock_db,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
