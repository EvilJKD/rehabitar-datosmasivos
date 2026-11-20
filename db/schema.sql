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
-- IMPORTANTE PARA ESCALABILIDAD CITUS:
-- No usar `id SERIAL PRIMARY KEY`. La clave primaria DEBE ser compuesta `(codigo_ine, anio)`
-- para incluir la columna de particionamiento `codigo_ine`.
-- Columnas requeridas:
--   - codigo_ine VARCHAR(5) NOT NULL REFERENCES municipios(codigo_ine) ON DELETE CASCADE
--   - anio SMALLINT NOT NULL CHECK (anio BETWEEN 1900 AND 2100)
--   - poblacion INTEGER NOT NULL CHECK (poblacion >= 0)
--   - poblacion_mayor_65 INTEGER DEFAULT 0              -- Opcional (Tablas INE 2881/69744 para masa crítica)
--   - poblacion_menor_15 INTEGER DEFAULT 0
--   - tasa_envejecimiento NUMERIC(5, 2) DEFAULT 0.00
--   - PRIMARY KEY (codigo_ine, anio)
--
-- Índice a crear para Consulta 3 (variación a 10 años):
--   - CREATE INDEX IF NOT EXISTS idx_demografia_anio_codigo ON demografia_anual (anio, codigo_ine);


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
-- TODO 4 (Responsable P3): Tabla `centros_sanitarios` (Sección 7.1.4)
-- Rol en Citus: Reference Table (replicada en los workers para consultas espaciales KNN)
-- =============================================================================
-- Directorio asistencial de la Comunidad de Madrid:
--   - id_centro VARCHAR(40) PRIMARY KEY                 -- Ej. 'CS-28027'
--   - nombre VARCHAR(200) NOT NULL                      -- Ej. 'Consultorio Local Buitrago del Lozoya'
--   - tipo VARCHAR(100) NOT NULL                        -- Ej. 'Centro de Salud / Urgencias', 'Consultorio Local'
--   - tiene_urgencias BOOLEAN NOT NULL DEFAULT FALSE    -- Discriminador para Consulta 2 e Indicador 2 WLC
--   - municipio_nombre VARCHAR(120)
--   - direccion VARCHAR(250)
--   - horario VARCHAR(120)
--   - telefono VARCHAR(30)
--   - latitud DOUBLE PRECISION NOT NULL CHECK (latitud BETWEEN -90 AND 90)
--   - longitud DOUBLE PRECISION NOT NULL CHECK (longitud BETWEEN -180 AND 180)
--   - geom geometry(Point, 4326) NOT NULL               -- Punto PostGIS para operador KNN `<->`
--
-- Índices espaciales GiST a crear:
--   - CREATE INDEX IF NOT EXISTS idx_centros_sanitarios_geom ON centros_sanitarios USING GIST (geom);
--   - CREATE INDEX IF NOT EXISTS idx_centros_urgencias_geom ON centros_sanitarios USING GIST (geom) WHERE tiene_urgencias = TRUE;


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
