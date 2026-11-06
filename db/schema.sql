-- =============================================================================
-- RE-HABITAR PoC: Esqueleto del Esquema DDL (PostgreSQL + PostGIS)
-- =============================================================================

-- TODO 0: Habilitar la extensión espacial PostGIS si no existe
-- CREATE EXTENSION IF NOT EXISTS postgis;


-- =============================================================================
-- TODO 1 (Responsable P1): Tabla `municipios` e Índice Espacial GiST
-- =============================================================================
-- Debe almacenar las entidades municipales de la Sierra Norte de Madrid:
--   - codigo_ine VARCHAR(10) PRIMARY KEY
--   - nombre VARCHAR(120) NOT NULL
--   - comarca VARCHAR(100) DEFAULT 'Sierra Norte'
--   - altitud_m INTEGER NOT NULL
--   - superficie_km2 NUMERIC(8, 2) NOT NULL
--   - latitud DOUBLE PRECISION NOT NULL
--   - longitud DOUBLE PRECISION NOT NULL
--   - geom geometry(Point, 4326) NOT NULL
--   - created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
--
-- Crear también índice espacial GiST sobre la columna `geom`:
--   CREATE INDEX IF NOT EXISTS idx_municipios_geom ON municipios USING GIST (geom);


-- =============================================================================
-- TODO 2 (Responsable P2): Tabla `demografia_anual`
-- =============================================================================
-- Debe almacenar las series históricas anuales del Padrón del INE (2015-2025):
--   - id SERIAL PRIMARY KEY
--   - codigo_ine VARCHAR(10) NOT NULL REFERENCES municipios(codigo_ine) ON DELETE CASCADE
--   - anio INTEGER NOT NULL
--   - poblacion_total INTEGER NOT NULL
--   - poblacion_mayor_65 INTEGER NOT NULL DEFAULT 0
--   - poblacion_menor_15 INTEGER NOT NULL DEFAULT 0
--   - tasa_envejecimiento NUMERIC(5, 2) NOT NULL DEFAULT 0.0
--   - Restricción UNIQUE (codigo_ine, anio)


-- =============================================================================
-- TODO 3 (Responsable P3): Tabla `centros_sanitarios` e Índice Espacial GiST
-- =============================================================================
-- Debe almacenar los centros de salud, consultorios y puntos de urgencias 24h (CAM):
--   - id_centro VARCHAR(40) PRIMARY KEY
--   - nombre VARCHAR(200) NOT NULL
--   - tipo_centro VARCHAR(100) NOT NULL
--   - municipio_nombre VARCHAR(120) NOT NULL
--   - direccion VARCHAR(250)
--   - tiene_urgencias BOOLEAN NOT NULL DEFAULT FALSE
--   - horario VARCHAR(120)
--   - telefono VARCHAR(30)
--   - latitud DOUBLE PRECISION NOT NULL
--   - longitud DOUBLE PRECISION NOT NULL
--   - geom geometry(Point, 4326) NOT NULL
--
-- Crear índice espacial GiST sobre `geom` para acelerar consultas KNN (`<->`):
--   CREATE INDEX IF NOT EXISTS idx_centros_sanitarios_geom ON centros_sanitarios USING GIST (geom);


-- =============================================================================
-- TODO 4 (Responsable P4): Tablas `convocatorias` y `convocatoria_municipio`
-- =============================================================================
-- 4.1 Tabla `convocatorias` (Catálogo BDNS):
--   - codigo_bdns VARCHAR(30) PRIMARY KEY
--   - titulo TEXT NOT NULL
--   - organo_convocante VARCHAR(200) NOT NULL
--   - presupuesto_total NUMERIC(14, 2) NOT NULL
--   - fecha_inicio DATE NOT NULL
--   - fecha_fin DATE NOT NULL
--   - categoria VARCHAR(80) NOT NULL
--   - poblacion_max_objetivo INTEGER NOT NULL DEFAULT 20000
--   - url_ficha TEXT
--   - activa BOOLEAN NOT NULL DEFAULT TRUE
--
-- 4.2 Tabla puente `convocatoria_municipio` (Matching de ayudas con municipios):
--   - id SERIAL PRIMARY KEY
--   - codigo_bdns VARCHAR(30) NOT NULL REFERENCES convocatorias(codigo_bdns) ON DELETE CASCADE
--   - codigo_ine VARCHAR(10) NOT NULL REFERENCES municipios(codigo_ine) ON DELETE CASCADE
--   - importe_estimado_hab NUMERIC(10, 2) NOT NULL DEFAULT 0.0
--   - prioridad_asignacion VARCHAR(30) NOT NULL DEFAULT 'ALTA'
--   - justificacion_cruce TEXT
--   - Restricción UNIQUE (codigo_bdns, codigo_ine)


-- =============================================================================
-- TODO 5 (Responsables P1 / P5): Tabla `metricas_infraestructura`
-- =============================================================================
-- Debe almacenar los indicadores de conectividad y vivienda de soporte para el motor WLC:
--   - codigo_ine VARCHAR(10) PRIMARY KEY REFERENCES municipios(codigo_ine) ON DELETE CASCADE
--   - cobertura_5g_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.0
--   - cobertura_fibra_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.0
--   - viviendas_vacias_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.0
--   - precio_m2_eur NUMERIC(8, 2) NOT NULL DEFAULT 0.0
--   - servicios_basicos_score NUMERIC(5, 2) NOT NULL DEFAULT 50.0
--   - updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
