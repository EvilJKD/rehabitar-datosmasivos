# Módulo P2 - Demografía INE

## Qué hace

Este módulo cubre la ingesta y el cálculo de indicadores demográficos de los municipios de la Comunidad de Madrid:

1. **Extracción y carga (`etl/p2_ine/etl_ine.py`)**: descarga de la API REST JSON Tempus del INE (tabla `2881`, Padrón municipal) la serie anual de población total entre 2015 y 2025, y la inserta o actualiza en la tabla `demografia_anual` de PostgreSQL. Las columnas por edad (`poblacion_mayor_65`, `poblacion_menor_15` y `tasa_envejecimiento`) quedan a `NULL` mientras no exista una fuente desagregada por edad.
2. **Carga bajo demanda e indicadores (`backend/services/p2_demo_service.py`)**: si un municipio consultado aún no está en `demografia_anual`, dispara la descarga desde el INE y calcula para la Consulta 3:
   - Variación de población a 5 y 10 años (`variacion_5a_pct` y `variacion_10a_pct`).
   - Etiqueta de inercia demográfica (`COLAPSO`, `DECLIVE`, `ESTANCAMIENTO`, `RECUPERACION`, `REPUNTE_RECIENTE` o `SIN_DATOS`).
   - Preservación de masa crítica (`preserva_masa_critica`, con umbral en 100 habitantes).

## Cómo ejecutar el ETL

Para probar la descarga e imprimir las series por pantalla sin conectarse a la base de datos:

```bash
python etl/p2_ine/etl_ine.py --dry-run
python etl/p2_ine/etl_ine.py --dry-run 28070 28027
```

Para cargar los datos en `demografia_anual` (usa los municipios pasados por argumento, los ya registrados en `municipios` o los de `INITIAL_SEED_CODES` si la tabla está vacía):

```bash
python etl/p2_ine/etl_ine.py
python etl/p2_ine/etl_ine.py 28070 28027
```

## Variables de entorno

- `DATABASE_URL_SYNC` o `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: conexión a PostgreSQL (por defecto apunta a `localhost:5432`, base de datos `rehabitar_db`).
- `INE_TABLA_POBLACION`: tabla del INE a consultar (por defecto `2881`).
- `INE_API_TIMEOUT`: tiempo máximo de espera en segundos para la API del INE (por defecto `30`).
- `INITIAL_SEED_CODES`: códigos INE semilla separados por comas (por defecto `28078,28069,28027`).
