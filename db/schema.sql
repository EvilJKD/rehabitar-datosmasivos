-- =============================================================================
-- RE-HABITAR PoC: Esquema DDL (PostgreSQL + PostGIS, compatible con Citus)
-- =============================================================================

-- Habilitar la extensión espacial PostGIS (en despliegue Citus: CREATE EXTENSION IF NOT EXISTS citus;)
CREATE EXTENSION IF NOT EXISTS postgis;


-- =============================================================================
-- 1. CATÁLOGO MUNICIPAL: `municipios` (Reference Table / clave `codigo_ine`)
-- =============================================================================
CREATE TABLE IF NOT EXISTS municipios (
    codigo_ine VARCHAR(5) PRIMARY KEY CHECK (codigo_ine ~ '^[0-9]{5}$'),
    nombre VARCHAR(120) NOT NULL,
    provincia VARCHAR(80) NOT NULL DEFAULT 'Madrid',
    comarca VARCHAR(100) NOT NULL DEFAULT 'Sin clasificar',
    latitud DOUBLE PRECISION NOT NULL CHECK (latitud BETWEEN -90 AND 90),
    longitud DOUBLE PRECISION NOT NULL CHECK (longitud BETWEEN -180 AND 180),
    geom geometry(Point, 4326) NOT NULL,
    hidratado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_hidratacion TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_municipios_geom ON municipios USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_municipios_provincia_hidratado ON municipios (provincia, hidratado);


-- =============================================================================
-- 2. SERIE DEMOGRÁFICA: `demografia_anual` (Tabla distribuida por `codigo_ine`)
-- =============================================================================
-- Serie anual de población del Padrón municipal (INE tabla 2881).
-- Clave primaria compuesta (`codigo_ine`, `anio`) para co-localización en Citus;
-- las columnas de edad admiten NULL cuando no hay dato disponible en la fuente.
CREATE TABLE IF NOT EXISTS demografia_anual (
    codigo_ine          VARCHAR(5)    NOT NULL
                        REFERENCES municipios (codigo_ine) ON DELETE CASCADE,
    anio                SMALLINT      NOT NULL CHECK (anio BETWEEN 1900 AND 2100),
    poblacion           INTEGER       NOT NULL CHECK (poblacion >= 0),
    poblacion_mayor_65  INTEGER       CHECK (poblacion_mayor_65 >= 0),
    poblacion_menor_15  INTEGER       CHECK (poblacion_menor_15 >= 0),
    tasa_envejecimiento NUMERIC(5, 2) CHECK (tasa_envejecimiento BETWEEN 0 AND 100),
    CONSTRAINT pk_demografia_anual PRIMARY KEY (codigo_ine, anio)
);

-- Índice por año y municipio para consultas de variación demográfica sobre todo el territorio.
CREATE INDEX IF NOT EXISTS idx_demografia_anio_codigo ON demografia_anual (anio, codigo_ine);


-- =============================================================================
-- 3. INFRAESTRUCTURA Y CONECTIVIDAD: `metricas_infraestructura` (Tabla distribuida por `codigo_ine`)
-- =============================================================================
CREATE TABLE IF NOT EXISTS metricas_infraestructura (
    codigo_ine VARCHAR(5) PRIMARY KEY REFERENCES municipios(codigo_ine) ON DELETE CASCADE,
    distancia_carretera_km NUMERIC(6, 2) NOT NULL CHECK (distancia_carretera_km >= 0),
    distancia_recurso_hidrico_km NUMERIC(6, 2) NOT NULL CHECK (distancia_recurso_hidrico_km >= 0),
    cobertura_fibra_pct NUMERIC(5, 2) NOT NULL CHECK (cobertura_fibra_pct BETWEEN 0 AND 100),
    cobertura_movil_pct NUMERIC(5, 2) NOT NULL CHECK (cobertura_movil_pct BETWEEN 0 AND 100),
    fecha_actualizacion DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE INDEX IF NOT EXISTS idx_infra_cobertura_fibra
    ON metricas_infraestructura (cobertura_fibra_pct) WHERE cobertura_fibra_pct > 0;


-- =============================================================================
-- 4. DIRECTORIO ASISTENCIAL: `centros_sanitarios` (Reference Table)
-- =============================================================================
CREATE TABLE IF NOT EXISTS centros_sanitarios (
    id_centro           VARCHAR(40) PRIMARY KEY,
    nombre              VARCHAR(200) NOT NULL,
    tipo                VARCHAR(100) NOT NULL,
    tiene_urgencias     BOOLEAN NOT NULL DEFAULT FALSE,
    municipio_nombre    VARCHAR(120),
    direccion           VARCHAR(250),
    horario             VARCHAR(120),
    telefono            VARCHAR(30),
    latitud             DOUBLE PRECISION NOT NULL CHECK (latitud BETWEEN -90 AND 90),
    longitud            DOUBLE PRECISION NOT NULL CHECK (longitud BETWEEN -180 AND 180),
    geom                geometry(Point, 4326) NOT NULL
);

-- Índice espacial GiST general sobre `geom`
CREATE INDEX IF NOT EXISTS idx_centros_sanitarios_geom
    ON centros_sanitarios USING GIST (geom);

-- Índice espacial GiST parcial para centros con urgencias médicas
CREATE INDEX IF NOT EXISTS idx_centros_urgencias_geom
    ON centros_sanitarios USING GIST (geom)
    WHERE tiene_urgencias = TRUE;

-- Índice B-Tree por municipio para búsquedas administrativas locales
CREATE INDEX IF NOT EXISTS idx_centros_sanitarios_municipio
    ON centros_sanitarios (municipio_nombre);


-- =============================================================================
-- 5. AYUDAS Y SUBVENCIONES: `convocatorias` y `convocatoria_municipio`
-- =============================================================================

-- 5.1 `convocatorias` (Reference Table replicada en todos los nodos).
-- `poblacion_max_objetivo` admite NULL si no hay umbral poblacional y `abierta` refleja el estado al extraer.
CREATE TABLE IF NOT EXISTS convocatorias (
    codigo_bdns            VARCHAR(30)    PRIMARY KEY,                 -- Ej. '921084'
    descripcion            TEXT           NOT NULL,                    -- Título/objeto de la ayuda
    organo_nivel1          VARCHAR(150)   NOT NULL,                    -- 'ESTADO' | 'AUTONOMICA' | 'LOCAL' | 'OTROS'
    organo_nivel2          VARCHAR(150),                               -- Comunidad autónoma o municipio convocante
    organo_nivel3          VARCHAR(150),                               -- Consejería o unidad administrativa
    organo_convocante      TEXT GENERATED ALWAYS AS (COALESCE(organo_nivel3, organo_nivel2, organo_nivel1)) STORED,
    fecha_recepcion        DATE           NOT NULL DEFAULT CURRENT_DATE,
    inicio_solicitud       DATE,
    fin_solicitud          DATE,
    abierta                BOOLEAN        NOT NULL DEFAULT TRUE,       -- Filtro de convocatorias abiertas
    presupuesto_total      NUMERIC(14, 2) NOT NULL DEFAULT 0.00 CHECK (presupuesto_total >= 0),
    tipo_beneficiario      VARCHAR(150),
    finalidad              VARCHAR(150),                               -- Categoría (descripcionFinalidad BDNS)
    poblacion_max_objetivo INTEGER        CHECK (poblacion_max_objetivo > 0),  -- NULL = sin umbral
    url_bases              TEXT,
    fecha_extraccion       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Índice parcial para listar convocatorias abiertas ordenadas por fin de plazo.
CREATE INDEX IF NOT EXISTS idx_convocatorias_abiertas_fin
    ON convocatorias (fin_solicitud)
    WHERE abierta = TRUE;

-- Índice por órgano para localizar convocatorias de entidades locales.
CREATE INDEX IF NOT EXISTS idx_convocatorias_organo
    ON convocatorias (organo_nivel1, organo_nivel2);


-- 5.2 `convocatoria_municipio` (Tabla distribuida por `codigo_ine`, co-localizada en Citus).
CREATE TABLE IF NOT EXISTS convocatoria_municipio (
    codigo_ine        VARCHAR(5)  NOT NULL REFERENCES municipios (codigo_ine) ON DELETE CASCADE,
    codigo_bdns       VARCHAR(30) NOT NULL REFERENCES convocatorias (codigo_bdns) ON DELETE CASCADE,
    regla_asignacion  VARCHAR(30) NOT NULL
                      CHECK (regla_asignacion IN ('organo_local', 'umbral_poblacion', 'region_completa')),
    fecha_asignacion  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_convocatoria_municipio PRIMARY KEY (codigo_ine, codigo_bdns)
);

-- Índice inverso por convocatoria para consultas por ayuda y borrados en cascada.
CREATE INDEX IF NOT EXISTS idx_convocatoria_municipio_bdns
    ON convocatoria_municipio (codigo_bdns);
