# 📋 TODO List — Orquestador de Carga Inicial Ligera (`etl/`)

> **Estrategia de Ingesta Híbrida (Fase 1 - Carga Inicial en `etl_runner`):**
> En lugar de procesar todos los municipios en el arranque, `etl/run_all.py` hace una **carga semilla rápida (< 2 segundos)**:
> 1. Registra todos los puntos geográficos de los municipios en `municipios` con `hidratado = FALSE` (`P1`).
> 2. Registra el catálogo de centros sanitarios (`P3`) y el catálogo general de convocatorias (`P4`).
> 3. Pre-hidrata únicamente 2 municipios semilla (`INITIAL_SEED_CODES`, por defecto `28070` La Hiruela y `28027` Buitrago del Lozoya).
> 4. El resto de municipios se ingesta **bajo demanda** cuando el usuario los selecciona en el Frontend.

## Paso a Paso para Completar `etl/run_all.py`

- [ ] **Paso 1: Implementar `get_initial_seed_codes()`**
  - Leer la variable de entorno `INITIAL_SEED_CODES` (por defecto `"28070,28027"`), separar por comas y retornar la lista `["28070", "28027"]`.

- [ ] **Paso 2: Implementar `wait_for_db(max_retries=20, wait_seconds=2.0)`**
  - Intentar conectar a PostgreSQL con `psycopg2.connect(...)` hasta que responda.

- [ ] **Paso 3: Implementar `main()`**
  - Obtener `seed_codes = get_initial_seed_codes()`.
  - Ejecutar en orden:
    1. `run_etl_p1(seed_codes=seed_codes)` -> Inserta todos los municipios en `municipios` con `hidratado = FALSE` y las métricas de infraestructura de los municipios semilla.
    2. `run_etl_p2(target_codes=seed_codes)` -> Descarga e inserta en `demografia_anual` solo las series de `seed_codes`.
    3. `run_etl_p3()` -> Inserta todos los centros sanitarios en `centros_sanitarios`.
    4. `run_etl_p4(target_codes=seed_codes)` -> Inserta el catálogo de `convocatorias`, cruza ayudas solo para `seed_codes` y actualiza `hidratado = TRUE` en esos municipios semilla.
