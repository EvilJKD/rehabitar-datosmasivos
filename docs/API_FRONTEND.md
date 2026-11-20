# Guía del API para el Frontend — Re-Habitar PoC

Documento pensado para el equipo de interfaz web (UI). Explica en lenguaje sencillo qué ofrece cada endpoint del backend (`backend/main.py`), qué datos devuelve y en qué pantallas o componentes de la propuesta del proyecto se recomienda usarlo.

Todos los endpoints devuelven respuestas en formato JSON y el servidor incluye soporte CORS abierto para facilitar el desarrollo local del frontend.

---

## 1. Estado del sistema y progreso de carga

### `GET /api/health`

**Qué hace:** Comprueba que el servidor y la base de datos responden correctamente y dice cuántos municipios tienen ya sus datos completos guardados.

**Qué contiene la respuesta:**
- `status`: estado del servicio (`"ok"` cuando todo funciona).
- `database`: nombre del motor de base de datos activo.
- `total_municipios`: número total de municipios cargados en el catálogo.
- `municipios_hidratados`: cuántos de esos municipios ya tienen descargados sus datos de población, infraestructuras, sanidad y ayudas.

**Hints para el UI:**
- **Barra de estado o cabecera:** mostrar un indicador discreto tipo *"Sistema conectado · X de Y municipios con datos actualizados"*.
- **Pantalla de inicio / carga:** comprobar si el backend está listo antes de pedir el listado completo del mapa.

---

## 2. Mapa principal, filtros y buscador de pueblos viables

### `GET /api/municipios`

**Qué hace:** Devuelve la lista de todos los municipios disponibles con su ubicación, población reciente, fibra óptica, número de ayudas abiertas y su nota global de habitabilidad (índice WLC de 0 a 100 y color de semáforo).

**Filtros opcionales que puedes enviar en la URL:**
- `semaforo`: filtra por color (`VERDE`, `AMBAR`, `ROJO` o `PENDIENTE`).
- `min_wlc`: nota mínima de habitabilidad de `0` a `100` (por ejemplo, `75` para ver solo los más viables).
- `requiere_fibra`: si es `true`, deja solo los pueblos que cumplen el mínimo de fibra óptica.
- `min_fibra_pct`: porcentaje mínimo de fibra exigido cuando `requiere_fibra=true` (por defecto `50`).
- `con_ayuda_abierta`: `true` para ver solo pueblos con subvenciones activas hoy, o `false` para los que no tienen ninguna.
- **Pesos personalizados (entre `0` y `1`):** `w_carretera`, `w_sanidad`, `w_conectividad`, `w_hidrico`, `w_demografia` (también acepta los alias `w_demo`, `w_health`, `w_infra`). Permiten cambiar la importancia de cada criterio al vuelo sin recargar la página.

**Qué contiene cada municipio de la lista:**
- Identificación y mapa: `codigo_ine`, `nombre`, `provincia`, `comarca`, `latitud`, `longitud`.
- Estado de carga: `hidratado` (`true` si ya tiene todos sus datos descargados; si es `false`, su semáforo será `"PENDIENTE"`).
- Resumen rápido: `poblacion_actual`, `variacion_10a_pct` (porcentaje ganado o perdido en 10 años), `cobertura_fibra_pct` y `num_ayudas_abiertas`.
- Bloque `wlc` (semáforo y desglose): `indice_wlc` (0-100), `semaforo` (`VERDE`, `AMBAR`, `ROJO`, `PENDIENTE`), `etiqueta_viabilidad` y las 5 notas parciales (`score_acceso_carretera`, `score_proximidad_sanitaria`, `score_conectividad_digital`, `score_acceso_hidrico`, `score_inercia_demografica`), además de `pesos_aplicados`.

