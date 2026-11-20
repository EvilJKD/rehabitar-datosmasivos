# Suite de Pruebas y Verificación (`tests/`)

Contiene las pruebas unitarias, de integración, contratos de la API REST y utilidades de comprobación local del proyecto.

## Archivos principales

- **Pruebas por módulo e integración (`unittest`)**:
  - `test_p1_ngbe.py`: Pruebas del módulo P1 (fuentes IGN/SETELECO/IDEE, ETL y `p1_geo_service`).
  - `test_p2_ine.py`: Pruebas del módulo P2 (descarga INE tabla 2881, indicadores y `p2_demo_service`).
  - `test_p3_sanidad.py`: Pruebas del módulo P3 (reproyección UTM a WGS84, clasificación de urgencias y servicio PostGIS KNN).
  - `test_p4_bdns.py`: Pruebas unitarias, de API simulada, ORM/esquema e integración opcional para BDNS (P4).
  - `test_p5_wlc_and_cartociudad.py`: Pruebas del cálculo de rutas con CartoCiudad/respaldo Haversine y del motor multicriterio WLC.
  - `test_poc_integration.py`: Verificación de `db/schema.sql`, orden de `etl/run_all.py` y flujos de consultas C1-C4 en `backend/main.py`.
  - `test_frontend_api.py`: Validación de rutas expuestas al frontend y comprobación de uso exclusivo de APIs HTTP en las fuentes.
- **Scripts auxiliares y entorno de pruebas**:
  - `probar_p2_backend.py` y `run_local_test.sh`: Comprobación local de P2 contra un contenedor PostgreSQL temporal.
  - `docker-compose.p4-test.yml`: Entorno Docker desechable para ejecutar `test_p4_bdns.py` contra PostGIS.
  - `analisis_179.py` y `verificar_codigos.py`: Scripts de solo lectura para contrastar códigos INE y series de población en Madrid.
- **Datos de apoyo (`fixtures/`)**:
  - `p4_schema_stub.sql` y `fixtures/bdns/`: Esquema mínimo y respuestas JSON de ejemplo para pruebas sin acceso a red.

## Ejecución rápida

Desde el directorio `re-habitar-poc/`:

```bash
python -m unittest discover -s tests -v
```
