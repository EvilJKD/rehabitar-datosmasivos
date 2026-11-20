/**
 * Módulo Conector Cliente (`api.js`)
 * Gestiona las peticiones hacia FastAPI, incluyendo la hidratación bajo demanda
 * cuando el usuario selecciona un municipio en el mapa o selector.
 */

const ReHabitarAPI = (() => {
    const BASE_URL = "/api";

    /**
     * TODO: Construir el query string opcional `?w_demo=...&w_health=...&w_grants=...&w_infra=...`
     */
    function buildWeightQuery(weights) {
        return "";
    }

    /**
     * TODO: Obtener todos los municipios (`GET /api/municipios`), tanto los ya hidratados
     * (`hidratado: true`) como los pendientes de ingesta bajo demanda (`hidratado: false`).
     */
    async function fetchMunicipios(weights = null) {
        // TODO: Implementar fetch a `${BASE_URL}/municipios`
    }

    /**
     * TODO: Obtener el detalle de un municipio (`GET /api/municipios/{codigoIne}`).
     * Si el municipio aún no estaba hidratado en PostgreSQL, esta llamada dispara
     * automáticamente en el backend la ingesta desde INE, BDNS y CartoCiudad, guarda
     * el registro en la base de datos y devuelve el objeto completo con `origen_datos`.
     */
    async function fetchMunicipioDetail(codigoIne, weights = null, forceRefresh = false) {
        // TODO: Implementar fetch a `${BASE_URL}/municipios/${codigoIne}`
    }

    /**
     * TODO: Forzar explícitamente la re-ingesta en vivo de un municipio (`POST /api/municipios/{codigoIne}/ingest`).
     */
    async function triggerMunicipioIngestion(codigoIne) {
        // TODO: Implementar fetch POST a `${BASE_URL}/municipios/${codigoIne}/ingest`
    }

    /**
     * TODO: Obtener la serie demográfica 2015-2025 (`GET /api/municipios/{codigoIne}/demografia`).
     */
    async function fetchMunicipioDemografia(codigoIne) {
        // TODO: Implementar fetch a `${BASE_URL}/municipios/${codigoIne}/demografia`
    }

    /**
     * TODO: Obtener la red de centros sanitarios (`GET /api/centros-sanitarios`).
     */
    async function fetchCentrosSanitarios() {
        // TODO: Implementar fetch a `${BASE_URL}/centros-sanitarios`
    }

    /**
     * TODO: Obtener las convocatorias BDNS (`GET /api/convocatorias`).
     */
    async function fetchConvocatorias(codigoIne = null) {
        // TODO: Implementar fetch a `${BASE_URL}/convocatorias`
    }

    return {
        fetchMunicipios,
        fetchMunicipioDetail,
        triggerMunicipioIngestion,
        fetchMunicipioDemografia,
        fetchCentrosSanitarios,
        fetchConvocatorias,
    };
})();