**Hints para el UI (Propuesta Sección 6.4 y 6.5):**
- **Visualización 1 (Mapa Temático Interactivo):** es la llamada principal al abrir la web. Pinta un marcador en `(latitud, longitud)` coloreado según `wlc.semaforo` (verde, ámbar, rojo o gris para `PENDIENTE`).
- **Consulta 1 ("¿Qué pueblos tienen WLC > 75 y fibra?"):** implementa un botón de filtro rápido o barra de filtros que llame a `GET /api/municipios?min_wlc=75&requiere_fibra=true`.
- **Filtro de ayudas activas:** un interruptor *"Solo pueblos con subvenciones abiertas"* conectado a `con_ayuda_abierta=true`.
- **Simulador de prioridades (sliders):** añade 5 controles deslizantes (*Carretera, Sanidad, Internet, Agua, Población*) para que el ciudadano o emprendedor ajuste qué valora más y el mapa recoloree los pueblos al instante usando los parámetros `w_*`.
- **Selector de municipios para comparar:** reutiliza esta lista para poblar el desplegable o buscador de la Visualización 2 (gráficas).

---

## 3. Ficha completa del pueblo y ruta en tiempo real a urgencias

### `GET /api/municipios/{codigo_ine}`

**Qué hace:** Es el endpoint estrella al elegir un pueblo. Si el municipio aún estaba `"PENDIENTE"`, el servidor descarga automáticamente sus datos reales en ese momento, calcula en tiempo real la ruta por carretera hasta el centro de urgencias más cercano y devuelve la ficha completa lista para mostrar.

**Parámetros opcionales:**
- `force_refresh=true`: obliga a volver a consultar las fuentes externas en lugar de usar los datos guardados.
- `w_carretera`, `w_sanidad`, `w_conectividad`, `w_hidrico`, `w_demografia` (y alias `w_demo`, `w_health`, `w_infra`): recalculan la nota WLC del pueblo con prioridades personalizadas.

**Qué contiene la ficha:**
- **Datos básicos:** `codigo_ine`, `nombre`, `provincia`, `comarca`, `latitud`, `longitud`, `hidratado`, `origen_datos` (indica si salió de caché guardada o de descarga en vivo).
- **Resumen demográfico (Consulta 3):** `poblacion_inicial_10a`, `poblacion_actual`, `variacion_10a_pct`, `preserva_masa_critica` (sí/no) e `inercia_demografica` (etiqueta legible de tendencia).
- **Bloque `infraestructura`:** `distancia_carretera_km`, `distancia_recurso_hidrico_km`, `cobertura_fibra_pct`, `cobertura_movil_pct` y `fecha_actualizacion`.
- **Bloque `wlc`:** nota global `indice_wlc`, `semaforo`, `etiqueta_viabilidad` y las 5 puntuaciones parciales de 0 a 100.
- **Bloque `urgencias_mas_cercana` (Consulta 2):** nombre, tipo, dirección, horario, teléfono y coordenadas del centro sanitario más próximo, si tiene urgencias (`tiene_urgencias`), distancia en línea recta (`distancia_euclidea_km`), distancia real por carretera (`distancia_carretera_km`), tiempo estimado en coche (`tiempo_estimado_min`), cómo se calculó (`fuente_ruta`) y `geometria_ruta` (lista de puntos `[lat, lon]` para trazar la línea de la ruta).
- **Lista `convocatorias` (Consulta 4):** subvenciones abiertas aplicables a ese pueblo (misma estructura que `/api/convocatorias`).

**Hints para el UI (Propuesta Sección 6.4, 6.5 y 7.3):**
- **Panel lateral o modal al hacer clic en un pueblo del mapa (Visualización 1):** muestra el semáforo grande arriba, tarjetas con los 5 indicadores de habitabilidad (barras de progreso o gráfico radial 0-100) y las insignias de `inercia_demografica` y `preserva_masa_critica`.
- **Consulta 2 (Ruta sanitaria en el mapa):** cuando llegue `urgencias_mas_cercana.geometria_ruta`, dibuja la línea del trayecto en el mapa desde el pueblo hasta el centro médico y muestra una tarjeta destacada: *"Urgencias más cercanas: [nombre] · [tiempo_estimado_min] min ([distancia_carretera_km] km)"*, junto con su teléfono y horario.
- **Bloque "Ayudas disponibles aquí":** muestra directamente la lista `convocatorias` sin necesidad de hacer una segunda llamada extra para la vista rápida.
- **Aviso de carga en pueblos pendientes:** si el pueblo tenía `hidratado: false` en el mapa, muestra un spinner breve (*"Obteniendo datos oficiales y calculando ruta..."*) porque esta primera apertura tardará unos segundos más que las siguientes.

