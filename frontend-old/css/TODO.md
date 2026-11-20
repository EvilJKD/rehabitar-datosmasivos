# 📋 TODO List — Estilos CSS de la Interfaz (`frontend/css/`)

> **Archivo a completar:** `style.css`

## Paso a Paso para Completar `frontend/css/style.css`

- [ ] **Paso 1: Definir variables CSS (`:root`) y Reset general**
  - Definir paleta de colores institucionales y colores semafóricos (`--verde: #10b981`, `--ambar: #f59e0b`, `--rojo: #ef4444`).
  - Aplicar `box-sizing: border-box; margin: 0; padding: 0;` y configurar `body` con `display: flex; flex-direction: column; height: 100vh; overflow: hidden;`.

- [ ] **Paso 2: Maquetar el Layout Principal Split-View (`.workspace`)**
  - Configurar `.workspace` con `display: grid; grid-template-columns: 45% 55%; flex: 1; overflow: hidden;`.
  - Configurar `.map-panel` con `position: relative; height: 100%;` y `#map` con `width: 100%; height: 100%;` *(imprescindible para que Leaflet renderice los tiles)*.
  - Configurar `.dashboard-panel` con `height: 100%; overflow-y: auto; padding: 1.2rem;`.

- [ ] **Paso 3: Estilizar los marcadores personalizados de Leaflet y leyendas**
  - Crear la clase `.wlc-marker-pin` (círculo con borde blanco, sombra y texto centrado con la puntuación WLC).
  - Crear la clase `.wlc-marker-selected` para resaltar el municipio activo.
  - Crear estilos para `.map-overlay`, `.map-legend` y `.route-banner`.

- [ ] **Paso 4: Estilizar las tarjetas del Dashboard (`.card`, `.kpi-grid`, `.wlc-bars`, `.grants-list`)**
  - Crear estilos para `.wlc-score-box` y sus modificadores `.semaforo-VERDE`, `.semaforo-AMBAR` y `.semaforo-ROJO`.
  - Estilizar las barras de progreso `.progress-track` y `.progress-fill`.
  - Definir `.chart-container` con `position: relative; height: 245px; width: 100%;`.
  - Estilizar las tarjetas de convocatorias `.grant-item` y sus badges de prioridad (`.prio-CRÍTICA`, `.prio-ALTA`, `.prio-MEDIA`).
