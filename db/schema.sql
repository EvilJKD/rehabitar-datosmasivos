-- =============================================================================
-- RE-HABITAR PoC: Esqueleto del Esquema DDL (PostgreSQL + PostGIS + Citus-Ready)
-- Alineado con las Secciones 4, 5.2, 6.3, 6.5, 7.1, 7.2, 7.3 y 9 de la Propuesta
-- =============================================================================

-- TODO 0 (Completado por P3): Habilitar la extensión espacial PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
-- (En despliegue distribuido Citus: CREATE EXTENSION IF NOT EXISTS citus;)


-- =============================================================================
-- P1: Tabla `municipios` (Entidad Maestra - Sección 7.1.1)
-- Rol en Citus: Reference Table (o Distributed Table líder por `codigo_ine`)
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
-- TODO 2 (Responsable P2): Tabla `demografia_anual` (Serie Histórica - Sección 7.1.2)
-- Rol en Citus: Distributed Table (shard key: `codigo_ine`)
-- =============================================================================
-- Fuente: tabla 2881 de INE Tempus (Padrón municipal), cargada por etl/p2_ine/etl_ine.py.
-- Una fila por municipio y año.
--
-- Por qué clave primaria compuesta (codigo_ine, anio) y no un id SERIAL:
--   Citus reparte (shard) esta tabla entre los workers según codigo_ine.
--   Citus exige que la PK / restricciones UNIQUE incluyan la columna de reparto; si no,
--   no puede comprobar la unicidad dentro de un único nodo.
--   Además, metricas_infraestructura y convocatoria_municipio también se reparten por codigo_ine,
--   así que los datos de un mismo municipio acaban en el mismo nodo y los JOIN por codigo_ine
--   no tienen que mover datos entre nodos (co-located join).
--
-- Por qué las tres columnas de edad admiten NULL y no llevan DEFAULT 0:
--   la tabla 69744, que el repo tenía prevista como fuente de edades, es en realidad la estadística
--   de inmigraciones entre municipios y no tiene dimensión de edad (ver la explicación al principio
--   de etl_ine.py), así que hoy no hay datos de edad utilizables.
--   NULL significa «sin dato»; con un 0 por defecto se leería como «0 mayores / tasa de envejecimiento 0 %»,
--   y funciones de agregación como AVG contarían esos 0, mientras que los NULL se ignoran solos.
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

-- La Consulta 3 (variación de población a 10 años) filtra todos los municipios por año, p. ej. WHERE anio IN (2015, 2025).
-- El índice de la PK empieza por codigo_ine y no sirve para buscar por anio, así que creamos otro que empiece por anio.
CREATE INDEX IF NOT EXISTS idx_demografia_anio_codigo ON demografia_anual (anio, codigo_ine);


-- =============================================================================
-- P1: Tabla `metricas_infraestructura` (Sección 7.1.3)
-- Rol en Citus: Distributed Table (shard key: `codigo_ine`, co-localizada con `demografia_anual`)
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
-- 4. DIRECTORIO ASISTENCIAL: `centros_sanitarios` (Sección 7.1.4 - Completado por P3)
-- Rol en Citus: Reference Table (replicada en los workers para consultas espaciales KNN)
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

-- Índice espacial GiST parcial especializado para Consulta 2 (solo centros con urgencias médicas)
CREATE INDEX IF NOT EXISTS idx_centros_urgencias_geom
    ON centros_sanitarios USING GIST (geom)
    WHERE tiene_urgencias = TRUE;

-- Índice B-Tree por municipio para búsquedas administrativas locales
CREATE INDEX IF NOT EXISTS idx_centros_sanitarios_municipio
    ON centros_sanitarios (municipio_nombre);


-- =============================================================================
-- TODO 5 (Responsable P4): Tablas `convocatorias` y `convocatoria_municipio` (Sección 7.1.5 y 7.1.6)
-- =============================================================================
-- 5.1 Tabla `convocatorias` (BDNS - Reference Table en Citus):
--   - codigo_bdns VARCHAR(30) PRIMARY KEY               -- Ej. '921084'
--   - descripcion TEXT NOT NULL                         -- Título/objeto de la ayuda
--   - organo_nivel1 VARCHAR(150) NOT NULL               -- Ej. 'COMUNIDAD DE MADRID' o 'ESTADO'
--   - organo_nivel2 VARCHAR(150)                        -- Ej. 'CONSEJERÍA DE PRESIDENCIA...'
--   - organo_nivel3 VARCHAR(150)                        -- Ej. 'DIRECCIÓN GENERAL DE REEQUILIBRIO TERRITORIAL'
--   - organo_convocante TEXT GENERATED ALWAYS AS (COALESCE(organo_nivel3, organo_nivel2, organo_nivel1)) STORED
--   - fecha_recepcion DATE NOT NULL DEFAULT CURRENT_DATE
--   - inicio_solicitud DATE
--   - fin_solicitud DATE
--   - abierta BOOLEAN NOT NULL DEFAULT TRUE             -- Filtro de Consulta 4
--   - presupuesto_total NUMERIC(14, 2) NOT NULL DEFAULT 0.00
--   - tipo_beneficiario VARCHAR(150)
--   - poblacion_max_objetivo INTEGER DEFAULT 20000      -- Umbral demográfico (ej. 20000 hab)
--   - url_bases TEXT
--
-- 5.2 Tabla `convocatoria_municipio` (Resultado de asignación - Distributed Table por `codigo_ine` en Citus):
-- IMPORTANTE PARA CITUS: Clave primaria compuesta `(codigo_ine, codigo_bdns)` con `codigo_ine` primero
-- para co-localizar los datos en el mismo nodo worker que `demografia_anual` y `metricas_infraestructura`:
--   - codigo_ine VARCHAR(5) NOT NULL REFERENCES municipios(codigo_ine) ON DELETE CASCADE
--   - codigo_bdns VARCHAR(30) NOT NULL REFERENCES convocatorias(codigo_bdns) ON DELETE CASCADE
--   - regla_asignacion VARCHAR(30) NOT NULL CHECK (regla_asignacion IN ('organo_local', 'umbral_poblacion', 'region_completa'))
--   - fecha_asignacion TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
--   - PRIMARY KEY (codigo_ine, codigo_bdns)
