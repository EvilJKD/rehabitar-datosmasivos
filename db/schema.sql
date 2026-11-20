-- =============================================================================
-- RE-HABITAR PoC: Esqueleto del Esquema DDL (PostgreSQL + PostGIS + Citus-Ready)
-- Alineado con las Secciones 4, 5.2, 6.3, 6.5, 7.1, 7.2, 7.3 y 9 de la Propuesta
-- =============================================================================

-- TODO 0: Habilitar la extensión espacial PostGIS
-- CREATE EXTENSION IF NOT EXISTS postgis;
-- (En despliegue distribuido Citus: CREATE EXTENSION IF NOT EXISTS citus;)


-- =============================================================================
-- TODO 1 (Responsable P1): Tabla `municipios` (Entidad Maestra - Sección 7.1.1)
-- Rol en Citus: Reference Table (o Distributed Table líder por `codigo_ine`)
-- =============================================================================
-- Debe almacenar las entidades municipales de la Comunidad de Madrid:
--   - codigo_ine VARCHAR(5) PRIMARY KEY                 -- Ej. '28078' (Madarcos)
--   - nombre VARCHAR(120) NOT NULL                      -- Ej. 'Madarcos'
--   - provincia VARCHAR(80) NOT NULL DEFAULT 'Madrid'
--   - comarca VARCHAR(100) NOT NULL DEFAULT 'Sierra Norte'
--   - latitud DOUBLE PRECISION NOT NULL CHECK (latitud BETWEEN -90 AND 90)
--   - longitud DOUBLE PRECISION NOT NULL CHECK (longitud BETWEEN -180 AND 180)
--   - geom geometry(Point, 4326) NOT NULL               -- Punto PostGIS WGS84
--   - hidratado BOOLEAN NOT NULL DEFAULT FALSE          -- Control de Ingesta Híbrida Materializada
--   - fecha_hidratacion TIMESTAMP WITH TIME ZONE        -- Fecha de carga bajo demanda en BD
--   - created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
--
-- Índices a crear:
--   - Índice espacial GiST: CREATE INDEX IF NOT EXISTS idx_municipios_geom ON municipios USING GIST (geom);
--   - Índice B-Tree de estado: CREATE INDEX IF NOT EXISTS idx_municipios_provincia_hidratado ON municipios (provincia, hidratado);


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
-- TODO 3 (Responsable P1): Tabla `metricas_infraestructura` (Sección 7.1.3)
-- Rol en Citus: Distributed Table (shard key: `codigo_ine`, co-localizada con `demografia_anual`)
-- =============================================================================
-- REGLA ESTRICTA DE LA PROPUESTA (Sección 6.3 y 7.3):
--   "El tiempo de trayecto hacia el punto sanitario NO se almacena en ninguna tabla
--    para evitar obsolescencia." Por tanto, esta tabla SOLO guarda indicadores físicos
--   y digitales estáticos consolidados:
--   - codigo_ine VARCHAR(5) PRIMARY KEY REFERENCES municipios(codigo_ine) ON DELETE CASCADE
--   - distancia_carretera_km NUMERIC(6, 2) NOT NULL DEFAULT 0.00       -- Indicador 1 WLC (Acceso por carretera asfaltada)
--   - distancia_recurso_hidrico_km NUMERIC(6, 2) NOT NULL DEFAULT 0.00 -- Indicador 4 WLC (Acceso a recursos hídricos)
--   - cobertura_fibra_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.00          -- Indicador 3 WLC y Filtro de Consulta 1
--   - cobertura_movil_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.00          -- Indicador 3 WLC (Conectividad móvil 4G/5G)
--   - fecha_actualizacion DATE NOT NULL DEFAULT CURRENT_DATE
--
-- Índice parcial para acelerar Consulta 1 (municipios con cobertura de fibra):
--   - CREATE INDEX IF NOT EXISTS idx_infra_cobertura_fibra ON metricas_infraestructura (cobertura_fibra_pct) WHERE cobertura_fibra_pct > 0;


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
-- 5. AYUDAS Y SUBVENCIONES: `convocatorias` y `convocatoria_municipio` (Sección 7.1.5 y 7.1.6 - Completado por P4)
-- Fuente: API de la Base de Datos Nacional de Subvenciones (BDNS / SNPSAP), cargada por etl/p4_bdns/etl_bdns.py.
-- =============================================================================

