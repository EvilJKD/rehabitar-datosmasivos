# 📋 TODO List — Servicios de Negocio P1 a P5 (`backend/services/`) · Alineado con Propuesta Oficial

Cada servicio implementa las consultas y reglas descritas en las **Secciones 4, 6.3, 6.5, 7.1, 7.2, 7.3 y 9** del documento de propuesta:

---

## 1. Desarrollador P1 — `p1_geo_service.py` (NGBE + Infraestructura Materializada)
- [ ] **`get_all_municipios_base(db)`**: Consultar `municipios m LEFT JOIN metricas_infraestructura mi ON mi.codigo_ine = m.codigo_ine` devolviendo `codigo_ine`, `nombre`, `provincia`, `comarca`, `latitud`, `longitud`, `hidratado`, `distancia_carretera_km`, `distancia_recurso_hidrico_km`, `cobertura_fibra_pct` y `cobertura_movil_pct`.
- [ ] **`get_municipio_by_ine(db, codigo_ine)`**: Consultar los campos anteriores para un único `codigo_ine`.
- [ ] **`hydrate_infraestructura_on_demand(db, codigo_ine)`**: Si el municipio seleccionado en el Frontend aún no tiene fila en `metricas_infraestructura`, invocar a `ingest_infraestructura_municipio(codigo_ine)` para insertarla en PostgreSQL.

---

## 2. Desarrollador P2 — `p2_demo_service.py` (Consulta 3: Análisis de Inercia Poblacional)
- [ ] **`hydrate_demografia_on_demand(db, codigo_ine)`**: Si el municipio seleccionado no tiene serie en `demografia_anual`, llamar a `ingest_ine_for_municipio(codigo_ine)` para insertarla en BD.
- [ ] **`get_demografia_summary_all(db)`** y **`get_demografia_serie_by_municipio(db, codigo_ine)`**:
  - Resolver la **Consulta 3 (Sección 6.5)**: calcular la tasa de variación acumulada de población a 10 años ($\frac{P_{actual} - P_{actual-10}}{P_{actual-10}} \times 100$, ej. Madarcos `-7.84%`) y evaluar si preserva masa crítica comunitaria.

---

## 3. Desarrollador P3 — `p3_health_service.py` (PostGIS KNN `<->` para Consulta 2)
- [ ] **`get_nearest_emergency_all(db)`** y **`get_nearest_health_centers_for_municipio(db, codigo_ine)`**:
  - Localizar el centro asistencial con `tiene_urgencias = TRUE` más cercano (ej. `CS-28027` Buitrago del Lozoya para Madarcos) usando el operador espacial KNN `ORDER BY m.geom <-> cs.geom LIMIT 1` sobre el índice GiST `idx_centros_urgencias_geom`.

---

## 4. Desarrollador P4 — `p4_grants_service.py` (Consulta 4: Ayudas Abiertas del Municipio)
- [ ] **`hydrate_grants_on_demand(db, codigo_ine)`**: Si el municipio aún no ha sido cruzado en `convocatoria_municipio`, invocar a `ingest_bdns_for_municipio(codigo_ine)` evaluando la `regla_asignacion` (`organo_local | umbral_poblacion | region_completa`) y marcando `municipios.hidratado = TRUE`.
- [ ] **`get_convocatorias(db, codigo_ine, solo_abiertas=True)`**:
  - Resolver la **Consulta 4 (Sección 6.5)**: *"¿Qué convocatorias aplicables al municipio seleccionado están abiertas (`abierta = TRUE`), y con qué órgano convocante (`organo_convocante` / `organo_nivel1..3`), presupuesto (`presupuesto_total`), regla de asignación (`regla_asignacion`) y fecha de fin de plazo (`fin_solicitud`)?"*

---

## 5. Desarrollador P5 — `p5_cartociudad.py` y `p5_wlc_engine.py` (Consulta 1, Consulta 2 y Fusión en Memoria)
- [ ] **En `p5_cartociudad.py` (Sección 6.3 y 7.3 - Integración Virtual en Tiempo Real)**:
  - Implementar `calculate_route_cartociudad(lat_orig, lon_orig, lat_dest, lon_dest)` (con fallback `compute_fallback_route` Haversine a 45 km/h).
  - **Regla de Oro (Sección 7.3):** NO almacenar el tiempo de viaje ni la ruta en ninguna tabla de PostgreSQL; devolverlos en memoria para la **Consulta 2** y para alimentar el motor WLC.
- [ ] **En `p5_wlc_engine.py` (Sección 4 y Diagrama Sección 9 - Motor WLC en Memoria)**:
  - Implementar los **5 indicadores de habitabilidad (0-100)**:
    1. `compute_acceso_carretera_score(distancia_carretera_km)` (Peso Global 25% / PoC 40%)
    2. `compute_proximidad_sanitaria_score(tiempo_conduccion_min)` ($\le 15$ min = 100 pts, decae hasta 45 min; Peso Global 20% / PoC 30%)
    3. `compute_conectividad_digital_score(cobertura_fibra_pct, cobertura_movil_pct)` (Peso Global 20%)
    4. `compute_acceso_hidrico_score(distancia_recurso_hidrico_km)` (Peso Global 15%)
    5. `compute_inercia_demografica_score(poblacion_actual, variacion_10a_pct)` (Peso Global 20% / PoC 30%)
  - Implementar `evaluate_wlc_for_municipio(...)` que fusiona en memoria los indicadores y permite responder la **Consulta 1 (Sección 6.5)**: identificar municipios con `WLC > 75` y cobertura de fibra óptica.
