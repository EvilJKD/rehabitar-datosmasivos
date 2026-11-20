# Servicios del Backend (`backend/services/`)

Esta carpeta agrupa los módulos de lógica de negocio del backend organizados por dominio (P1 a P5). Cada módulo consulta PostgreSQL/PostGIS, lanza cargas bajo demanda hacia los ETL cuando faltan datos o ejecuta cálculos en memoria para las consultas de la aplicación.

## Módulos P1 a P5

### 1. P1: Territorio e infraestructura (`p1_geo_service.py`)
Consulta el catálogo de municipios junto con sus métricas de infraestructura materializadas (`metricas_infraestructura`: distancia a carretera, distancia a recurso hídrico, cobertura de fibra óptica y cobertura móvil).
- `get_all_municipios_base(db)`: lista todos los municipios con sus métricas disponibles.
- `get_municipio_by_ine(db, codigo_ine)`: obtiene los datos base e infraestructura de un municipio concreto.
- `hydrate_infraestructura_on_demand(db, codigo_ine)`: si el municipio no tiene métricas guardadas, ejecuta `ingest_infraestructura_municipio` en un hilo secundario.

### 2. P2: Demografía e inercia poblacional (`p2_demo_service.py`)
Resuelve la Consulta 3 analizando la evolución poblacional de los últimos 5 y 10 años a partir de `demografia_anual`.
- `hydrate_demografia_on_demand(db, codigo_ine)`: descarga y guarda la serie del INE mediante `ingest_ine_for_municipio` si el municipio aún no tiene registros.
- `get_demografia_summary_all(db)`: resume las variaciones y la clasificación de inercia de los municipios ya cargados.
- `get_demografia_serie_by_municipio(db, codigo_ine, ...)`: hidrata si hace falta y devuelve la serie anual junto con los indicadores calculados.
- `calcular_indicadores` y `classify_demographic_inertia`: calculan variaciones, comprueban el umbral de masa crítica y asignan la etiqueta de inercia (`COLAPSO`, `DECLIVE`, `ESTANCAMIENTO`, `RECUPERACION`, `REPUNTE_RECIENTE` o `SIN_DATOS`).

### 3. P3: Accesibilidad sanitaria PostGIS (`p3_health_service.py`)
Resuelve la parte espacial de la Consulta 2 buscando los centros asistenciales más cercanos sobre `centros_sanitarios` con el operador KNN `<->` de PostGIS y distancia geodésica `ST_DistanceSphere`.
- `hydrate_health_centers_on_demand(db, ...)`: importa y actualiza centros desde la API de la Comunidad de Madrid cuando faltan registros en la base de datos.
- `get_nearest_emergency_all(db)`: devuelve el centro con urgencias más cercano para cada municipio.
- `get_nearest_health_centers_for_municipio(db, codigo_ine)`: devuelve el centro de urgencias y el consultorio más cercanos al municipio indicado.
- `list_centros_sanitarios_service(db, ...)`: lista centros filtrando por urgencias o municipio para su visualización en mapa.

### 4. P4: Subvenciones y ayudas BDNS (`p4_grants_service.py`)
Resuelve la Consulta 4 sobre convocatorias públicas asignadas a cada municipio en `convocatorias` y `convocatoria_municipio`.
- `hydrate_grants_on_demand(db, codigo_ine)`: cruza y persiste las ayudas aplicables al municipio mediante `ingest_bdns_for_municipio`.
- `get_grants_summary_all(db)` y `get_num_ayudas_abiertas(db, codigo_ine)`: devuelven conteos y presupuesto agregado de ayudas abiertas por municipio.
- `get_convocatorias(db, codigo_ine, categoria, solo_abiertas)`: lista convocatorias filtradas por municipio, finalidad y vigencia de plazo.

### 5. P5.1: Rutas en tiempo real con CartoCiudad (`p5_cartociudad.py`)
Calcula en tiempo real la ruta por carretera entre un municipio y su centro sanitario más cercano usando la API de CartoCiudad (IGN), sin guardar rutas ni tiempos de viaje en PostgreSQL.
- `calculate_route_cartociudad(lat_orig, lon_orig, lat_dest, lon_dest, force_refresh)`: consulta la caché efímera en memoria (`_CARTOCIUDAD_MEM_CACHE`) y, si no hay dato vigente, llama a CartoCiudad de forma asíncrona.
- `compute_fallback_route(...)`, `haversine_km(...)` y `build_curved_mountain_polyline(...)`: calculan una ruta de respaldo en memoria (factor de sinuosidad 1.32 y 45 km/h) si la API externa falla o devuelve datos inválidos.

### 6. P5.2: Motor WLC en memoria (`p5_wlc_engine.py`)
Normaliza los cinco indicadores de habitabilidad a una escala de 0 a 100 y calcula el índice agregado en memoria para la Consulta 1, sin persistir puntuaciones en base de datos.
- `compute_acceso_carretera_score`, `compute_proximidad_sanitaria_score`, `compute_conectividad_digital_score`, `compute_acceso_hidrico_score` y `compute_inercia_demografica_score`: calculan cada subíndice individual.
- `evaluate_wlc_for_municipio(...)`: combina los cinco subíndices con los pesos `GLOBAL_5`, `POC_3` o pesos personalizados y asigna el semáforo (`VERDE`, `AMBAR` o `ROJO`).
- `filter_viable_municipios_c1(...)`: filtra los municipios que alcanzan el umbral mínimo de WLC y de cobertura de fibra óptica, ordenados de mayor a menor puntuación.