-- 5.1 `convocatorias` (Rol en Citus: Reference Table, replicada en todos los workers).
-- Es un catálogo pequeño (cientos de filas por comunidad autónoma) que se cruza con cualquier municipio,
-- así que replicarla evita mover datos entre nodos en los JOIN con `convocatoria_municipio`.
--
-- Cambios respecto al esquema preliminar de la propuesta:
--   * `poblacion_max_objetivo` NO lleva DEFAULT 20000: NULL significa "la convocatoria no tiene umbral de población".
--     Con un 20000 por defecto, todas las ayudas parecerían limitadas a municipios pequeños y la regla
--     `umbral_poblacion` se aplicaría a convocatorias que no la mencionan.
--   * `finalidad` (nueva): `descripcionFinalidad` de la BDNS (ej. 'Infraestructuras', 'Vivienda'). Permite el filtro
--     `categoria` de `GET /api/convocatorias`.
--   * `abierta` se guarda como "abierta en el momento de la extracción" (campo `abierto` de la BDNS y fecha de fin
--     no vencida). Las consultas vuelven a comprobar `fin_solicitud >= CURRENT_DATE` para no depender de la última carga.
CREATE TABLE IF NOT EXISTS convocatorias (
    codigo_bdns            VARCHAR(30)    PRIMARY KEY,                 -- Ej. '921084'
    descripcion            TEXT           NOT NULL,                    -- Título/objeto de la ayuda
    organo_nivel1          VARCHAR(150)   NOT NULL,                    -- 'ESTADO' | 'AUTONOMICA' | 'LOCAL' | 'OTROS'
    organo_nivel2          VARCHAR(150),                               -- Ej. 'COMUNIDAD DE MADRID' o el municipio ('LA HIRUELA')
    organo_nivel3          VARCHAR(150),                               -- Ej. 'CONSEJERÍA DE PRESIDENCIA, JUSTICIA Y ADMINISTRACIÓN LOCAL'
    organo_convocante      TEXT GENERATED ALWAYS AS (COALESCE(organo_nivel3, organo_nivel2, organo_nivel1)) STORED,
    fecha_recepcion        DATE           NOT NULL DEFAULT CURRENT_DATE,
    inicio_solicitud       DATE,
    fin_solicitud          DATE,
    abierta                BOOLEAN        NOT NULL DEFAULT TRUE,       -- Filtro de la Consulta 4
    presupuesto_total      NUMERIC(14, 2) NOT NULL DEFAULT 0.00 CHECK (presupuesto_total >= 0),
    tipo_beneficiario      VARCHAR(150),
    finalidad              VARCHAR(150),                               -- Categoría (descripcionFinalidad BDNS)
    poblacion_max_objetivo INTEGER        CHECK (poblacion_max_objetivo > 0),  -- NULL = sin umbral
    url_bases              TEXT,
    fecha_extraccion       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Consulta 4: "convocatorias abiertas ordenadas por fin de plazo".
CREATE INDEX IF NOT EXISTS idx_convocatorias_abiertas_fin
    ON convocatorias (fin_solicitud)
    WHERE abierta = TRUE;

-- Regla `organo_local`: búsqueda de las convocatorias de entidades locales por nombre del órgano.
CREATE INDEX IF NOT EXISTS idx_convocatorias_organo
    ON convocatorias (organo_nivel1, organo_nivel2);


-- 5.2 `convocatoria_municipio` (resultado de la asignación; Rol en Citus: Distributed Table por `codigo_ine`).
-- Clave primaria compuesta con `codigo_ine` primero: así Citus la co-localiza con `demografia_anual` y
-- `metricas_infraestructura`, y los cruces por municipio se resuelven dentro de cada worker.
CREATE TABLE IF NOT EXISTS convocatoria_municipio (
    codigo_ine        VARCHAR(5)  NOT NULL REFERENCES municipios (codigo_ine) ON DELETE CASCADE,
    codigo_bdns       VARCHAR(30) NOT NULL REFERENCES convocatorias (codigo_bdns) ON DELETE CASCADE,
    regla_asignacion  VARCHAR(30) NOT NULL
                      CHECK (regla_asignacion IN ('organo_local', 'umbral_poblacion', 'region_completa')),
    fecha_asignacion  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_convocatoria_municipio PRIMARY KEY (codigo_ine, codigo_bdns)
);

-- La PK empieza por codigo_ine; este índice sirve para el camino inverso
-- ("¿a qué municipios se ha asignado la convocatoria X?") y para el ON DELETE CASCADE desde `convocatorias`.
CREATE INDEX IF NOT EXISTS idx_convocatoria_municipio_bdns
    ON convocatoria_municipio (codigo_bdns);
