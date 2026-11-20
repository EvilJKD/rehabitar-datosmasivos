# Suite de Pruebas (`tests/`)

Contiene las 7 suites de pruebas activas (`unittest`) del proyecto Re-Habitar PoC.

## Suites activas

- `test_p1_ngbe.py`: Pruebas unitarias del módulo P1 (fuentes IGN, SETELECO e IDEE, proceso ETL `etl_ngbe`, servicio `p1_geo_service` y esquema `InfraestructuraSchema`).
- `test_p2_ine.py`: Pruebas unitarias del módulo P2 (ingesta de la tabla 2881 del INE, cálculo de indicadores demográficos, servicio `p2_demo_service` y esquema `DemografiaSerieResponseSchema`).
- `test_p3_sanidad.py`: Pruebas del módulo P3 (reproyección UTM a WGS84, clasificación de urgencias, servicio `p3_health_service` y consultas espaciales KNN).
- `test_p4_bdns.py`: Pruebas del módulo P4 (ETL `etl_bdns`, servicio `p4_grants_service`, modelos, esquemas y endpoint `GET /api/convocatorias`).
- `test_p5_wlc_and_cartociudad.py`: Pruebas del módulo P5 (cálculo de rutas con CartoCiudad y respaldo Haversine en `p5_cartociudad`, motor multicriterio WLC en `p5_wlc_engine` y esquemas `WLCBreakdownSchema` y `RutaSanitariaSchema`).
- `test_poc_integration.py`: Pruebas de integración entre módulos (estructura DDL de `db/schema.sql`, orden de ejecución en `etl/run_all.py` y flujos de las consultas C1 a C4 en `backend/main.py`).
- `test_frontend_api.py`: Pruebas de los contratos del API REST expuesto al frontend en `backend/main.py` y comprobación de uso exclusivo de APIs HTTP en las fuentes P1 a P5.

## Ejecución

Desde el directorio `re-habitar-poc/`:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
