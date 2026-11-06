# 📋 TODO List — Capa de Base de Datos (`db/`) · Modelo Normalizado y Escalable (Citus + PostGIS)

> **Dictamen de Arquitectura de Base de Datos (Alineado con Secciones 5.2, 6.3, 6.5, 7.1, 7.2, 7.3 y 9 de la Propuesta):**
> 1. **Cumplimiento estricto de Integración Virtual (Sección 6.3 y 7.3):** Los tiempos de conducción y polilíneas de **CartoCiudad NO se almacenan en ninguna tabla** para evitar obsolescencia; se calculan y fusionan en memoria en FastAPI.
> 2. **Compatibilidad nativa con Sharding en Citus (Sección 5.2 y 7.1.6):** Se eliminan las claves subrogadas `id SERIAL` en las tablas distribuidas (`demografia_anual` y `convocatoria_municipio`) y se definen claves primarias compuestas encabezadas por la clave de particionamiento `codigo_ine`: `PRIMARY KEY (codigo_ine, anio)` y `PRIMARY KEY (codigo_ine, codigo_bdns)`. Así los `JOIN` por municipio se ejecutan localmente en cada nodo worker (*co-located joins*).
> 3. **Ingesta Híbrida Materializada:** La tabla `municipios` incorpora `hidratado BOOLEAN DEFAULT FALSE` y `fecha_hidratacion` para permitir una carga inicial rápida de la entidad maestra y poblar progresivamente `demografia_anual`, `metricas_infraestructura` y `convocatoria_municipio` conforme el usuario selecciona pueblos en el Frontend.

---

## Paso a Paso para Completar `db/schema.sql`

- [ ] **Paso 1: Habilitar la extensión espacial PostGIS**
  - Escribir `CREATE EXTENSION IF NOT EXISTS postgis;`.

