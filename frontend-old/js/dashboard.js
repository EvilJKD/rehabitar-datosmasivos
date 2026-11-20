/**
 * Visualización 2 y Controlador del Dashboard (`dashboard.js`)
 * Gestiona el panel derecho: ficha WLC, ruta sanitaria, lista de convocatorias BDNS
 * y gráfica histórica Chart.js (2015-2025).
 */

(() => {
    let allMunicipios = [];
    let currentFilter = "ALL";
    let currentIne = null;
    let demoChart = null;
    let customWeights = null;

    /**
     * TODO: Actualizar los contadores numéricos de los botones de filtro semafórico
     * (`#count-all`, `#count-rojo`, `#count-ambar`, `#count-verde`).
     * @param {Array} municipios
     */
    function updateFilterCounters(municipios) {
        // TODO: Contar cuántos municipios hay en cada estado del semáforo y actualizar el DOM
    }

    /**
     * TODO: Poblar el selector `<select id="municipio-select">` con la lista de municipios
     * para permitir cambiar de municipio también desde la barra superior.
     * @param {Array} municipios
     */
    function populateSelector(municipios) {
        // TODO: Crear elementos <option> con `codigo_ine` y nombre + WLC
    }

    /**
     * TODO: Actualizar el panel derecho del DOM con la ficha detallada del municipio:
     * - Nombre, código INE, altitud, superficie, densidad e inercia demográfica.
     * - Puntuación global del Índice WLC y su color semafórico.
     * - Barras de progreso de los 4 subíndices WLC (Demografía, Sanidad, Ayudas, Infraestructura).
     * - Datos del centro de urgencias 24h más cercano (distancia KNN, distancia carretera, minutos).
     * - Indicadores de fibra óptica, 5G y viviendas vacías.
     * @param {Object} detail - Objeto `MunicipioDetailSchema` devuelto por el backend.
     */
    function renderMunicipioDetail(detail) {
        // TODO: Volcar propiedades de `detail` en los elementos del DOM y llamar a `renderConvocatoriasList`
    }

    /**
     * TODO: Renderizar en `#grants-list` las tarjetas de las convocatorias activas de la BDNS
     * asignadas al municipio seleccionado, mostrando código BDNS, categoría, prioridad,
     * presupuesto total, importe estimado por habitante y enlace a la ficha oficial.
     * @param {Array} convocatorias
     */
    function renderConvocatoriasList(convocatorias) {
        // TODO: Construir el HTML de cada convocatoria en `#grants-list`
    }

    /**
     * TODO: Crear o actualizar la gráfica de Chart.js en el `<canvas id="demografiaChart">`
     * combinando:
     * - Eje Y izquierdo (líneas): `poblacion_total` (2015-2025) y `poblacion_mayor_65`.
     * - Eje Y derecho (barras): `ayudas_estimadas_hab_anio` (€/hab).
     * @param {Object} serieData - Objeto `DemografiaSerieResponseSchema` devuelto por el backend.
     */
    function renderDemografiaChart(serieData) {
        // TODO: Destruir instancia previa de `demoChart` si existe e instanciar `new Chart(ctx, ...)`
    }

    /**
     * TODO: Cargar en paralelo (`Promise.all`) el detalle del municipio (`fetchMunicipioDetail`)
     * y su serie demográfica (`fetchMunicipioDemografia`), actualizar el dashboard,
     * resaltar el marcador en el mapa y trazar la polilínea hacia urgencias (`drawEmergencyRoute`).
     * @param {string} codigoIne
     */
    async function selectMunicipio(codigoIne) {
        // TODO: Coordinar llamadas a ReHabitarAPI y actualizar ReHabitarMap + Dashboard
    }

    /**
     * TODO: Recargar el listado de municipios y el municipio activo cuando el usuario
     * modifique los sliders del simulador de pesos WLC.
     */
    async function refreshAllWithWeights() {
        // TODO: Llamar a `ReHabitarAPI.fetchMunicipios(customWeights)` y refrescar vista
    }

    /**
     * TODO: Asociar los listeners de eventos del DOM:
     * - Botones de filtro semafórico (`#semaforo-filters`).
     * - Selector desplegable `#municipio-select`.
     * - Sliders de pesos WLC y botón de restaurar pesos por defecto.
     */
    function bindEvents() {
        // TODO: Registrar addEventListener en los controles de la interfaz
    }

    /**
     * TODO: Función de arranque inicial al cargar el documento (`DOMContentLoaded`):
     * 1. Inicializar el mapa con `ReHabitarMap.initMap(selectMunicipio)`.
     * 2. Vincular eventos con `bindEvents()`.
     * 3. Obtener municipios y centros sanitarios desde `ReHabitarAPI`.
     * 4. Pintar capas en el mapa y seleccionar por defecto el primer municipio (ej. La Hiruela `28070`).
     */
    async function bootstrap() {
        // TODO: Implementar secuencia de inicio de la aplicación
    }

    document.addEventListener("DOMContentLoaded", bootstrap);
})();
