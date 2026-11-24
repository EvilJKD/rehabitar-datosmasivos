# Módulo ETL P4 - Convocatorias de Subvenciones (BDNS / SNPSAP)

Este módulo extrae convocatorias de subvenciones desde la API REST pública de la BDNS (SNPSAP), normaliza sus plazos y requisitos de población, las almacena en PostgreSQL y las asigna a los municipios de la Comunidad de Madrid para servir a la Consulta 4.

## Qué hace el módulo

1. **Extracción desde la API REST de la BDNS (`etl/p4_bdns/etl_bdns.py`)**
   - Consulta las convocatorias publicadas para las regiones configuradas en `BDNS_REGIONES` (por defecto `26` para Comunidad de Madrid y `27` para la provincia de Madrid) dentro de la ventana de `BDNS_MESES_ATRAS` meses.
   - Aplica un prefiltro sobre los resúmenes antes de pedir los detalles: conserva ayudas `LOCAL` de municipios presentes en el sistema, `AUTONOMICA` de `COMUNIDAD DE MADRID` y `ESTADO`, descartando convocatorias dirigidas a ayuntamientos ajenos y filtrando por palabras clave de ámbito rural (`BDNS_PALABRAS_CLAVE`) hasta el límite `BDNS_MAX_DETALLES`.
   - Mantiene la última descarga en memoria RAM durante `BDNS_CACHE_HORAS` como caché y respaldo si falla la API.

2. **Normalización**
   - Convierte las fechas de inicio y fin de solicitud a formato ISO; si no vienen informadas en campos estructurados, intenta interpretar los textos libres (`textInicio` y `textFin`).
   - Calcula el indicador `abierta` comprobando el flag de la BDNS y que la fecha de fin de plazo no haya vencido.
   - Extrae el umbral máximo de habitantes (`poblacion_max_objetivo`) a partir de la descripción y de las bases reguladoras cuando se restringe la ayuda a municipios por debajo de cierto tamaño.

3. **Carga y asignación territorial**
   - Inserta o actualiza el catálogo en la tabla `convocatorias` (clave `codigo_bdns`).
   - Evalúa las reglas de asignación en `convocatoria_municipio` por orden de prioridad y marca `municipios.hidratado = TRUE`:
     - `organo_local`: la convocatoria la publica el propio ayuntamiento del municipio o una ayuda estatal o autonómica se dirige expresamente a ese ayuntamiento.
     - `umbral_poblacion`: la convocatoria fija un máximo de habitantes y el último padrón disponible del municipio en `demografia_anual` es estrictamente menor que ese umbral.
     - `region_completa`: convocatoria autonómica de la Comunidad de Madrid o estatal sin destinatario local concreto ni umbral de población.

4. **Servicio y Consulta 4 (`backend/services/p4_grants_service.py`)**
   - Consulta las convocatorias aplicables a un municipio o al catálogo completo (`get_convocatorias`), resume ayudas abiertas y presupuestos (`get_grants_summary_all`, `get_num_ayudas_abiertas`) y reutiliza `ingest_bdns_for_municipio` para hidratar municipios bajo demanda (`hydrate_grants_on_demand`).

## Dependencias con otros módulos

- **P1 (`municipios`)**: necesaria para conocer los códigos INE y nombres de municipios antes de asignar ayudas.
- **P2 (`demografia_anual`)**: necesaria para evaluar la regla `umbral_poblacion`; si no existe padrón para un municipio, esa regla no se aplica.

## Cómo ejecutarlo

Desde la raíz del proyecto (`re-habitar-poc`):

```bash
# Carga completa para todos los municipios registrados en PostgreSQL
python etl/p4_bdns/etl_bdns.py

# Asignación limitada a uno o varios códigos INE concretos
python etl/p4_bdns/etl_bdns.py 28070 28078

# Forzar descarga desde la API ignorando la caché reciente en memoria
python etl/p4_bdns/etl_bdns.py --force-refresh

# Prueba sin base de datos: descarga, filtra y muestra un resumen en consola
python etl/p4_bdns/etl_bdns.py --dry-run --nombres "La Hiruela,Madarcos"
```

### Variables de entorno principales

- Conexión PostgreSQL: `DATABASE_URL_SYNC` o bien `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
- API BDNS: `BDNS_API_URL`, `BDNS_REGIONES`, `BDNS_MESES_ATRAS`, `BDNS_PAGE_SIZE`, `BDNS_MAX_PAGINAS`, `BDNS_MAX_DETALLES`, `BDNS_PAUSA_SEG`, `BDNS_TIMEOUT`, `BDNS_CACHE_HORAS`, `BDNS_PALABRAS_CLAVE`.