- [ ] **Paso 2 (P1): Crear la tabla maestra `municipios` (Sección 7.1.1 - *Reference Table*)**
  - Columnas:
    - `codigo_ine VARCHAR(5) PRIMARY KEY` (ej. `'28078'`)
    - `nombre VARCHAR(120) NOT NULL` (ej. `'Madarcos'`)
    - `provincia VARCHAR(80) NOT NULL DEFAULT 'Madrid'`
    - `comarca VARCHAR(100) NOT NULL DEFAULT 'Sierra Norte'`
    - `latitud DOUBLE PRECISION NOT NULL CHECK (latitud BETWEEN -90 AND 90)`
    - `longitud DOUBLE PRECISION NOT NULL CHECK (longitud BETWEEN -180 AND 180)`
    - `geom geometry(Point, 4326) NOT NULL`
    - `hidratado BOOLEAN NOT NULL DEFAULT FALSE`
    - `fecha_hidratacion TIMESTAMP WITH TIME ZONE`
    - `created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - Crear índice espacial GiST: `CREATE INDEX IF NOT EXISTS idx_municipios_geom ON municipios USING GIST (geom);`.

- [ ] **Paso 3 (P2): Crear la tabla `demografia_anual` (Sección 7.1.2 - *Distributed Table por `codigo_ine`*)**
  - Columnas:
    - `codigo_ine VARCHAR(5) NOT NULL REFERENCES municipios(codigo_ine) ON DELETE CASCADE`
    - `anio SMALLINT NOT NULL CHECK (anio BETWEEN 1900 AND 2100)`
    - `poblacion INTEGER NOT NULL CHECK (poblacion >= 0)`
    - `poblacion_mayor_65 INTEGER DEFAULT 0`
    - `poblacion_menor_15 INTEGER DEFAULT 0`
    - `tasa_envejecimiento NUMERIC(5, 2) DEFAULT 0.00`
  - Clave primaria compuesta Citus-ready: `CONSTRAINT pk_demografia_anual PRIMARY KEY (codigo_ine, anio)`.
  - Crear índice `CREATE INDEX IF NOT EXISTS idx_demografia_anio_codigo ON demografia_anual (anio, codigo_ine);`.

- [ ] **Paso 4 (P1): Crear la tabla `metricas_infraestructura` (Sección 7.1.3 - *Distributed Table por `codigo_ine`*)**
  - Columnas exactas del documento (sin almacenar rutas de CartoCiudad):
    - `codigo_ine VARCHAR(5) PRIMARY KEY REFERENCES municipios(codigo_ine) ON DELETE CASCADE`
    - `distancia_carretera_km NUMERIC(6, 2) NOT NULL DEFAULT 0.00 CHECK (distancia_carretera_km >= 0)`
    - `distancia_recurso_hidrico_km NUMERIC(6, 2) NOT NULL DEFAULT 0.00 CHECK (distancia_recurso_hidrico_km >= 0)`
    - `cobertura_fibra_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.00 CHECK (cobertura_fibra_pct BETWEEN 0 AND 100)`
    - `cobertura_movil_pct NUMERIC(5, 2) NOT NULL DEFAULT 0.00 CHECK (cobertura_movil_pct BETWEEN 0 AND 100)`
    - `fecha_actualizacion DATE NOT NULL DEFAULT CURRENT_DATE`
  - Crear índice parcial para la **Consulta 1**:
    `CREATE INDEX IF NOT EXISTS idx_infra_cobertura_fibra ON metricas_infraestructura (cobertura_fibra_pct) WHERE cobertura_fibra_pct > 0;`.

- [ ] **Paso 5 (P3): Crear la tabla `centros_sanitarios` (Sección 7.1.4 - *Reference Table*)**
  - Columnas:
    - `id_centro VARCHAR(40) PRIMARY KEY` (ej. `'CS-28027'`)
    - `nombre VARCHAR(200) NOT NULL`
    - `tipo VARCHAR(100) NOT NULL` (ej. `'Centro de Salud / Urgencias'`, `'Consultorio Local'`)
    - `tiene_urgencias BOOLEAN NOT NULL DEFAULT FALSE`
    - `municipio_nombre VARCHAR(120)`
    - `direccion VARCHAR(250)`
    - `horario VARCHAR(120)`
    - `telefono VARCHAR(30)`
    - `latitud DOUBLE PRECISION NOT NULL`
    - `longitud DOUBLE PRECISION NOT NULL`
    - `geom geometry(Point, 4326) NOT NULL`
  - Crear índices espaciales GiST para la **Consulta 2 (KNN `<->`)**:
    - `CREATE INDEX IF NOT EXISTS idx_centros_sanitarios_geom ON centros_sanitarios USING GIST (geom);`
    - `CREATE INDEX IF NOT EXISTS idx_centros_urgencias_geom ON centros_sanitarios USING GIST (geom) WHERE tiene_urgencias = TRUE;`

- [ ] **Paso 6 (P4): Crear las tablas `convocatorias` y `convocatoria_municipio` (Sección 7.1.5 y 7.1.6)**
  - Tabla `convocatorias` (*Reference Table*):
    - `codigo_bdns VARCHAR(30) PRIMARY KEY` (ej. `'921084'`)
    - `descripcion TEXT NOT NULL`
    - `organo_nivel1 VARCHAR(150) NOT NULL`
    - `organo_nivel2 VARCHAR(150)`
    - `organo_nivel3 VARCHAR(150)`
    - `organo_convocante TEXT GENERATED ALWAYS AS (COALESCE(organo_nivel3, organo_nivel2, organo_nivel1)) STORED`
    - `fecha_recepcion DATE NOT NULL DEFAULT CURRENT_DATE`
    - `inicio_solicitud DATE`
    - `fin_solicitud DATE`
    - `abierta BOOLEAN NOT NULL DEFAULT TRUE`
    - `presupuesto_total NUMERIC(14, 2) NOT NULL DEFAULT 0.00`
    - `tipo_beneficiario VARCHAR(150)`
    - `poblacion_max_objetivo INTEGER DEFAULT 20000`
    - `url_bases TEXT`
  - Tabla `convocatoria_municipio` (*Distributed Table co-localizada por `codigo_ine`*):
    - `codigo_ine VARCHAR(5) NOT NULL REFERENCES municipios(codigo_ine) ON DELETE CASCADE`
    - `codigo_bdns VARCHAR(30) NOT NULL REFERENCES convocatorias(codigo_bdns) ON DELETE CASCADE`
    - `regla_asignacion VARCHAR(30) NOT NULL CHECK (regla_asignacion IN ('organo_local', 'umbral_poblacion', 'region_completa'))`
    - `fecha_asignacion TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP`
    - `CONSTRAINT pk_convocatoria_municipio PRIMARY KEY (codigo_ine, codigo_bdns)`
