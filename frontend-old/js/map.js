/**
 * Visualización 1: Mapa Temático Interactivo con Leaflet/OSM (`map.js`)
 * Responsable: Desarrollador P5 (junto con P1 y P3)
 */

const ReHabitarMap = (() => {
    let map = null;
    let municipiosLayer = null;
    let centrosLayer = null;
    let routeLayer = null;
    let onSelectCallback = null;

    /**
     * TODO: Inicializar el mapa Leaflet en el contenedor `#map` centrado en la
     * Sierra Norte de Madrid (lat: 40.965, lon: -3.575, zoom: 10), añadir la capa
     * base de OpenStreetMap (`L.tileLayer`) y crear los `L.layerGroup()` para
     * municipios, centros sanitarios y ruta de urgencias.
     * @param {Function} selectCallback - Función que se invocará al hacer clic en un municipio (`selectCallback(codigo_ine)`).
     */
    function initMap(selectCallback) {
        // TODO: Inicializar instancia L.map y capas
    }

    /**
     * TODO: Pintar en `centrosLayer` los marcadores de los centros sanitarios de la CAM,
     * distinguiendo visualmente aquellos que tienen Urgencias 24h (`tiene_urgencias === true`)
     * de los consultorios locales, y añadiendo un popup informativo con dirección y horario.
     * @param {Array} centros
     */
    function renderCentrosSanitarios(centros) {
        // TODO: Limpiar `centrosLayer` y añadir marcadores L.marker por cada centro sanitario
    }

    /**
     * TODO: Pintar en `municipiosLayer` un marcador por cada municipio usando el color
     * semafórico de su índice WLC:
     *   - `VERDE`: #10b981
     *   - `AMBAR`: #f59e0b
     *   - `ROJO`:  #ef4444
     * Al hacer clic en un marcador, debe llamar a `onSelectCallback(m.codigo_ine)`.
     * @param {Array} municipios
     * @param {string} activeFilter - Filtro activo ('ALL', 'VERDE', 'AMBAR', 'ROJO').
     */
    function renderMunicipios(municipios, activeFilter = "ALL") {
        // TODO: Limpiar `municipiosLayer`, filtrar según `activeFilter` y crear marcadores con el score WLC
    }

    /**
     * TODO: Dibujar en `routeLayer` la polilínea (`L.polyline`) entre el municipio
     * seleccionado y su centro de urgencias 24h más cercano empleando las coordenadas
     * de `municipioDetail.urgencias_mas_cercana.geometria_ruta`, y actualizar el banner
     * flotante del mapa con los kilómetros por carretera y minutos estimados.
     * @param {Object} municipioDetail
     */
    function drawEmergencyRoute(municipioDetail) {
        // TODO: Limpiar `routeLayer`, dibujar `L.polyline` y mostrar métricas de ruta
    }

    return {
        initMap,
        renderCentrosSanitarios,
        renderMunicipios,
        drawEmergencyRoute,
    };
})();
