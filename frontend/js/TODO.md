# 📋 TODO List — Lógica JavaScript del Frontend (`frontend/js/`) · Alineado con Sección 6.4, 6.5 y 7.3

> **Archivos a completar:** `api.js`, `map.js` y `dashboard.js`

---

## 1. Paso a Paso para `frontend/js/api.js` (Conector REST a las 4 Consultas)
- [ ] **Paso 1.1 (`fetchMunicipios`)**: Soportar los parámetros de la **Consulta 1**: `min_wlc` (ej. `75`), `requiere_fibra` (`true`), `con_ayuda_abierta` (`true`) y `semaforo`.
- [ ] **Paso 1.2 (`fetchMunicipioDetail`)**: Llamar a `GET /api/municipios/{codigo_ine}`, que en el Backend dispara la **Ingesta Híbrida Materializada** (si `hidratado == false`) y ejecuta en vivo la **Fusión en Memoria con CartoCiudad** (**Consulta 2**, Sección 7.3).
- [ ] **Paso 1.3 (`fetchMunicipioDemografia`)**: Llamar a `GET /api/municipios/{codigo_ine}/demografia` (**Consulta 3**).
- [ ] **Paso 1.4 (`fetchConvocatorias`)**: Llamar a `GET /api/convocatorias?codigo_ine={codigo_ine}&abierta=true` (**Consulta 4**).

---

## 2. Paso a Paso para `frontend/js/map.js` (Visualización 1 - Sección 6.4)
- [ ] **Paso 2.1 (`initMap`)**: Inicializar el visor cartográfico con teselas OpenStreetMap centrado en la Sierra Norte de Madrid (`[40.965, -3.575]`, zoom `10`).
- [ ] **Paso 2.2 (`renderCentrosSanitarios`)**: Representar los consultorios locales y centros de salud con urgencias (`CS-28027` Buitrago, etc.).
- [ ] **Paso 2.3 (`renderMunicipios`)**: Pintar los marcadores tematizados y coloreados según el Índice de Viabilidad WLC (`VERDE`, `AMBAR`, `ROJO`, o gris si aún está pendiente de hidratación bajo demanda).
- [ ] **Paso 2.4 (`drawEmergencyRoute`)**: Trazar la ruta exacta en vehículo privado devuelta en tiempo real por CartoCiudad y mostrar en pantalla los kilómetros y minutos de conducción (**Consulta 2**).

---

## 3. Paso a Paso para `frontend/js/dashboard.js` (Visualización 2 y Ficha de 5 Parámetros)
- [ ] **Paso 3.1 (`renderMunicipioDetail`)**:
  - Mostrar la Puntuación de Viabilidad Global WLC (0-100) y las **5 barras de progreso de habitabilidad (Sección 4 y 6.4)**:
    1. `score_acceso_carretera` (`distancia_carretera_km`)
    2. `score_proximidad_sanitaria` (`tiempo_estimado_min` en tiempo real desde CartoCiudad)
    3. `score_conectividad_digital` (`cobertura_fibra_pct` y `cobertura_movil_pct`)
    4. `score_acceso_hidrico` (`distancia_recurso_hidrico_km`)
    5. `score_inercia_demografica` (`variacion_10a_pct`)
- [ ] **Paso 3.2 (`renderConvocatoriasList` - Consulta 4)**:
  - Renderizar las convocatorias abiertas aplicables al municipio mostrando su `organo_convocante`, `presupuesto_total`, `fin_solicitud` y la `regla_asignacion` (`organo_local | umbral_poblacion | region_completa`).
- [ ] **Paso 3.3 (`renderDemografiaChart` - Visualización 2 y Consulta 3)**:
  - Implementar en `Chart.js` el gráfico bivariable que permite seleccionar uno o varios municipios rurales y comparar su evolución poblacional de los últimos 10 años frente a su conectividad / distancia asistencial / ayudas activas.
