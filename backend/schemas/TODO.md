# 📋 TODO List — Schemas Pydantic (`backend/schemas/`) · Alineado con Secciones 4, 6.5 y 7.1

> **Archivo a completar:** `domain.py`

## Paso a Paso para Completar `backend/schemas/domain.py`

- [ ] **Paso 1 (P5): `WLCBreakdownSchema` (Sección 4 y 6.4)**
  - Debe incluir `indice_wlc`, `semaforo` y los **5 subíndices de habitabilidad** exigidos por la Sección 4 y 6.4:
    1. `score_acceso_carretera: float`
    2. `score_proximidad_sanitaria: float`
    3. `score_conectividad_digital: float`
    4. `score_acceso_hidrico: float`
    5. `score_inercia_demografica: float`

- [ ] **Paso 2 (P1): `InfraestructuraSchema` (Sección 7.1.3)**
  - `distancia_carretera_km: float`, `distancia_recurso_hidrico_km: float`, `cobertura_fibra_pct: float`, `cobertura_movil_pct: float`, `fecha_actualizacion: date`.

- [ ] **Paso 3 (P3/P5): `RutaSanitariaSchema` (Consulta 2 y Sección 7.3)**
  - `id_centro`, `nombre`, `tipo`, `tiene_urgencias`, `latitud`, `longitud`, `distancia_euclidea_km`, `distancia_carretera_km` (CartoCiudad en tiempo real), `tiempo_estimado_min` (CartoCiudad en tiempo real), `fuente_ruta` y `geometria_ruta`.

- [ ] **Paso 4 (P4): `ConvocatoriaMunicipioItemSchema` (Consulta 4 y Sección 7.1.5 / 7.1.6)**
  - `codigo_bdns`, `descripcion`, `organo_nivel1`, `organo_nivel2`, `organo_nivel3`, `organo_convocante`, `fecha_recepcion`, `inicio_solicitud`, `fin_solicitud`, `abierta`, `presupuesto_total`, `tipo_beneficiario`, `url_bases`, `regla_asignacion` (`'organo_local' | 'umbral_poblacion' | 'region_completa'`).

- [ ] **Paso 5: `MunicipioListItemSchema`, `MunicipioDetailSchema`, `DemografiaPuntoAnualSchema` y `DemografiaSerieResponseSchema`**
