-- =============================================================================
-- SOLO PARA TESTS DE P4 (no se usa en producción ni en docker-compose.yml)
-- Versión mínima de las tablas de P1 (`municipios`) y P2 (`demografia_anual`) para poder probar
-- `convocatoria_municipio` (que tiene FK a `municipios`) mientras sus ramas no estén fusionadas en main.
-- Si db/schema.sql ya crea las tablas reales, los tests usan esas y este fichero no se ejecuta.
-- =============================================================================
CREATE TABLE IF NOT EXISTS municipios (
    codigo_ine        VARCHAR(5)   PRIMARY KEY,
    nombre            VARCHAR(120) NOT NULL,
    hidratado         BOOLEAN      NOT NULL DEFAULT FALSE,
    fecha_hidratacion TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS demografia_anual (
    codigo_ine VARCHAR(5) NOT NULL REFERENCES municipios (codigo_ine) ON DELETE CASCADE,
    anio       SMALLINT   NOT NULL,
    poblacion  INTEGER    NOT NULL CHECK (poblacion >= 0),
    PRIMARY KEY (codigo_ine, anio)
);
