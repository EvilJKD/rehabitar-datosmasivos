"""
Suite de Pruebas Unitarias y de Integración para el Módulo P5:
- Servicio P5.1: Integración Virtual en Tiempo Real con CartoCiudad + Fallback Haversine (`p5_cartociudad.py`)
- Servicio P5.2: Motor Multicriterio WLC (0-100) y Filtro Consulta 1 (`p5_wlc_engine.py`)
- Schemas Pydantic: `WLCBreakdownSchema` y `RutaSanitariaSchema` (`schemas/domain.py`)

Ejecución:
    python -m unittest discover -s re-habitar-poc/tests -p "test_p5_wlc_and_cartociudad.py" -v
"""

import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(TESTS_DIR, ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from schemas.domain import RutaSanitariaSchema, WLCBreakdownSchema  # noqa: E402
from services import p5_cartociudad, p5_wlc_engine  # noqa: E402

# Coordenadas reales de referencia (Sección 7.2 de la Propuesta):
# Madarcos -> Consultorio Local Buitrago del Lozoya (CS-28027)
MADARCOS_LAT, MADARCOS_LON = 41.04870, -3.58280
BUITRAGO_LAT, BUITRAGO_LON = 40.99310, -3.63840


class TestP5CartoCiudadService(unittest.IsolatedAsyncioTestCase):
    """Pruebas unitarias e integración resiliente para P5.1 (CartoCiudad y Fallback Haversine)."""

    def setUp(self):
        p5_cartociudad._CARTOCIUDAD_MEM_CACHE.clear()

    def tearDown(self):
        p5_cartociudad._CARTOCIUDAD_MEM_CACHE.clear()

    def test_haversine_km_madarcos_buitrago(self):
        """Verifica la distancia ortodrómica Haversine entre Madarcos y Buitrago del Lozoya."""
        self.assertEqual(
            p5_cartociudad.haversine_km(MADARCOS_LAT, MADARCOS_LON, MADARCOS_LAT, MADARCOS_LON),
            0.0,
        )
        dist = p5_cartociudad.haversine_km(
            MADARCOS_LAT, MADARCOS_LON, BUITRAGO_LAT, BUITRAGO_LON
        )
        self.assertGreater(dist, 7.0)
        self.assertLess(dist, 8.5)

    def test_build_curved_mountain_polyline(self):
        """Verifica número de puntos, coincidencia exacta en extremos y curvatura intermedia."""
        poly = p5_cartociudad.build_curved_mountain_polyline(
            MADARCOS_LAT, MADARCOS_LON, BUITRAGO_LAT, BUITRAGO_LON, steps=12
        )
        self.assertEqual(len(poly), 13)
        self.assertEqual(poly[0], [MADARCOS_LAT, MADARCOS_LON])
        self.assertEqual(poly[-1], [BUITRAGO_LAT, BUITRAGO_LON])

        # El punto medio debe desviarse de la recta exacta por la curvatura de montaña
        mid_linear_lat = (MADARCOS_LAT + BUITRAGO_LAT) / 2.0
        self.assertNotAlmostEqual(poly[6][0], mid_linear_lat, places=5)

    def test_compute_fallback_route(self):
        """Verifica factor de sinuosidad 1.32x, velocidad rural 45 km/h y estructura de salida."""
        route = p5_cartociudad.compute_fallback_route(
            MADARCOS_LAT, MADARCOS_LON, BUITRAGO_LAT, BUITRAGO_LON
        )
        expected_eucl = p5_cartociudad.haversine_km(
            MADARCOS_LAT, MADARCOS_LON, BUITRAGO_LAT, BUITRAGO_LON
        )
        expected_road = round(expected_eucl * 1.32, 2)
        expected_min = round((expected_road / 45.0) * 60.0, 2)

        self.assertEqual(route["distancia_euclidea_km"], expected_eucl)
        self.assertEqual(route["distancia_carretera_km"], expected_road)
        self.assertEqual(route["tiempo_estimado_min"], expected_min)
        self.assertIn("Fallback", route["fuente_ruta"])
        self.assertEqual(len(route["geometria_ruta"]), 13)

    async def test_calculate_route_cartociudad_wkt_cache_and_fallback(self):
        """
        Verifica el parseo de la respuesta JSON+WKT de CartoCiudad (metros->km, ms->min,
        inversión [lon, lat]->[lat, lon]), la caché efímera en RAM y el fallback ante error.
        """
        mock_payload = {
            "distance": 11400.0,
            "time": 732000.0,
            "geom": "LINESTRING(-3.58280 41.04870, -3.61050 41.02100, -3.63840 40.99310)",
        }

        with patch.object(
            p5_cartociudad, "_request_cartociudad", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = mock_payload

            r1 = await p5_cartociudad.calculate_route_cartociudad(
                MADARCOS_LAT, MADARCOS_LON, BUITRAGO_LAT, BUITRAGO_LON
            )
            # Segunda llamada sin force_refresh debe usar la caché efímera en RAM
            r2 = await p5_cartociudad.calculate_route_cartociudad(
                MADARCOS_LAT, MADARCOS_LON, BUITRAGO_LAT, BUITRAGO_LON
            )
            # Con force_refresh=True debe volver a consultar la API
            r3 = await p5_cartociudad.calculate_route_cartociudad(
                MADARCOS_LAT, MADARCOS_LON, BUITRAGO_LAT, BUITRAGO_LON, force_refresh=True
            )

            self.assertEqual(mock_req.await_count, 2)
            self.assertAlmostEqual(r1["distancia_carretera_km"], 11.40, places=2)
            self.assertAlmostEqual(r1["tiempo_estimado_min"], 12.20, places=2)
            self.assertEqual(r1["fuente_ruta"], "API CartoCiudad IGN (Tiempo Real)")
            self.assertEqual(r1["geometria_ruta"][0], [41.04870, -3.58280])
            self.assertEqual(r1["geometria_ruta"][-1], [40.99310, -3.63840])
            self.assertEqual(r2["tiempo_estimado_min"], r1["tiempo_estimado_min"])
            self.assertEqual(r3["distancia_carretera_km"], 11.40)

        # Verificar soporte de MultiLineString GeoJSON
        geojson_geom = {
            "type": "MultiLineString",
            "coordinates": [
                [[-3.58280, 41.04870], [-3.61000, 41.02000]],
                [[-3.61000, 41.02000], [-3.63840, 40.99310]],
            ],
        }
        parsed_multi = p5_cartociudad._parse_cartociudad_geometry(geojson_geom)
        self.assertEqual(len(parsed_multi), 4)
        self.assertEqual(parsed_multi[0], [41.04870, -3.58280])

        # Verificar soporte de Google Encoded Polyline (formato real de `geom` en CartoCiudad IGN)
        parsed_poly = p5_cartociudad._parse_cartociudad_geometry("kgpyF|szTBB")
        self.assertEqual(parsed_poly, [[41.04838, -3.58223], [41.04836, -3.58225]])

        # Verificar que un payload con `found=False` se rechaza para activar el fallback
        self.assertIsNone(
            p5_cartociudad._parse_cartociudad_payload(
                {"found": False, "distance": 11400.0, "time": 732000.0},
                MADARCOS_LAT,
                MADARCOS_LON,
                BUITRAGO_LAT,
                BUITRAGO_LON,
            )
        )

        # Verificar activación automática de fallback ante timeout/excepción de red
        p5_cartociudad._CARTOCIUDAD_MEM_CACHE.clear()
        with patch.object(
            p5_cartociudad,
            "_request_cartociudad",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Timeout simulado CartoCiudad"),
        ):
            fallback = await p5_cartociudad.calculate_route_cartociudad(
                MADARCOS_LAT, MADARCOS_LON, BUITRAGO_LAT, BUITRAGO_LON
            )
        self.assertIn("Fallback", fallback["fuente_ruta"])
        self.assertGreater(fallback["distancia_carretera_km"], 0.0)
        self.assertGreater(fallback["tiempo_estimado_min"], 0.0)
        self.assertEqual(len(p5_cartociudad._CARTOCIUDAD_MEM_CACHE), 0)

    async def test_live_or_resilient_cartociudad_call(self):
        """
        Ejecuta una llamada real resiliente contra `https://www.cartociudad.es/services/api/route`:
        tanto si el servicio del IGN responde en vivo como si activa el fallback local,
        el contrato de retorno debe garantizar distancia > 0, tiempo > 0 y polilínea válida.
        """
        route = await p5_cartociudad.calculate_route_cartociudad(
            MADARCOS_LAT, MADARCOS_LON, BUITRAGO_LAT, BUITRAGO_LON, force_refresh=True
        )
        self.assertGreater(route["distancia_carretera_km"], 5.0)
        self.assertGreater(route["tiempo_estimado_min"], 5.0)
        self.assertGreaterEqual(len(route["geometria_ruta"]), 2)
        self.assertIn(
            route["fuente_ruta"],
            {"API CartoCiudad IGN (Tiempo Real)", "Fallback Haversine (45 km/h)"},
        )
        if route["fuente_ruta"] == "API CartoCiudad IGN (Tiempo Real)":
            self.assertGreater(len(route["geometria_ruta"]), 20)

    async def test_cartociudad_edge_cases_short_zero_geojson_and_invalid_strings(self):
        """
        Pruebas de regresión de auditoría P5.1:
        - Rutas cortas intra-municipales (<= 200 m / <= 10 s) en metros y milisegundos.
        - Rutas de distancia/tiempo 0.0 cuando origen y destino coinciden (y rechazo si distan > 50 m).
        - Parseo de cadenas JSON GeoJSON serializadas.
        - Rechazo de cadenas no válidas (`INVALID_GEOM`, `123456`) para evitar coordenadas (0, 0).
        """
        short_payload = {
            "found": True,
            "distance": 150.0,
            "time": 9500.0,
            "geom": "kgpyF|szTBB",
        }
        parsed_short = p5_cartociudad._parse_cartociudad_payload(
            short_payload, 40.9931, -3.6384, 40.9935, -3.6380
        )
        self.assertIsNotNone(parsed_short)
        self.assertEqual(parsed_short["distancia_carretera_km"], 0.15)
        self.assertEqual(parsed_short["tiempo_estimado_min"], 0.16)
        self.assertEqual(
            p5_wlc_engine.compute_proximidad_sanitaria_score(
                parsed_short["tiempo_estimado_min"]
            ),
            100.0,
        )

        # Origen y destino coincidentes -> distancia 0.0 / tiempo 0.0 válidos y cacheados
        with patch.object(
            p5_cartociudad, "_request_cartociudad", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = {"found": True, "distance": 0.0, "time": 0.0, "geom": ""}
            zero_route = await p5_cartociudad.calculate_route_cartociudad(
                BUITRAGO_LAT, BUITRAGO_LON, BUITRAGO_LAT, BUITRAGO_LON
            )
            self.assertEqual(zero_route["distancia_carretera_km"], 0.0)
            self.assertEqual(zero_route["tiempo_estimado_min"], 0.0)
            self.assertEqual(len(p5_cartociudad._CARTOCIUDAD_MEM_CACHE), 1)

        # Distancia 0.0 para puntos alejados sigue siendo inválida
        self.assertIsNone(
            p5_cartociudad._parse_cartociudad_payload(
                {"found": True, "distance": 0.0, "time": 0.0, "geom": ""},
                MADARCOS_LAT,
                MADARCOS_LON,
                BUITRAGO_LAT,
                BUITRAGO_LON,
            )
        )

        # Cadena GeoJSON serializada
        geojson_str = json.dumps(
            {
                "type": "LineString",
                "coordinates": [[MADARCOS_LON, MADARCOS_LAT], [BUITRAGO_LON, BUITRAGO_LAT]],
            }
        )
        self.assertEqual(
            p5_cartociudad._parse_cartociudad_geometry(geojson_str),
            [[MADARCOS_LAT, MADARCOS_LON], [BUITRAGO_LAT, BUITRAGO_LON]],
        )

        # Cadenas inválidas no deben producir vértices falsos en (0, 0)
        self.assertEqual(p5_cartociudad._parse_cartociudad_geometry("INVALID_GEOM"), [])
        self.assertEqual(p5_cartociudad._parse_cartociudad_geometry("123456"), [])
        parsed_bad_geom = p5_cartociudad._parse_cartociudad_payload(
            {"found": True, "distance": 11400.0, "time": 732000.0, "geom": "INVALID_GEOM"},
            MADARCOS_LAT,
            MADARCOS_LON,
            BUITRAGO_LAT,
            BUITRAGO_LON,
        )
        self.assertEqual(parsed_bad_geom["geometria_ruta"][0], [MADARCOS_LAT, MADARCOS_LON])
        self.assertEqual(parsed_bad_geom["geometria_ruta"][-1], [BUITRAGO_LAT, BUITRAGO_LON])


class TestP5WLCEngineAndSchemas(unittest.TestCase):
    """Pruebas unitarias para P5.2 (5 indicadores, WLC, Consulta 1 y Schemas Pydantic)."""

    def test_individual_indicator_scoring_functions(self):
        """Verifica la normalización 0-100 de los 5 parámetros de habitabilidad y `clamp`."""
        self.assertEqual(p5_wlc_engine.clamp(-10.0), 0.0)
        self.assertEqual(p5_wlc_engine.clamp(125.0), 100.0)
        self.assertEqual(p5_wlc_engine.clamp(42.5), 42.5)

        # Indicador 1: Acceso carretera asfaltada
        self.assertEqual(p5_wlc_engine.compute_acceso_carretera_score(0.0), 100.0)
        self.assertEqual(p5_wlc_engine.compute_acceso_carretera_score(7.5), 50.0)
        self.assertEqual(p5_wlc_engine.compute_acceso_carretera_score(15.0), 0.0)
        self.assertEqual(p5_wlc_engine.compute_acceso_carretera_score(25.0), 0.0)

        # Indicador 2: Proximidad sanitaria (<= 15 min = 100; >= 45 min = 0)
        self.assertEqual(p5_wlc_engine.compute_proximidad_sanitaria_score(12.2), 100.0)
        self.assertEqual(p5_wlc_engine.compute_proximidad_sanitaria_score(15.0), 100.0)
        self.assertEqual(p5_wlc_engine.compute_proximidad_sanitaria_score(30.0), 50.0)
        self.assertEqual(p5_wlc_engine.compute_proximidad_sanitaria_score(45.0), 0.0)
        self.assertEqual(p5_wlc_engine.compute_proximidad_sanitaria_score(60.0), 0.0)

        # Indicador 3: Conectividad digital (60% fibra + 40% móvil)
        self.assertEqual(p5_wlc_engine.compute_conectividad_digital_score(100.0, 98.5), 99.4)
        self.assertEqual(p5_wlc_engine.compute_conectividad_digital_score(50.0, 50.0), 50.0)
        self.assertEqual(p5_wlc_engine.compute_conectividad_digital_score(0.0, 0.0), 0.0)

        # Indicador 4: Acceso hídrico
        self.assertEqual(p5_wlc_engine.compute_acceso_hidrico_score(0.35), 96.5)
        self.assertEqual(p5_wlc_engine.compute_acceso_hidrico_score(0.0), 100.0)
        self.assertEqual(p5_wlc_engine.compute_acceso_hidrico_score(12.0), 0.0)

        # Indicador 5: Inercia demográfica y masa crítica
        self.assertEqual(p5_wlc_engine.compute_inercia_demografica_score(47, -7.84), 83.48)
        self.assertEqual(p5_wlc_engine.compute_inercia_demografica_score(150, 5.0), 97.5)
        self.assertEqual(p5_wlc_engine.compute_inercia_demografica_score(20, -7.84), 58.48)
        self.assertEqual(p5_wlc_engine.compute_inercia_demografica_score(0, -10.0), 0.0)

    def test_evaluate_wlc_madarcos_reference_case(self):
        """
        Verifica el caso real de referencia de la Sección 7.2 y 7.3 de la Propuesta (Madarcos):
        debe producir exactamente `indice_wlc == 96.05` y `semaforo == "VERDE"`.
        """
        result = p5_wlc_engine.evaluate_wlc_for_municipio(
            distancia_carretera_km=0.00,
            tiempo_urgencias_min=12.2,
            cobertura_fibra_pct=100.0,
            cobertura_movil_pct=98.5,
            distancia_recurso_hidrico_km=0.35,
            poblacion_actual=47,
            variacion_10a_pct=-7.84,
            modo_pesos="GLOBAL_5",
        )
        self.assertEqual(result["indice_wlc"], 96.05)
        self.assertEqual(result["semaforo"], "VERDE")
        self.assertEqual(result["score_acceso_carretera"], 100.0)
        self.assertEqual(result["score_proximidad_sanitaria"], 100.0)
        self.assertEqual(result["score_conectividad_digital"], 99.4)
        self.assertEqual(result["score_acceso_hidrico"], 96.5)
        self.assertEqual(result["score_inercia_demografica"], 83.48)
        self.assertAlmostEqual(sum(result["pesos_aplicados"].values()), 1.0, places=4)

        # Validar compatibilidad con `WLCBreakdownSchema` y `RutaSanitariaSchema`
        wlc_schema = WLCBreakdownSchema(**result)
        self.assertEqual(wlc_schema.indice_wlc, 96.05)

        ruta_schema = RutaSanitariaSchema(
            id_centro="CS-28027",
            nombre="Consultorio Local Buitrago del Lozoya",
            tipo="Centro de Salud / Urgencias",
            tiene_urgencias=True,
            latitud=BUITRAGO_LAT,
            longitud=BUITRAGO_LON,
            distancia_euclidea_km=7.75,
            distancia_carretera_km=11.4,
            tiempo_estimado_min=12.2,
            fuente_ruta="API CartoCiudad IGN (Tiempo Real)",
            geometria_ruta=[[MADARCOS_LAT, MADARCOS_LON], [BUITRAGO_LAT, BUITRAGO_LON]],
        )
        self.assertEqual(ruta_schema.id_centro, "CS-28027")

    def test_evaluate_wlc_modes_custom_weights_and_traffic_lights(self):
        """Verifica modo PoC (3 indicadores), pesos personalizados normalizados y semáforos AMBAR/ROJO."""
        poc_res = p5_wlc_engine.evaluate_wlc_for_municipio(
            distancia_carretera_km=0.0,
            tiempo_urgencias_min=12.2,
            cobertura_fibra_pct=0.0,
            cobertura_movil_pct=0.0,
            distancia_recurso_hidrico_km=10.0,
            poblacion_actual=47,
            variacion_10a_pct=-7.84,
            modo_pesos="POC_3",
        )
        # 100*0.40 + 100*0.30 + 83.48*0.30 = 95.044 -> 95.04
        self.assertEqual(poc_res["indice_wlc"], 95.04)
        self.assertEqual(poc_res["semaforo"], "VERDE")
        self.assertEqual(poc_res["pesos_aplicados"]["carretera"], 0.4)

        # Pesos personalizados sin sumar 1.0 se normalizan automáticamente
        custom_res = p5_wlc_engine.evaluate_wlc_for_municipio(
            distancia_carretera_km=0.0,
            tiempo_urgencias_min=45.0,
            cobertura_fibra_pct=100.0,
            cobertura_movil_pct=100.0,
            distancia_recurso_hidrico_km=0.0,
            poblacion_actual=50,
            variacion_10a_pct=0.0,
            custom_weights={"carretera": 1.0, "sanidad": 1.0},
        )
        # Normalizado a 0.5 carretera (100) + 0.5 sanidad (0) = 50.0 -> AMBAR
        self.assertEqual(custom_res["indice_wlc"], 50.0)
        self.assertEqual(custom_res["semaforo"], "AMBAR")

        # Municipio en vulnerabilidad crítica -> ROJO
        rojo_res = p5_wlc_engine.evaluate_wlc_for_municipio(
            distancia_carretera_km=12.0,
            tiempo_urgencias_min=42.0,
            cobertura_fibra_pct=0.0,
            cobertura_movil_pct=20.0,
            distancia_recurso_hidrico_km=8.0,
            poblacion_actual=18,
            variacion_10a_pct=-35.0,
        )
        self.assertLess(rojo_res["indice_wlc"], 50.0)
        self.assertEqual(rojo_res["semaforo"], "ROJO")

    def test_filter_viable_municipios_c1(self):
        """Verifica el filtro en memoria de la Consulta 1 (WLC >= 75 y cobertura de fibra óptica)."""
        municipios = [
            {
                "codigo_ine": "28069",
                "nombre": "La Hiruela",
                "cobertura_fibra_pct": 85.0,
                "wlc": {"indice_wlc": 79.2, "semaforo": "VERDE"},
            },
            {
                "codigo_ine": "28078",
                "nombre": "Madarcos",
                "infraestructura": {"cobertura_fibra_pct": 100.0},
                "wlc": {"indice_wlc": 96.05, "semaforo": "VERDE"},
            },
            {
                "codigo_ine": "28118",
                "nombre": "Puebla de la Sierra",
                "cobertura_fibra_pct": 15.0,  # Falla requisito de fibra
                "wlc": {"indice_wlc": 81.0, "semaforo": "VERDE"},
            },
            {
                "codigo_ine": "28120",
                "nombre": "Municipio Vulnerable",
                "cobertura_fibra_pct": 90.0,
                "wlc": {"indice_wlc": 61.5, "semaforo": "AMBAR"},
            },
        ]
        viables = p5_wlc_engine.filter_viable_municipios_c1(
            municipios, min_wlc=75.0, requiere_fibra=True, min_fibra_pct=50.0
        )
        self.assertEqual([m["codigo_ine"] for m in viables], ["28078", "28069"])

    def test_audit_regressions_weights_c1_and_schema_defaults(self):
        """
        Pruebas de regresión de auditoría P5.2 / Schemas:
        - Reparto proporcional de `w_infra` legado entre pilares físicos/digitales.
        - Pesos parciales (< 1.0) conservan los pesos base para los indicadores omitidos.
        - `filter_viable_municipios_c1` soporta `cobertura_fibra_pct=None` en raíz e instancias Pydantic/Schema.
        - `RutaSanitariaSchema` inicializa `geometria_ruta` a `[]` de forma independiente.
        """
        legacy_w = p5_wlc_engine._resolve_weights(
            custom_weights={"w_demo": 0.25, "w_health": 0.25, "w_grants": 0.25, "w_infra": 0.25}
        )
        self.assertGreater(legacy_w["carretera"], 0.0)
        self.assertGreater(legacy_w["hidrico"], 0.0)
        self.assertGreater(legacy_w["conectividad"], 0.0)
        self.assertAlmostEqual(sum(legacy_w.values()), 1.0, places=6)

        partial_w = p5_wlc_engine._resolve_weights(custom_weights={"w_sanidad": 0.4})
        self.assertAlmostEqual(partial_w["sanidad"], 0.4, places=6)
        self.assertGreater(partial_w["carretera"], 0.0)
        self.assertGreater(partial_w["demografia"], 0.0)
        self.assertAlmostEqual(sum(partial_w.values()), 1.0, places=6)

        wlc_schema = WLCBreakdownSchema(
            indice_wlc=96.05,
            semaforo="VERDE",
            etiqueta_viabilidad="Alta Viabilidad / Prioridad Rescate",
            score_acceso_carretera=100.0,
            score_proximidad_sanitaria=100.0,
            score_conectividad_digital=99.4,
            score_acceso_hidrico=96.5,
            score_inercia_demografica=83.48,
            pesos_aplicados=p5_wlc_engine.WEIGHTS_GLOBAL_5,
        )
        municipios_mixed = [
            {
                "codigo_ine": "28069",
                "cobertura_fibra_pct": 85.0,
                "wlc": {"indice_wlc": 79.2},
            },
            {
                "codigo_ine": "28078",
                "cobertura_fibra_pct": None,
                "infraestructura": {"cobertura_fibra_pct": 100.0},
                "wlc": wlc_schema,
            },
        ]
        viables = p5_wlc_engine.filter_viable_municipios_c1(municipios_mixed)
        self.assertEqual([m["codigo_ine"] for m in viables], ["28078", "28069"])

        r1 = RutaSanitariaSchema(
            id_centro="CS-28027",
            nombre="Consultorio Local Buitrago del Lozoya",
            tipo="Centro de Salud / Urgencias",
            latitud=BUITRAGO_LAT,
            longitud=BUITRAGO_LON,
            distancia_euclidea_km=7.75,
            distancia_carretera_km=11.4,
            tiempo_estimado_min=12.2,
            fuente_ruta="API CartoCiudad IGN (Tiempo Real)",
        )
        r2 = RutaSanitariaSchema(
            id_centro="CS-28028",
            nombre="Otro Centro",
            tipo="Consultorio Local",
            latitud=BUITRAGO_LAT,
            longitud=BUITRAGO_LON,
            distancia_euclidea_km=1.0,
            distancia_carretera_km=1.2,
            tiempo_estimado_min=2.0,
            fuente_ruta="Fallback Haversine (45 km/h)",
        )
        self.assertEqual(r1.geometria_ruta, [])
        r1.geometria_ruta.append([MADARCOS_LAT, MADARCOS_LON])
        self.assertEqual(r2.geometria_ruta, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
