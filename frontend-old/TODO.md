# 📋 TODO List — Estructura HTML del Frontend (`frontend/`) · Alineado con Sección 6.4 y 6.5

> **Archivo a completar en esta carpeta:** `index.html`

## Paso a Paso para Completar `frontend/index.html`

- [ ] **Paso 1: Barra Superior y Filtros de las Consultas Básicas (Sección 6.5)**
  - Incluir los filtros semafóricos del Índice de Viabilidad WLC (`Todos`, `Verde`, `Ámbar`, `Rojo`).
  - Incluir un botón/checkbox de filtro rápido para ejecutar la **Consulta 1 (Sección 6.5)**:
    *"Municipios viables con WLC > 75 + Cobertura de Fibra Óptica + Ayudas Abiertas"*.
  - Incluir el selector `<select id="municipio-select">` (con opción de comparar un segundo municipio en la gráfica de Chart.js según la **Visualización 2 de la Sección 6.4**).

- [ ] **Paso 2: Panel Izquierdo — Visualización 1: Cartografía Temática Interactiva (Sección 6.4)**
  - Contenedor `<div id="map"></div>` con teselas de OpenStreetMap.
  - Leyenda del Índice de Viabilidad WLC y tarjeta flotante (`#route-banner`) para mostrar en vivo la respuesta de la **Consulta 2 (Sección 6.5)**: distancia en km y tiempo real de conducción desde CartoCiudad hasta el servicio de urgencias médicas más próximo.

- [ ] **Paso 3: Panel Derecho — Ficha de Habitabilidad (5 Parámetros), Consultas 3 y 4 y Visualización 2**
  - **Desglose pormenorizado de los 5 parámetros de habitabilidad (Sección 4 y 6.4)**:
    1. Acceso por carretera asfaltada (Peso Global 25% / PoC 40%)
    2. Proximidad a servicios sanitarios y de urgencia en minutos de CartoCiudad (Peso Global 20% / PoC 30%)
    3. Conectividad digital: Fibra FTTH y Móvil (Peso Global 20%)
    4. Acceso a recursos hídricos (Peso Global 15%)
    5. Inercia demográfica a 10 años (Peso Global 20% / PoC 30%)
  - **Visualización 2 — Dashboard Analítico Temporal y Multivariable (Sección 6.4 y Consulta 3)**:
    - `<canvas id="demografiaChart"></canvas>` permitiendo comparar la evolución poblacional de los últimos 10 años de uno o varios municipios frente al nivel de conectividad / distancia asistencial / ayudas por año.
  - **Listado de Ayudas Abiertas del Municipio (Consulta 4 - Sección 6.5)**:
    - Contenedor `#grants-list` mostrando `codigo_bdns`, `descripcion`, `organo_convocante` (`organo_nivel1/2/3`), `presupuesto_total`, `fin_solicitud` y `regla_asignacion` (`organo_local | umbral_poblacion | region_completa`).
