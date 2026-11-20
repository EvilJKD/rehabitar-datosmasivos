# Módulo P3: Centros Sanitarios (Comunidad de Madrid)

Este módulo descarga el catálogo oficial de centros, servicios y establecimientos sanitarios de la Comunidad de Madrid, normaliza sus datos geográficos y los deja listos en PostGIS para consultar la accesibilidad sanitaria de cada municipio.

## Qué hace

1. **Descarga desde la API CKAN de Datos Abiertos de la CAM**: `etl/p3_cam/etl_sanidad.py` consulta `package_show?id=centros_servicios_establecimientos_sanitarios` para obtener las URL vigentes en JSON y CSV (con URL directas de respaldo), filtra centros asistenciales relevantes (`RELEVANT_CENTER_TYPES`) y consolida duplicados por `id_centro`.
2. **Conversión de coordenadas UTM ETRS89 a WGS84**: `utm30n_etrs89_to_wgs84()` transforma las coordenadas proyectadas UTM Huso 30N ETRS89 (`EPSG:25830`) a latitud y longitud WGS84 (`EPSG:4326`) y valida que estén dentro del entorno de la Comunidad de Madrid.
3. **Clasificación de urgencias**: `detect_tiene_urgencias()` determina el valor de `tiene_urgencias` según los datos del catálogo, el tipo de centro (hospitales, urgencias, atención continuada, SAR, SUAP o PAC), el horario 24 horas y los municipios cabecera SAR de referencia (como `Buitrago del Lozoya`, homologado con `CS-28027`).
4. **Carga en `centros_sanitarios`**: `upsert_health_centers_to_db()` inserta o actualiza los centros en PostgreSQL con `ON CONFLICT (id_centro) DO UPDATE` y genera su geometría `ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)`. La ejecución inicial (`run_etl_p3()`) carga la red de urgencias y los municipios semilla (`La Hiruela` y `Buitrago del Lozoya`); el resto de municipios se hidrata bajo demanda con `ingest_centros_for_municipio()`.
5. **Consulta espacial KNN `<->` en PostGIS**: `backend/services/p3_health_service.py` usa `CROSS JOIN LATERAL` con `ORDER BY m.geom <-> c.geom LIMIT 1` y `ST_DistanceSphere(m.geom, cs.geom) / 1000.0` para calcular la distancia en kilómetros al centro de urgencias y al consultorio más cercanos a cada municipio (`get_nearest_emergency_all()` y `get_nearest_health_centers_for_municipio()`), además de hidratar bajo demanda (`hydrate_health_centers_on_demand()`) cuando faltan datos en la base de datos.

## Cómo ejecutarlo

Desde la raíz de `re-habitar-poc`, con PostgreSQL/PostGIS disponible y el esquema creado:

```bash
python etl/p3_cam/etl_sanidad.py
```

### Variables de entorno

El script utiliza valores por defecto locales que pueden sobrescribirse mediante variables de entorno:

- `POSTGRES_HOST` (por defecto `localhost`)
- `POSTGRES_PORT` (por defecto `5432`)
- `POSTGRES_USER` (por defecto `rehabitar`)
- `POSTGRES_PASSWORD` (por defecto `rehabitar_pwd`)
- `POSTGRES_DB` (por defecto `rehabitar_db`)
- `CAM_SANIDAD_JSON_URL` y `CAM_SANIDAD_CSV_URL` (URL directas de respaldo si falla el descubrimiento CKAN)
- `CAM_CACHE_TTL_SECONDS` (tiempo de caché en memoria en segundos, por defecto `600`)
- `EXTERNAL_API_TIMEOUT` (tiempo máximo de espera HTTP en segundos, por defecto `10`)
