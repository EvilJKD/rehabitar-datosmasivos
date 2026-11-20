# Módulo P1: Catálogo municipal e infraestructura

Este módulo carga el catálogo base de municipios de la Comunidad de Madrid y sus métricas de conectividad y acceso físico en PostgreSQL/PostGIS.

## Qué hace

1. **Catálogo municipal (`municipios`)**: descarga la publicación municipal del IGN (obra derivada del NGMEP, CC-BY 4.0) y registra los municipios de Madrid (códigos INE `28xxx`) con su nombre, provincia, comarca (`Sierra Norte` o `Sin clasificar`) y coordenadas en `Point(4326)`.
2. **Métricas de infraestructura (`metricas_infraestructura`)**: para cada municipio indicado por semilla en el ETL o consultado bajo demanda desde el backend, calcula y guarda:
   - Cobertura de fibra (`FTTH (junio 2025)`) y telefonía móvil (`4G (junio 2025)`), de 0 a 100, a partir del informe de SETELECO.
   - Distancia geodésica en kilómetros a la vía pavimentada (`roadlink`) y al curso de agua natural permanente (`watercourse`) más cercanos según la API de IDEE.

## Cómo ejecutarlo

Desde la carpeta `etl/` (con PostgreSQL/PostGIS disponible y el esquema aplicado):

```bash
python p1_ngbe/etl_ngbe.py
```

Este comando carga o actualiza los municipios de Madrid en `municipios` sin alterar su estado de hidratación.

Para cargar también las métricas de infraestructura de un municipio semilla (por ejemplo, `28078` para Madarcos), pasa `--seed`:

```bash
python p1_ngbe/etl_ngbe.py --seed 28078
```

Puedes repetir `--seed` varias veces si quieres cargar métricas para varios municipios en la misma ejecución.

Si trabajas con Docker Compose desde la raíz del proyecto, puedes lanzarlo mediante el servicio `etl_runner`:

```powershell
docker compose run --rm etl_runner python p1_ngbe/etl_ngbe.py
docker compose run --rm etl_runner python p1_ngbe/etl_ngbe.py --seed 28078
```

## Variables de entorno

- `DATABASE_URL_SYNC` o `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_DB` para la conexión síncrona a PostgreSQL.
- `P1_HTTP_TIMEOUT` para configurar el tiempo máximo de espera en segundos de las peticiones HTTP (por defecto `30`).
