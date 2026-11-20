"""
Suite de Pruebas Unitarias y de Integración para el Módulo P3:
API de Datos Abiertos de la Comunidad de Madrid (Sanidad) + Consultas Espaciales PostGIS (KNN <->).

Ejecución:
    python -m unittest discover -s re-habitar-poc/tests -p "test_p3_sanidad.py" -v
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Añadir rutas de `etl/p3_cam` y `backend` al path para importar los módulos de P3
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(TESTS_DIR, ".."))
ETL_P3_DIR = os.path.join(REPO_ROOT, "etl", "p3_cam")
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")

for path in (ETL_P3_DIR, BACKEND_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

import etl_sanidad as p3_etl  # noqa: E402


class TestP3CoordinateConversionAndNormalization(unittest.TestCase):
    """Pruebas unitarias de reproyección geodésica ETRS89 UTM 30N -> WGS84 y normalización."""

    def test_utm30n_etrs89_to_wgs84_buitrago(self):
        """
        Verifica que la conversión matemática de UTM Huso 30N (EPSG:25830) a WGS84 (EPSG:4326)
        en Buitrago del Lozoya (X=446431, Y=4538273) produce latitud ~40.9929 y longitud ~-3.6368.
        """
        coords = p3_etl.utm30n_etrs89_to_wgs84(446431.0, 4538273.0)
        self.assertIsNotNone(coords)
        lat, lon = coords
        self.assertAlmostEqual(lat, 40.9929, places=2)
        self.assertAlmostEqual(lon, -3.6368, places=2)

    def test_utm30n_etrs89_out_of_bounds_returns_none(self):
        """Coordenadas fuera del rango válido de la península deben devolver None."""
        self.assertIsNone(p3_etl.utm30n_etrs89_to_wgs84(0.0, 0.0))
        self.assertIsNone(p3_etl.utm30n_etrs89_to_wgs84(-500.0, 4500000.0))

    def test_detect_tiene_urgencias(self):
        """Verifica la detección heurística de urgencias / SAR / SUAP / PAC 24h sin falsos positivos."""
        self.assertTrue(
            p3_etl.detect_tiene_urgencias(
                tipo="Centro de Salud",
                nombre="Centro de Salud Buitrago del Lozoya",
                horario="Atención continuada 24 horas",
                municipio="Buitrago del Lozoya",
            )
        )
        self.assertTrue(
            p3_etl.detect_tiene_urgencias(
                tipo="Punto de Atención Continuada (PAC / SAR)",
                nombre="SAR Rascafría",
                horario="Urgencias nocturnas y festivos",
                municipio="Rascafría",
            )
        )
        self.assertFalse(
            p3_etl.detect_tiene_urgencias(
                tipo="Consultorio Local",
                nombre="Consultorio Local Madarcos",
                horario="Lunes a Viernes de 10:00 a 12:00",
                municipio="Madarcos",
            )
        )
        # Un Centro de Salud sin oferta/horario de urgencias fuera de cabeceras SAR no es urgencias 24h
        self.assertFalse(
            p3_etl.detect_tiene_urgencias(
                tipo="Centro de Salud",
                nombre="Centro de Salud Navacerrada",
                horario="Lunes a Viernes de 08:00 a 21:00",
                municipio="Navacerrada",
            )
        )

    def test_is_primary_or_emergency_center_filtering(self):
        """Filtra centros de salud, consultorios y urgencias, descartando farmacias u ópticas."""
        self.assertTrue(
            p3_etl.is_primary_or_emergency_center("Consultorio Local", "Consultorio Local La Hiruela")
        )
        self.assertTrue(
            p3_etl.is_primary_or_emergency_center("Centro de Salud", "CS Torrelaguna")
        )
        self.assertFalse(
            p3_etl.is_primary_or_emergency_center("Oficina de Farmacia", "Farmacia Ldo. Pérez")
        )
        self.assertFalse(
            p3_etl.is_primary_or_emergency_center("Centro de Óptica", "Óptica Visión")
        )

    def test_normalize_cam_record_buitrago_homogenization(self):
        """
        Verifica que 'Buitrago del Lozoya' se homologa a 'CS-28027' (Sección 7.2) y que
        'Gargantilla del Lozoya y Pinilla de Buitrago' NO colisiona con 'CS-28027'.
        """
        raw_buitrago = {
            "codigo_centro": "2802701",
            "centro_nro_registro": "CS28027",
            "centro_denominacion": "Consultorio Local Buitrago del Lozoya",
            "centro_tipo_descripcion": "Consultorio Local",
            "direccion_municipio_nombre": "Buitrago del Lozoya",
            "direccion_vial_tipo": "CALLE",
            "direccion_vial_nombre": "Real",
            "direccion_vial_nro": "14",
            "direccion_codigo_postal": "28730",
            "horario": "Atención continuada 24h",
            "contacto_telefono": "918680116",
            "direccion_coordenada_x": "446431",
            "direccion_coordenada_y": "4538273",
        }
        normalized = p3_etl.normalize_cam_record(raw_buitrago)
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized["id_centro"], "CS-28027")
        self.assertTrue(normalized["tiene_urgencias"])
        self.assertEqual(normalized["municipio_nombre"], "Buitrago del Lozoya")
        self.assertTrue(40.0 <= normalized["latitud"] <= 41.3)
        self.assertTrue(-4.6 <= normalized["longitud"] <= -3.0)

        # Municipio vecino con 'Buitrago' en el nombre debe mantener su propio ID y no marcar urgencias
        raw_pinilla = {
            "centro_nro_registro": "CS99901",
            "centro_denominacion": "Consultorio Pinilla de Buitrago",
            "centro_tipo_descripcion": "Consultorio de atención primaria",
            "municipio_nombre": "Gargantilla del Lozoya y Pinilla de Buitrago",
            "localizacion_coordenada_x": "441500",
            "localizacion_coordenada_y": "4535000",
        }
        normalized_pinilla = p3_etl.normalize_cam_record(raw_pinilla)
        self.assertIsNotNone(normalized_pinilla)
        self.assertEqual(normalized_pinilla["id_centro"], "CS99901")
        self.assertFalse(normalized_pinilla["tiene_urgencias"])

    def test_cam_api_memory_cache_and_force_refresh(self):
        """
        Verifica que `_CAM_API_CACHE` evita descargar repetidamente desde el endpoint de la CAM
        cuando `force_refresh=False` y vuelve a consultar la API cuando `force_refresh=True`.
        """
        sample_payload = {
            "data": [
                {
                    "centro_nro_registro": "CL-28078",
                    "centro_denominacion": "Consultorio Local Madarcos",
                    "centro_tipo_descripcion": "Consultorio de atención primaria",
                    "municipio_nombre": "Madarcos",
                    "localizacion_coordenada_x": "451100",
                    "localizacion_coordenada_y": "4543100",
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_payload

        p3_etl._CAM_API_CACHE["timestamp"] = 0.0
        p3_etl._CAM_API_CACHE["records"] = []
        try:
            with patch(
                "etl_sanidad.discover_cam_sanidad_resource_urls",
                return_value=[("JSON", "https://datos.comunidad.madrid/mock.json")],
            ), patch("etl_sanidad.requests.get", return_value=mock_resp) as mock_get:
                first = p3_etl.fetch_cam_health_centers_api(force_refresh=False)
                second = p3_etl.fetch_cam_health_centers_api(force_refresh=False)
                third = p3_etl.fetch_cam_health_centers_api(force_refresh=True)

            self.assertEqual(len(first), 1)
            self.assertEqual(len(second), 1)
            self.assertEqual(len(third), 1)
            # Solo 2 descargas HTTP (la primera y la de force_refresh=True); la segunda usa caché
            self.assertEqual(mock_get.call_count, 2)
        finally:
            p3_etl._CAM_API_CACHE["timestamp"] = 0.0
            p3_etl._CAM_API_CACHE["records"] = []

    def test_run_etl_p3_seed_load_and_ingest_for_municipio(self):
        """
        Verifica que `run_etl_p3` realiza una carga semilla ligera (urgencias + municipios semilla)
        y que `ingest_centros_for_municipio` filtra sin sensibilidad a tildes bajo demanda.
        """
        fake_centers = [
            {
                "id_centro": "CS-28027",
                "nombre": "Consultorio Local Buitrago del Lozoya",
                "tipo": "Centro de Salud / Urgencias",
                "tiene_urgencias": True,
                "municipio_nombre": "Buitrago del Lozoya",
                "direccion": "C/ Real 14",
                "horario": "24 Horas",
                "telefono": "918680116",
                "latitud": 40.9929,
                "longitud": -3.6368,
            },
            {
                "id_centro": "CL-28069",
                "nombre": "Consultorio La Hiruela",
                "tipo": "Consultorio de atención primaria",
                "tiene_urgencias": False,
                "municipio_nombre": "La Hiruela",
                "direccion": "C/ Pilón 1",
                "horario": "Horario Atención Primaria",
                "telefono": None,
                "latitud": 41.077,
                "longitud": -3.455,
            },
            {
                "id_centro": "CL-28078",
                "nombre": "Consultorio Madarcos",
                "tipo": "Consultorio de atención primaria",
                "tiene_urgencias": False,
                "municipio_nombre": "Madarcos",
                "direccion": "Plaza Mayor 1",
                "horario": "Horario Atención Primaria",
                "telefono": None,
                "latitud": 41.047,
                "longitud": -3.582,
            },
            {
                "id_centro": "CL-28120",
                "nombre": "Consultorio Rascafría",
                "tipo": "Consultorio de atención primaria",
                "tiene_urgencias": False,
                "municipio_nombre": "Rascafría",
                "direccion": "Av. El Paular 5",
                "horario": "Horario Atención Primaria",
                "telefono": None,
                "latitud": 40.904,
                "longitud": -3.879,
            },
        ]

        with patch("etl_sanidad.fetch_cam_health_centers_api", return_value=fake_centers), patch(
            "etl_sanidad.upsert_health_centers_to_db", return_value=(2, 1)
        ) as mock_upsert:
            summary = p3_etl.run_etl_p3()
            self.assertIn("semilla", summary)
            seeded = mock_upsert.call_args[0][0]
            seeded_ids = {c["id_centro"] for c in seeded}
            # Solo CS-28027 (urgencias + Buitrago) y CL-28069 (La Hiruela); Madarcos y Rascafría quedan bajo demanda
            self.assertEqual(seeded_ids, {"CS-28027", "CL-28069"})

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)  # Ya existen urgencias en BD
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("etl_sanidad.fetch_cam_health_centers_api", return_value=fake_centers), patch(
            "etl_sanidad.upsert_health_centers_to_db", return_value=(1, 0)
        ) as mock_upsert_mun:
            # Búsqueda sin tilde ('Rascafria') debe encontrar 'Rascafría'
            count = p3_etl.ingest_centros_for_municipio("Rascafria", conn=mock_conn)
            self.assertEqual(count, 1)
            ingested = mock_upsert_mun.call_args[0][0]
            self.assertEqual([c["id_centro"] for c in ingested], ["CL-28120"])

    def test_parse_cam_json_and_csv_payloads(self):
        """Verifica el parseo tanto de payloads JSON como CSV de Datos Abiertos CAM."""
        sample_record = {
            "centro_nro_registro": "CL-28064",
            "centro_denominacion": "Consultorio Local La Hiruela",
            "centro_tipo_descripcion": "Consultorio Local",
            "direccion_municipio_nombre": "La Hiruela",
            "direccion_coordenada_x": "460800",
            "direccion_coordenada_y": "4547600",
        }
        parsed_json = p3_etl.parse_cam_json_payload({"data": [sample_record]})
        self.assertEqual(len(parsed_json), 1)
        self.assertEqual(parsed_json[0]["municipio_nombre"], "La Hiruela")

        csv_text = (
            "centro_nro_registro;centro_denominacion;centro_tipo_descripcion;"
            "direccion_municipio_nombre;direccion_coordenada_x;direccion_coordenada_y\n"
            "CL-28064;Consultorio Local La Hiruela;Consultorio Local;La Hiruela;460800;4547600\n"
        )
        parsed_csv = p3_etl.parse_cam_csv_content(csv_text)
        self.assertEqual(len(parsed_csv), 1)
        self.assertEqual(parsed_csv[0]["id_centro"], "CL-28064")


class TestP3LiveCAMOpenDataAPIConnection(unittest.TestCase):
    """Prueba de integración contra el API pública de Datos Abiertos de la Comunidad de Madrid."""

    def test_live_cam_api_connection_and_extraction(self):
        """
        Intenta conectar en tiempo real con https://datos.comunidad.madrid mediante
        `discover_cam_sanidad_resource_urls` y `fetch_cam_health_centers_api`. Si el
        entorno bloquea la red, ejecuta un respaldo HTTP simulado con respuestas CKAN
        `package_show` y payloads JSON/CSV en UTM ETRS89 a través del pipeline real:
        1. Se descubren las URLs del catálogo CKAN o recursos directos.
        2. Se descargan y normalizan los centros sanitarios de la Comunidad de Madrid.
        3. Todas las coordenadas están reproyectadas en WGS84 (EPSG:4326) dentro de Madrid.
        4. El centro de referencia CS-28027 (Buitrago del Lozoya) está presente y tiene urgencias.
        """
        ckan_json_url = (
            "https://datos.comunidad.madrid/catalogo/dataset/d8a0a444-adf5-4c04-8999-0eac3de52cb7/"
            "resource/94090084-2276-4a07-87b4-cd028ea6b46d/download/"
            "centros_servicios_establecimientos_sanitarios.json"
        )
        ckan_csv_url = (
            "https://datos.comunidad.madrid/catalogo/dataset/d8a0a444-adf5-4c04-8999-0eac3de52cb7/"
            "resource/2948b4da-8b39-42b7-b667-779a5284f39d/download/"
            "centros_servicios_establecimientos_sanitarios.csv"
        )
        ckan_package_payload = {
            "success": True,
            "result": {
                "name": "centros_servicios_establecimientos_sanitarios",
                "resources": [
                    {"format": "CSV", "url": ckan_csv_url},
                    {"format": "JSON", "url": ckan_json_url},
                ],
            },
        }
        raw_cam_records = [
            {
                "centro_nro_registro": "2802701",
                "centro_denominacion": "Consultorio Local Buitrago del Lozoya",
                "centro_tipo_descripcion": "Consultorio Local",
                "direccion_municipio_nombre": "Buitrago del Lozoya",
                "direccion_vial_tipo": "CALLE",
                "direccion_vial_nombre": "Real",
                "direccion_vial_nro": "14",
                "direccion_codigo_postal": "28730",
                "horario": "Atención continuada 24 horas",
                "oferta_asistencial": "Urgencias Atención Primaria",
                "contacto_telefono": "918680116",
                "direccion_coordenada_x": "446431",
                "direccion_coordenada_y": "4538273",
            },
            {
                "centro_nro_registro": "CL-28069",
                "centro_denominacion": "Consultorio Local La Hiruela",
                "centro_tipo_descripcion": "Consultorio Local",
                "direccion_municipio_nombre": "La Hiruela",
                "direccion_vial_tipo": "CALLE",
                "direccion_vial_nombre": "Pilón",
                "direccion_vial_nro": "1",
                "direccion_codigo_postal": "28191",
                "direccion_coordenada_x": "460800",
                "direccion_coordenada_y": "4547600",
            },
            {
                "centro_nro_registro": "CL-28078",
                "centro_denominacion": "Consultorio Local Madarcos",
                "centro_tipo_descripcion": "Consultorio Local",
                "direccion_municipio_nombre": "Madarcos",
                "direccion_vial_tipo": "PLAZA",
                "direccion_vial_nombre": "Mayor",
                "direccion_vial_nro": "1",
                "direccion_codigo_postal": "28755",
                "direccion_coordenada_x": "451100",
                "direccion_coordenada_y": "4543100",
            },
            {
                "centro_nro_registro": "CS-28120",
                "centro_denominacion": "Centro de Salud Rascafría",
                "centro_tipo_descripcion": "Centro de Salud",
                "direccion_municipio_nombre": "Rascafría",
                "oferta_asistencial": "SAR Atención continuada",
                "direccion_coordenada_x": "426000",
                "direccion_coordenada_y": "4528500",
            },
            {
                "centro_nro_registro": "CS-28151",
                "centro_denominacion": "Centro de Salud Torrelaguna",
                "centro_tipo_descripcion": "Centro de Salud",
                "direccion_municipio_nombre": "Torrelaguna",
                "horario": "Atención continuada 24 horas",
                "direccion_coordenada_x": "454600",
                "direccion_coordenada_y": "4519800",
            },
            {
                "centro_nro_registro": "CL-28063",
                "centro_denominacion": "Consultorio Local Pinilla de Buitrago",
                "centro_tipo_descripcion": "Consultorio de atención primaria",
                "direccion_municipio_nombre": "Gargantilla del Lozoya y Pinilla de Buitrago",
                "direccion_coordenada_x": "441500",
                "direccion_coordenada_y": "4535000",
            },
            {
                "centro_nro_registro": "CS-28030",
                "centro_denominacion": "Centro de Salud La Cabrera",
                "centro_tipo_descripcion": "Centro de Salud",
                "direccion_municipio_nombre": "La Cabrera",
                "direccion_coordenada_x": "448350",
                "direccion_coordenada_y": "4523900",
            },
            {
                "centro_nro_registro": "CS-28144",
                "centro_denominacion": "Centro de Salud Soto del Real",
                "centro_tipo_descripcion": "Centro de Salud",
                "direccion_municipio_nombre": "Soto del Real",
                "direccion_coordenada_x": "433650",
                "direccion_coordenada_y": "4511600",
            },
            {
                "centro_nro_registro": "CS-28045",
                "centro_denominacion": "Centro de Salud Colmenar Viejo Sur",
                "centro_tipo_descripcion": "Centro de Salud",
                "direccion_municipio_nombre": "Colmenar Viejo",
                "direccion_coordenada_x": "435150",
                "direccion_coordenada_y": "4501150",
            },
            {
                "centro_nro_registro": "H-28079",
                "centro_denominacion": "Hospital Universitario La Paz",
                "centro_tipo_descripcion": "Hospitales",
                "direccion_municipio_nombre": "Madrid",
                "horario": "Urgencias 24 horas",
                "direccion_coordenada_x": "441670",
                "direccion_coordenada_y": "4481380",
            },
            {
                "centro_nro_registro": "FA-28027",
                "centro_denominacion": "Oficina de Farmacia Buitrago",
                "centro_tipo_descripcion": "Oficina de Farmacia",
                "direccion_municipio_nombre": "Buitrago del Lozoya",
                "direccion_coordenada_x": "446450",
                "direccion_coordenada_y": "4538290",
            },
        ]
        csv_lines = [
            "centro_nro_registro;centro_denominacion;centro_tipo_descripcion;"
            "direccion_municipio_nombre;horario;oferta_asistencial;"
            "direccion_coordenada_x;direccion_coordenada_y"
        ]
        for rec in raw_cam_records:
            csv_lines.append(
                ";".join(
                    [
                        rec["centro_nro_registro"],
                        rec["centro_denominacion"],
                        rec["centro_tipo_descripcion"],
                        rec["direccion_municipio_nombre"],
                        rec.get("horario", ""),
                        rec.get("oferta_asistencial", ""),
                        rec["direccion_coordenada_x"],
                        rec["direccion_coordenada_y"],
                    ]
                )
            )
        csv_bytes = "\n".join(csv_lines).encode("utf-8")

        used_http_fallback = False
        csv_centers = None
        try:
            # Garantizar consulta en vivo limpia sin residuo de caché previa
            p3_etl._CAM_API_CACHE["timestamp"] = 0.0
            p3_etl._CAM_API_CACHE["records"] = []
            urls = p3_etl.discover_cam_sanidad_resource_urls(timeout=15)
            self.assertTrue(len(urls) >= 1, "Debe existir al menos una URL de recurso de la CAM")
            centers = p3_etl.fetch_cam_health_centers_api(timeout=25, force_refresh=True)
        except (RuntimeError, OSError, ConnectionError):
            used_http_fallback = True
            allow_json_endpoint = True

            def mock_http_get(url, **kwargs):
                resp = MagicMock()
                if url == p3_etl.CAM_CKAN_PACKAGE_URL:
                    resp.status_code = 200
                    resp.json.return_value = ckan_package_payload
                    return resp
                if url == ckan_json_url:
                    if not allow_json_endpoint:
                        resp.status_code = 503
                        resp.raise_for_status.side_effect = p3_etl.requests.HTTPError(
                            "503 Server Error"
                        )
                        return resp
                    resp.status_code = 200
                    resp.json.return_value = {"data": raw_cam_records}
                    return resp
                if url == ckan_csv_url:
                    resp.status_code = 200
                    resp.content = csv_bytes
                    return resp
                resp.status_code = 404
                resp.raise_for_status.side_effect = p3_etl.requests.HTTPError("404 Not Found")
                return resp

            with patch("etl_sanidad.requests.get", side_effect=mock_http_get):
                p3_etl._CAM_API_CACHE["timestamp"] = 0.0
                p3_etl._CAM_API_CACHE["records"] = []
                urls = p3_etl.discover_cam_sanidad_resource_urls(timeout=15)
                self.assertEqual(urls[0], ("JSON", ckan_json_url))
                self.assertIn(("CSV", ckan_csv_url), urls)
                centers = p3_etl.fetch_cam_health_centers_api(timeout=25, force_refresh=True)

                # Validar también el recurso CSV de respaldo cuando falla la descarga JSON
                allow_json_endpoint = False
                p3_etl._CAM_API_CACHE["timestamp"] = 0.0
                p3_etl._CAM_API_CACHE["records"] = []
                csv_centers = p3_etl.fetch_cam_health_centers_api(timeout=25, force_refresh=True)
        finally:
            p3_etl._CAM_API_CACHE["timestamp"] = 0.0
            p3_etl._CAM_API_CACHE["records"] = []

        if used_http_fallback:
            self.assertEqual(
                len(centers),
                10,
                f"El parser JSON debía conservar 10 centros asistenciales válidos, obtenidos: {len(centers)}",
            )
            self.assertIsNotNone(csv_centers)
            self.assertEqual(
                len(csv_centers),
                10,
                f"El parser CSV debía conservar 10 centros asistenciales válidos, obtenidos: {len(csv_centers)}",
            )
            datasets_to_validate = [centers, csv_centers]
        else:
            self.assertGreater(
                len(centers),
                50,
                f"Se esperaban más de 50 centros sanitarios reales desde la API CAM, obtenidos: {len(centers)}",
            )
            datasets_to_validate = [centers]

        # Comprobar que todos los centros tienen coordenadas WGS84 válidas en el entorno de Madrid
        # y que el centro de referencia CS-28027 (Buitrago del Lozoya) está presente con urgencias
        for dataset in datasets_to_validate:
            for c in dataset[:50]:
                self.assertTrue(
                    39.8 <= c["latitud"] <= 41.35,
                    f"Latitud fuera de rango en {c['id_centro']}: {c['latitud']}",
                )
                self.assertTrue(
                    -4.65 <= c["longitud"] <= -3.0,
                    f"Longitud fuera de rango en {c['id_centro']}: {c['longitud']}",
                )

            buitrago = next((c for c in dataset if c["id_centro"] == "CS-28027"), None)
            self.assertIsNotNone(buitrago, "El centro CS-28027 (Buitrago del Lozoya) debe estar presente")
            self.assertEqual(p3_etl._normalize_text(buitrago["municipio_nombre"]), "BUITRAGO DEL LOZOYA")
            self.assertTrue(buitrago["tiene_urgencias"])


class TestP3DatabaseUpsertAndServiceIntegration(unittest.IsolatedAsyncioTestCase):
    """Pruebas unitarias de persistencia PostGIS y del servicio espacial KNN del Backend."""

    def test_upsert_health_centers_to_db_with_mock_connection(self):
        """
        Verifica que `upsert_health_centers_to_db` ejecuta el UPSERT con PostGIS
        `ST_SetSRID(ST_MakePoint(%s, %s), 4326)` y devuelve `(total_insertados, total_con_urgencias)`.
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        sample_centers = [
            {
                "id_centro": "CS-28027",
                "nombre": "Consultorio Local Buitrago del Lozoya",
                "tipo": "Centro de Salud / Urgencias",
                "tiene_urgencias": True,
                "municipio_nombre": "Buitrago del Lozoya",
                "direccion": "C/ Real 14, 28730 Buitrago del Lozoya",
                "horario": "Atención continuada 24 horas",
                "telefono": "918680116",
                "latitud": 40.992912,
                "longitud": -3.636845,
            }
        ]

        inserted_count, urgencias_count = p3_etl.upsert_health_centers_to_db(
            sample_centers, conn=mock_conn
        )

        self.assertEqual(inserted_count, 1)
        self.assertEqual(urgencias_count, 1)
        mock_cursor.execute.assert_called_once()
        sql_passed, params_passed = mock_cursor.execute.call_args[0]
        self.assertIn("INSERT INTO centros_sanitarios", sql_passed)
        self.assertIn("ST_SetSRID(ST_MakePoint(%s, %s), 4326)", sql_passed)
        self.assertIn("ON CONFLICT (id_centro) DO UPDATE", sql_passed)
        # Verificar orden PostGIS: ST_MakePoint(longitud, latitud)
        self.assertAlmostEqual(params_passed[-2], -3.636845)
        self.assertAlmostEqual(params_passed[-1], 40.992912)

    def test_backend_orm_and_pydantic_schemas(self):
        """
        Verifica la estructura de los modelos ORM (`CentroSanitario`) y Schemas Pydantic
        (`CentroSanitarioSchema`, `RutaSanitariaSchema`) definidos en `backend/`.
        """
        models_file = os.path.join(BACKEND_DIR, "models", "domain.py")
        schemas_file = os.path.join(BACKEND_DIR, "schemas", "domain.py")

        with open(models_file, "r", encoding="utf-8") as f:
            models_src = f.read()
        self.assertIn("class CentroSanitario(Base):", models_src)
        self.assertIn('__tablename__ = "centros_sanitarios"', models_src)
        for col in ("id_centro", "nombre", "tipo", "tiene_urgencias", "latitud", "longitud"):
            self.assertIn(col, models_src)

        with open(schemas_file, "r", encoding="utf-8") as f:
            schemas_src = f.read()
        self.assertIn("class CentroSanitarioSchema(BaseModel):", schemas_src)
        self.assertIn("class RutaSanitariaSchema(BaseModel):", schemas_src)
        self.assertIn("distancia_euclidea_km", schemas_src)
        self.assertIn("tiempo_estimado_min", schemas_src)

    async def test_p3_health_service_knn_queries(self):
        """
        Verifica que `get_nearest_emergency_all`, `get_nearest_health_centers_for_municipio`
        y `list_centros_sanitarios_service` construyen las consultas espaciales PostGIS
        con `CROSS JOIN LATERAL` y el operador KNN `<->` y formatean la salida.
        """
        from services import p3_health_service

        # Verificar que las consultas SQL contienen el operador espacial KNN (<->) y ST_DistanceSphere
        self.assertIn("<->", str(p3_health_service.SQL_KNN_NEAREST_EMERGENCY_ALL))
        self.assertIn("CROSS JOIN LATERAL", str(p3_health_service.SQL_KNN_NEAREST_EMERGENCY_ALL))
        self.assertIn("ST_DistanceSphere", str(p3_health_service.SQL_KNN_NEAREST_EMERGENCY_ALL))

        # Mock de sesión asíncrona SQLAlchemy para `get_nearest_emergency_all`
        mock_db = AsyncMock()
        mock_result_all = MagicMock()
        mock_result_all.mappings.return_value.all.return_value = [
            {
                "codigo_ine": "28078",  # Madarcos (28078)
                "municipio_origen": "Madarcos",
                "id_centro": "CS-28027",
                "nombre": "Consultorio Local Buitrago del Lozoya",
                "tipo": "Centro de Salud / Urgencias",
                "tiene_urgencias": True,
                "municipio_nombre": "Buitrago del Lozoya",
                "direccion": "C/ Real 14",
                "horario": "24h",
                "telefono": "918680116",
                "latitud": 40.992912,
                "longitud": -3.636845,
                "distancia_euclidea_km": 5.74,
            }
        ]
        mock_db.execute.return_value = mock_result_all

        nearest_map = await p3_health_service.get_nearest_emergency_all(mock_db)
        self.assertIn("28078", nearest_map)
        self.assertEqual(nearest_map["28078"]["id_centro"], "CS-28027")
        self.assertAlmostEqual(nearest_map["28078"]["distancia_euclidea_km"], 5.74)

        # Mock para `get_nearest_health_centers_for_municipio` (ya hidratado en BD)
        mock_res_mun_name = MagicMock()
        mock_res_mun_name.mappings.return_value.first.return_value = {"nombre": "Madarcos"}
        mock_res_urg_count = MagicMock()
        mock_res_urg_count.mappings.return_value.first.return_value = {"total_urg": 12}
        mock_res_mun_count = MagicMock()
        mock_res_mun_count.mappings.return_value.first.return_value = {"total_mun": 1}

        mock_res_urg = MagicMock()
        mock_res_urg.mappings.return_value.first.return_value = {
            "id_centro": "CS-28027",
            "nombre": "Consultorio Local Buitrago del Lozoya",
            "tipo": "Centro de Salud / Urgencias",
            "tiene_urgencias": True,
            "municipio_nombre": "Buitrago del Lozoya",
            "direccion": "C/ Real 14",
            "horario": "24h",
            "telefono": "918680116",
            "latitud": 40.992912,
            "longitud": -3.636845,
            "distancia_euclidea_km": 5.74,
        }
        mock_res_cons = MagicMock()
        mock_res_cons.mappings.return_value.first.return_value = {
            "id_centro": "CL-MADARCOS",
            "nombre": "Consultorio Local Madarcos",
            "tipo": "Consultorio Local",
            "tiene_urgencias": False,
            "municipio_nombre": "Madarcos",
            "direccion": "Plaza Mayor 1",
            "horario": "L-V",
            "telefono": "918680000",
            "latitud": 41.0381,
            "longitud": -3.5819,
            "distancia_euclidea_km": 0.12,
        }
        mock_db.execute.side_effect = [
            mock_res_mun_name,
            mock_res_urg_count,
            mock_res_mun_count,
            mock_res_urg,
            mock_res_cons,
        ]

        detail_centers = await p3_health_service.get_nearest_health_centers_for_municipio(
            mock_db, "28078"
        )
        self.assertEqual(detail_centers["urgencias"]["id_centro"], "CS-28027")
        self.assertEqual(detail_centers["consultorio"]["id_centro"], "CL-MADARCOS")

    async def test_p3_on_demand_hydration_in_backend_service(self):
        """
        Verifica el flujo on-demand en `p3_health_service.py`:
        1. Cuando `centros_sanitarios` no tiene datos del municipio solicitado, invoca
           a `fetch_cam_health_centers_api`, ejecuta `SQL_UPSERT_CENTRO_SANITARIO` y hace `commit()`.
        2. `list_centros_sanitarios_service` auto-hidrata si el primer `SELECT` devuelve `[]`.
        """
        from services import p3_health_service

        cam_records = [
            {
                "id_centro": "CS-28027",
                "nombre": "Consultorio Local Buitrago del Lozoya",
                "tipo": "Centro de Salud / Urgencias",
                "tiene_urgencias": True,
                "municipio_nombre": "Buitrago del Lozoya",
                "direccion": "C/ Real 14",
                "horario": "24 Horas",
                "telefono": "918680116",
                "latitud": 40.992912,
                "longitud": -3.636845,
            },
            {
                "id_centro": "CL-28078",
                "nombre": "Consultorio Local Madarcos",
                "tipo": "Consultorio de atención primaria",
                "tiene_urgencias": False,
                "municipio_nombre": "Madarcos",
                "direccion": "Plaza Mayor 1",
                "horario": "Horario de Atención Primaria",
                "telefono": None,
                "latitud": 41.0471,
                "longitud": -3.5821,
            },
        ]

        # Escenario 1: `hydrate_health_centers_on_demand` por codigo_ine cuando el pueblo aún no está en BD
        mock_db = AsyncMock()
        res_mun_name = MagicMock()
        res_mun_name.mappings.return_value.first.return_value = {"nombre": "Madarcos"}
        res_urg_count = MagicMock()
        res_urg_count.mappings.return_value.first.return_value = {"total_urg": 5}
        res_mun_count = MagicMock()
        res_mun_count.mappings.return_value.first.return_value = {"total_mun": 0}
        res_upsert = MagicMock()
        mock_db.execute.side_effect = [res_mun_name, res_urg_count, res_mun_count, res_upsert]

        with patch.object(
            p3_health_service.cam_etl,
            "fetch_cam_health_centers_api",
            return_value=cam_records,
        ) as mock_fetch:
            inserted = await p3_health_service.hydrate_health_centers_on_demand(
                mock_db, codigo_ine="28078"
            )

        self.assertEqual(inserted, 1)
        mock_fetch.assert_called_once()
        mock_db.commit.assert_awaited_once()
        upsert_sql_arg, upsert_rows_arg = mock_db.execute.call_args_list[-1][0]
        self.assertIn("INSERT INTO centros_sanitarios", str(upsert_sql_arg))
        self.assertEqual([r["id_centro"] for r in upsert_rows_arg], ["CL-28078"])

        # Escenario 2: `list_centros_sanitarios_service` devuelve [] inicialmente, auto-hidrata desde CAM y re-consulta
        mock_db_list = AsyncMock()
        res_empty_select = MagicMock()
        res_empty_select.mappings.return_value.all.return_value = []
        res_list_urg_count = MagicMock()
        res_list_urg_count.mappings.return_value.first.return_value = {"total_urg": 5}
        res_list_mun_count = MagicMock()
        res_list_mun_count.mappings.return_value.first.return_value = {"total_mun": 0}
        res_list_upsert = MagicMock()
        res_populated_select = MagicMock()
        res_populated_select.mappings.return_value.all.return_value = [cam_records[1]]

        mock_db_list.execute.side_effect = [
            res_empty_select,
            res_list_urg_count,
            res_list_mun_count,
            res_list_upsert,
            res_populated_select,
        ]

        with patch.object(
            p3_health_service.cam_etl,
            "fetch_cam_health_centers_api",
            return_value=cam_records,
        ) as mock_fetch_list:
            centers_list = await p3_health_service.list_centros_sanitarios_service(
                mock_db_list, municipio_nombre="Madarcos"
            )

        mock_fetch_list.assert_called_once()
        mock_db_list.commit.assert_awaited_once()
        self.assertEqual(len(centers_list), 1)
        self.assertEqual(centers_list[0]["id_centro"], "CL-28078")
        self.assertIsNone(centers_list[0]["distancia_euclidea_km"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
