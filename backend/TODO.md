# 📋 TODO List — Aplicación Principal Backend (`backend/`) · Las 4 Consultas y Mediador en Memoria

> **Papel del Mediador en `backend/main.py` (Sección 5, 6.5, 7.3 y Diagrama Sección 9):**
> 1. **Hidratación Materializada Bajo Demanda:** Si el usuario selecciona un municipio con `hidratado = FALSE`, ingesta y guarda en PostgreSQL sus datos estáticos/consolidados (`demografia_anual`, `metricas_infraestructura`, `convocatoria_municipio`).
> 2. **Integración Virtual en Memoria (Sección 7.3):** Identifica el centro de urgencias más cercano con KNN en PostGIS (`<->`), pide la ruta en vivo a **CartoCiudad** (sin persistir tiempos en BD) y **fusiona en memoria** los valores en el **Motor WLC**.

## Paso a Paso para Completar `backend/main.py`

- [ ] **Paso 1: Implementar `ensure_municipio_hydrated(db, codigo_ine, force_refresh=False)`**
  - Si `municipios.hidratado == FALSE` (o `force_refresh == TRUE`), ejecutar la ingesta materializada para ese `codigo_ine` en `metricas_infraestructura` (P1), `demografia_anual` (P2) y `convocatoria_municipio` (P4), y marcar `municipios.hidratado = TRUE`.

- [ ] **Paso 2: Implementar `GET /api/municipios` (Resuelve la Consulta 1 - Sección 6.5)**
  - Soportar filtros de la **Consulta 1**:
    - `min_wlc: Optional[float]` (ej. `75.0` para *"Índice de Viabilidad WLC superior a 75 puntos"*)
    - `requiere_fibra: Optional[bool]` (para *"que cuenten con cobertura de fibra óptica"*)
    - `con_ayuda_abierta: Optional[bool]` (para cruzar con municipios que tienen subvenciones activas en `convocatoria_municipio`)
    - `semaforo: Optional[str]` (`VERDE`, `AMBAR`, `ROJO`)

- [ ] **Paso 3: Implementar `GET /api/municipios/{codigo_ine}` (Resuelve la Consulta 2 y Fusión en Memoria - Sección 6.5 y 7.3)**
  - Seguir los **4 pasos exactos del Mediador (Sección 7.3 y Diagrama Sección 9)**:
    1. Asegurar hidratación materializada (`ensure_municipio_hydrated`) y leer padrón, infraestructuras y ayudas abiertas desde PostgreSQL.
    2. Identificar el centro asistencial de urgencias más cercano mediante KNN en PostGIS (`get_nearest_health_centers_for_municipio`).
    3. Realizar la llamada REST en tiempo real a `calculate_route_cartociudad(...)` obteniendo los minutos de viaje y km de trayecto (**Consulta 2**), sin guardarlos en tablas.
    4. Invocar en memoria a `evaluate_wlc_for_municipio(...)` combinando los indicadores estáticos con los minutos en vivo de CartoCiudad, y devolver `MunicipioDetailSchema`.

- [ ] **Paso 4: Implementar `GET /api/municipios/{codigo_ine}/demografia` (Resuelve la Consulta 3 - Sección 6.5)**
  - Devolver la serie histórica de `demografia_anual`, la tasa de variación acumulada a 10 años y el diagnóstico de masa crítica comunitaria, lista para la **Visualización 2 (Chart.js)**.

- [ ] **Paso 5: Implementar `GET /api/convocatorias` (Resuelve la Consulta 4 - Sección 6.5)**
  - Devolver las convocatorias aplicables al `codigo_ine` que están abiertas (`abierta = TRUE`), incluyendo `descripcion`, `organo_convocante` (`organo_nivel1/2/3`), `presupuesto_total`, `fin_solicitud`, `url_bases` y `regla_asignacion` (`organo_local | umbral_poblacion | region_completa`).