---

## 4. Botón para actualizar datos en vivo

### `POST /api/municipios/{codigo_ine}/ingest`

**Qué hace:** Fuerza la re-descarga completa de todos los datos oficiales de ese municipio (infraestructuras, padrón, sanidad, ayudas y ruta) y devuelve la misma ficha actualizada que `GET /api/municipios/{codigo_ine}`.

**Qué contiene la respuesta:**
- Exactamente la misma ficha completa descrita en `GET /api/municipios/{codigo_ine}`, con `origen_datos` indicando que se acaba de refrescar en vivo.

**Hints para el UI:**
- **Botón "Actualizar datos ahora" dentro de la ficha del municipio:** útil para técnicos de ayuntamiento o usuarios que quieran asegurarse de tener la última convocatoria publicada hoy o el último dato disponible. Conviene mostrar un estado de carga mientras termina la petición.

---

## 5. Gráfica histórica de población y comparativa multivariable

### `GET /api/municipios/{codigo_ine}/demografia`

**Qué hace:** Devuelve la evolución año a año de la población de un municipio (serie histórica 2015-2025) junto con indicadores clave de contexto para poder cruzarla visualmente con servicios y ayudas.

**Qué contiene la respuesta:**
- `codigo_ine` y `nombre`.
- `poblacion_inicial_10a`, `poblacion_actual` y `variacion_10a_pct`.
- Indicadores de contexto para comparar: `cobertura_fibra_pct`, `distancia_urgencias_km` y `num_ayudas_abiertas`.
- `serie_anual`: lista ordenada por año con `anio`, `poblacion`, y (cuando la fuente lo desglosa) `poblacion_mayor_65`, `poblacion_menor_15` y `tasa_envejecimiento`.

**Hints para el UI (Propuesta Sección 6.4 — Visualización 2 y Consulta 3):**
- **Visualización 2 (Dashboard Analítico con Chart.js):**
  - **Gráfica de líneas temporal:** usa `serie_anual` (`anio` en el eje X y `poblacion` en el eje Y). Si el usuario selecciona 2 o 3 pueblos para comparar, haz una llamada por cada `codigo_ine` y dibuja varias líneas en la misma gráfica.
  - **Gráfica multivariable o de burbujas/barras comparativas:** cruza `variacion_10a_pct` con `cobertura_fibra_pct`, `distancia_urgencias_km` y `num_ayudas_abiertas` para ver de un vistazo si los pueblos con mejor fibra o más ayudas frenan mejor la pérdida de vecinos.
  - **Tarjeta de envejecimiento:** si `tasa_envejecimiento`, `poblacion_mayor_65` o `poblacion_menor_15` traen valor (no son `null`), muéstralos como detalle demográfico; si vienen en `null`, oculta el desglose por edades con elegancia.

---

## 6. Buscador y listado de ayudas y subvenciones públicas

### `GET /api/convocatorias`

**Qué hace:** Lista las subvenciones oficiales de la BDNS. Si indicas un municipio, devuelve las que aplican a ese pueblo y explica por qué criterio le corresponden; si no indicas municipio, devuelve el catálogo general.

**Filtros opcionales en la URL:**
- `codigo_ine`: código del municipio para ver solo las ayudas que le aplican.
- `categoria`: palabra clave para filtrar por finalidad (por ejemplo `Infraestructuras` o `vivienda`).
- `solo_abiertas` (o su alias `abierta`): por defecto `true` para mostrar solo ayudas cuyo plazo sigue abierto hoy; envíalo como `false` si quieres incluir convocatorias ya cerradas.

