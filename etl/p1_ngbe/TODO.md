# Módulo P1 · Catálogo municipal e infraestructura

Desde la raíz del repositorio, con Docker Desktop en marcha:

```powershell
docker compose up -d --build --wait db
docker compose run --build --rm etl_runner python p1_ngbe/etl_ngbe.py
```

La carga registra los puntos de los municipios de la Comunidad de Madrid. Se puede
repetir sin duplicar municipios ni cambiar su estado de hidratación.

Para cargar también las métricas de un municipio, añade `--seed` con su código INE.
Puedes repetir el argumento para varios municipios.

```powershell
docker compose run --rm etl_runner python p1_ngbe/etl_ngbe.py --seed 28078 --seed 28069
```

`28078` corresponde a Madarcos y `28069` a La Hiruela.

Si PostgreSQL ya se había inicializado antes de incorporar P1, aplica el esquema
sobre el volumen existente antes de ejecutar el ETL. Este ejemplo usa el usuario
y la base de datos por defecto del proyecto.

```powershell
Get-Content -Raw -Encoding UTF8 db/schema.sql | docker compose exec -T db psql -v ON_ERROR_STOP=1 -U rehabitar -d rehabitar_db
```

## Fuentes y métricas

- **Catálogo municipal.** Obra derivada del NGMEP, CC BY 4.0 Instituto Geográfico
  Nacional. Se usa la [publicación municipal del Atlas Nacional de España](https://www.ign.es/resources/ane/Informacion_Geografica_Destacada/IGN_INFOGEO_MUNICIPIOS.html).
  La columna «Ver en mapa» proporciona las coordenadas de referencia que se guardan
  como `Point(4326)`. La etiqueta Sierra Norte indica pertenencia a la
  [mancomunidad publicada por la Comunidad de Madrid](https://www.comunidad.madrid/centros/mancomunidad-interes-general-servicios-sierra-norte).
- **Cobertura.** FTTH y 4G municipales en junio de 2025, expresadas de 0 a 100.
  Se usa la hoja municipal por hogares del [informe de cobertura de SETELECO](https://digital.gob.es/telecomunicaciones-infraestructuras-digitales/areas-interes/banda-ancha/informacion-cobertura/informes-cobertura/informe-cobertura-2025).
- **Distancias.** Distancias geodésicas desde el punto municipal a la vía
  pavimentada y al curso de agua natural permanente más próximos de las capas
  consultadas. Se usan las colecciones
  [Road Link](https://api-features.idee.es/collections/roadlink) y
  [Watercourse](https://api-features.idee.es/collections/watercourse) del IGN.

`P1_IGN_FILE` y `P1_COBERTURA_FILE` permiten usar copias locales de los Excel
oficiales. `P1_HTTP_TIMEOUT` configura el tiempo máximo de espera en segundos.

El servicio de P1 consulta las tablas con la sesión asíncrona proporcionada por
FastAPI. La primera consulta de infraestructura pide las métricas al ETL y las
persiste. Las consultas siguientes reutilizan los valores guardados. El
orquestador general es quien cambia el estado de hidratación del municipio.
