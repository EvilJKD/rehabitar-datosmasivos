# Re-Habitar PoC · Evaluación de Viabilidad Demográfica y Canalización de Subvenciones Rurales (Comunidad de Madrid)

Prueba de Concepto (PoC) completa en **Python + PostgreSQL/PostGIS + FastAPI + Leaflet/Chart.js** para analizar el riesgo de despoblación en la **Sierra Norte de la Comunidad de Madrid**, evaluar la accesibilidad espacial a servicios sanitarios de urgencias 24h y canalizar de forma inteligente convocatorias públicas de la **BDNS / Reto Demográfico** mediante un motor **WLC (Weighted Linear Combination)**.

---

## 🚀 Despliegue y Demostración en un Único Comando

Clona el repositorio, entra en el directorio `re-habitar-poc` y ejecuta:

```bash
docker compose up --build
```

### Flujo automático de arranque:
1. **`db` (`postgis/postgis:15-3.4-alpine`)**: Levanta PostgreSQL con la extensión `postgis`, inicializa el esquema DDL (`db/schema.sql`) con índices espaciales **GiST** (`geom geometry(Point, 4326)`) y expone un `healthcheck` (`pg_isready`).
2. **`etl_runner` (Contenedor efímero Python)**: Espera a que `db` esté sano (`service_healthy`) y ejecuta en vivo `python run_all.py`, lanzando secuencialmente los 4 pipelines (`P1 -> P2 -> P3 -> P4`) con logs detallados en consola y respaldo automático a `data/raw/` si alguna fuente gubernamental externa presenta caídas o falta de red.
3. **`app` (FastAPI + Uvicorn + Frontend)**: Espera a que `etl_runner` finalice con éxito (`service_completed_successfully`) y publica tanto la API REST como la aplicación web interactiva en:
   - **Interfaz Web Interactiva (Mapa + Dashboard)**: [http://localhost:8000](http://localhost:8000)
   - **Documentación Interactiva OpenAPI (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 👥 Arquitectura Modular para Trabajo en Paralelo (5 Desarrolladores)

El repositorio está particionado en módulos desacoplados para permitir que **5 personas** desarrollen y prueben sus componentes en paralelo sin bloquearse:

| Rol | Módulo ETL | Servicio Backend | Responsabilidad Principal |
| :--- | :--- | :--- | :--- |
| **P1** | `etl/p1_ngbe/etl_ngbe.py` | `backend/services/p1_geo_service.py` | Ingesta del Nomenclátor Geográfico Básico de España (IGN), geometrías `Point(4326)` e indicadores de conectividad/vivienda. |
| **P2** | `etl/p2_ine/etl_ine.py` | `backend/services/p2_demo_service.py` | Ingesta de series padronales (INE API Tempus Tabla 2881, 2015-2025) y **Consulta C3** (inercia demográfica, envejecimiento y reemplazo). |
| **P3** | `etl/p3_cam/etl_sanidad.py` | `backend/services/p3_health_service.py` | Geocodificación de centros sanitarios CAM y consulta espacial **KNN en PostGIS (`<->`)** al punto de Urgencias 24h más cercano. |
| **P4** | `etl/p4_bdns/etl_bdns.py` | `backend/services/p4_grants_service.py` | Ingesta de convocatorias BDNS y **Consulta C4** (matching de subvenciones por umbral poblacional `< 20.000 hab` y envejecimiento). |
| **P5** | *(Orquestación)* | `p5_cartociudad.py` + `p5_wlc_engine.py` | Cálculo vial en tiempo real vía **CartoCiudad** (con fallback Haversine a 45 km/h), motor multicriterio **WLC (0-100)** y visualización web. |

### Ejecución aislada de cada módulo ETL:
Cada desarrollador puede ejecutar su ETL de forma independiente contra la base de datos:

```bash
python etl/p1_ngbe/etl_ngbe.py
python etl/p2_ine/etl_ine.py
python etl/p3_cam/etl_sanidad.py
python etl/p4_bdns/etl_bdns.py
```

---

## 🔌 Endpoints Principales del Backend (`FastAPI`)

- `GET /api/municipios`: Devuelve el listado de municipios de la Sierra Norte con su puntuación del **Índice WLC (0-100)**, color semafórico (`VERDE`, `AMBAR`, `ROJO`), variación demográfica 2015-2025, distancia KNN a urgencias y ayudas activas. Soporta ajuste dinámico de pesos (`w_demo`, `w_health`, `w_grants`, `w_infra`).
- `GET /api/municipios/{codigo_ine}`: Ficha integral del municipio, desglose dimensional WLC, búsqueda espacial PostGIS KNN (`<->`) al centro de urgencias 24h más cercano, enrutamiento en tiempo real con **CartoCiudad** (o respaldo Haversine a 45 km/h) y ayudas BDNS canalizadas.
- `GET /api/municipios/{codigo_ine}/demografia`: Serie histórica anual **2015-2025** cruzada con la intensidad estimada de ayudas por habitante para el gráfico dual de **Chart.js**.
- `GET /api/convocatorias?codigo_ine=28070`: Catálogo de ayudas y subvenciones públicas de la BDNS con filtro opcional por municipio y categoría.
- `GET /api/centros-sanitarios`: Capa geoespacial de centros de salud y urgencias SAR/Hospital de la Comunidad de Madrid.
