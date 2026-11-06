/**
 * Módulo Conector Cliente (`api.js`)
 * Centraliza todas las llamadas `fetch` asíncronas hacia los endpoints de FastAPI.
 */

const ReHabitarAPI = (() => {
    const BASE_URL = "/api";

    /**
     * TODO: Construir el query string opcional `?w_demo=...&w_health=...&w_grants=...&w_infra=...`
     * cuando el usuario ajuste los pesos del simulador WLC.
     * @param {Object|null} weights
     * @returns {string}
     */
    function buildWeightQuery(weights) {
        // TODO: Implementar construcción de URLSearchParams
        return "";
    }

    /**
     * TODO: Realizar petición `GET /api/municipios` para obtener el listado de municipios
     * con su puntuación del índice WLC y color semafórico (`VERDE`, `AMBAR`, `ROJO`).
     * @param {Object|null} weights
     * @returns {Promise<Array>}
     */
    async function fetchMunicipios(weights = null) {
        // TODO: Hacer fetch a `${BASE_URL}/municipios` y retornar el JSON
    }

    /**
     * TODO: Realizar petición `GET /api/municipios/{codigoIne}` para obtener el detalle
     * del municipio, desglose WLC, ruta KNN + CartoCiudad a urgencias y ayudas BDNS.
     * @param {string} codigoIne
     * @param {Object|null} weights
     * @returns {Promise<Object>}
     */
    async function fetchMunicipioDetail(codigoIne, weights = null) {
        // TODO: Hacer fetch a `${BASE_URL}/municipios/${codigoIne}` y retornar el JSON
    }

    /**
     * TODO: Realizar petición `GET /api/municipios/{codigoIne}/demografia` para obtener
     * la serie histórica 2015-2025 para el gráfico de Chart.js.
     * @param {string} codigoIne
     * @returns {Promise<Object>}
     */
    async function fetchMunicipioDemografia(codigoIne) {
        // TODO: Hacer fetch a `${BASE_URL}/municipios/${codigoIne}/demografia` y retornar el JSON
    }

    /**
     * TODO: Realizar petición `GET /api/centros-sanitarios` para cargar la capa de centros
     * de salud y urgencias de la Comunidad de Madrid en el mapa Leaflet.
     * @returns {Promise<Array>}
     */
    async function fetchCentrosSanitarios() {
        // TODO: Hacer fetch a `${BASE_URL}/centros-sanitarios` y retornar el JSON
    }

    /**
     * TODO: Realizar petición `GET /api/convocatorias` con filtro opcional `codigo_ine`.
     * @param {string|null} codigoIne
     * @returns {Promise<Array>}
     */
    async function fetchConvocatorias(codigoIne = null) {
        // TODO: Hacer fetch a `${BASE_URL}/convocatorias` y retornar el JSON
    }

    return {
        fetchMunicipios,
        fetchMunicipioDetail,
        fetchMunicipioDemografia,
        fetchCentrosSanitarios,
        fetchConvocatorias,
    };
})();
