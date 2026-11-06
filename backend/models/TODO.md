# 📋 TODO List — Modelos ORM SQLAlchemy (`backend/models/`) · Citus-Ready

> **Archivo a completar:** `domain.py`

## Paso a Paso para Completar `backend/models/domain.py`

- [ ] **Paso 1 (P1): Clase `Municipio(Base)` (`__tablename__ = "municipios"`)**
  - `codigo_ine`: `String(5)`, `primary_key=True`
  - `nombre`: `String(120)`, `provincia`: `String(80)`, `comarca`: `String(100)`
  - `latitud`: `Float`, `longitud`: `Float`
  - `hidratado`: `Boolean`, `fecha_hidratacion`: `DateTime(timezone=True)`

- [ ] **Paso 2 (P2): Clase `DemografiaAnual(Base)` (`__tablename__ = "demografia_anual"`)**
  - **Clave primaria compuesta (Citus):** `codigo_ine` (`primary_key=True`) y `anio` (`primary_key=True`).
  - `poblacion`: `Integer` (nombre oficial de la Sección 7.1.2).
  - `poblacion_mayor_65`, `poblacion_menor_15`, `tasa_envejecimiento`.

- [ ] **Paso 3 (P1): Clase `MetricaInfraestructura(Base)` (`__tablename__ = "metricas_infraestructura"`)**
  - `codigo_ine`: `String(5)`, `primary_key=True`
  - `distancia_carretera_km`: `Numeric(6, 2)`
  - `distancia_recurso_hidrico_km`: `Numeric(6, 2)`
  - `cobertura_fibra_pct`: `Numeric(5, 2)`
  - `cobertura_movil_pct`: `Numeric(5, 2)`
  - `fecha_actualizacion`: `Date`

- [ ] **Paso 4 (P3): Clase `CentroSanitario(Base)` (`__tablename__ = "centros_sanitarios"`)**
  - `id_centro` (PK), `nombre`, `tipo`, `tiene_urgencias`, `municipio_nombre`, `direccion`, `horario`, `telefono`, `latitud`, `longitud`.

- [ ] **Paso 5 (P4): Clases `Convocatoria(Base)` y `ConvocatoriaMunicipio(Base)`**
  - En `Convocatoria`: `codigo_bdns` (PK), `descripcion`, `organo_nivel1`, `organo_nivel2`, `organo_nivel3`, `fecha_recepcion`, `inicio_solicitud`, `fin_solicitud`, `abierta`, `presupuesto_total`, `tipo_beneficiario`, `poblacion_max_objetivo`, `url_bases`.
  - En `ConvocatoriaMunicipio`: **Clave primaria compuesta (Citus)** `(codigo_ine, codigo_bdns)` y columna `regla_asignacion` (`'organo_local' | 'umbral_poblacion' | 'region_completa'`).