**Qué contiene cada convocatoria:**
- `codigo_bdns`, `descripcion` (título de la ayuda) y `finalidad`.
- Quién la convoca: `organo_convocante` (y niveles `organo_nivel1`, `organo_nivel2`, `organo_nivel3`).
- Plazos y estado: `fecha_recepcion`, `inicio_solicitud`, `fin_solicitud` (puede ser `null` si no se publicó fecha de cierre) y `abierta` (`true`/`false`).
- Importe y destinatarios: `presupuesto_total`, `tipo_beneficiario`, `poblacion_max_objetivo` (si la ayuda exige menos de X habitantes) y `url_bases` (enlace oficial).
- `regla_asignacion` (cuando se filtra por `codigo_ine`): explica por qué aplica al pueblo (`"organo_local"`, `"umbral_poblacion"` o `"region_completa"`).

**Hints para el UI (Propuesta Sección 6.5 — Consulta 4):**
- **Pestaña o tabla "Ayudas y Subvenciones":** muestra una tabla filtrable con título, organismo convocante, presupuesto formateado en euros, fecha límite (`fin_solicitud`, o *"Sin fecha de cierre publicada"* si es `null`) y un botón *"Ver bases oficiales"* que abra `url_bases` en una nueva pestaña.
- **Etiqueta explicativa de elegibilidad:** usa `regla_asignacion` para mostrar un chip informativo al usuario (por ejemplo: *"Por tamaño de población"*, *"Ayuda autonómica"* o *"Ayuda local"*).
- **Filtros de búsqueda:** caja de texto para `categoria`, selector de pueblo (`codigo_ine`) y casilla *"Incluir convocatorias cerradas"* (`solo_abiertas=false`).

---

## 7. Capa de centros sanitarios para el mapa

### `GET /api/centros-sanitarios`

**Qué hace:** Devuelve el directorio geolocalizado de centros de salud, consultorios y puntos de urgencias de la Comunidad de Madrid.

**Filtros opcionales en la URL:**
- `solo_urgencias`: `true` para recibir únicamente centros con atención continuada o urgencias 24h.
- `municipio_nombre`: filtra los centros ubicados en un municipio concreto (por ejemplo `Buitrago del Lozoya`).
- `force_refresh`: `true` si se desea forzar la actualización desde Datos Abiertos de la Comunidad de Madrid.

**Qué contiene cada centro:**
- `id_centro`, `nombre`, `tipo` (Centro de Salud, Consultorio Local, etc.) y `tiene_urgencias` (`true`/`false`).
- Ubicación y contacto: `municipio_nombre`, `direccion`, `horario`, `telefono`, `latitud`, `longitud`.

**Hints para el UI (Propuesta Sección 6.4 — Mapa V1):**
- **Capa opcional en el mapa (toggle "Mostrar centros sanitarios"):** dibuja pines con icono de cruz médica encima del mapa de municipios, diferenciando visualmente los de urgencias 24h (`tiene_urgencias=true`) de los consultorios locales.
- **Tooltip o popup rápido:** al pasar o pulsar sobre un pin sanitario, muestra `nombre`, `tipo`, `horario` y `telefono`.

---

## Resumen rápido: qué endpoint usar en cada vista

| Vista o componente del UI | Endpoint recomendado |
| :--- | :--- |
| Barra de estado inicial | `GET /api/health` |
| Mapa principal de municipios y semáforos (V1 + Consulta 1) | `GET /api/municipios` |
| Capa de hospitales y centros médicos en el mapa | `GET /api/centros-sanitarios` |
| Ficha del pueblo al hacer clic + ruta a urgencias (V1 + Consulta 2) | `GET /api/municipios/{codigo_ine}` |
| Botón "Actualizar datos en vivo" dentro de la ficha | `POST /api/municipios/{codigo_ine}/ingest` |
| Gráficas comparativas de población 2015-2025 (V2 + Consulta 3) | `GET /api/municipios/{codigo_ine}/demografia` |
| Buscador y tabla de subvenciones abiertas (Consulta 4) | `GET /api/convocatorias` |
