# Modelos ORM (`backend/models/`)

Define las clases ORM de **SQLAlchemy** que mapean las tablas creadas por `db/schema.sql`.

## Archivos principales

- `__init__.py`: Reexporta los seis modelos del dominio en `__all__`.
- `domain.py`: Declara el tipo espacial `PuntoWGS84` (`geometry(Point, 4326)`) y los modelos `Municipio` (`municipios`), `DemografiaAnual` (`demografia_anual`), `MetricaInfraestructura` (`metricas_infraestructura`), `CentroSanitario` (`centros_sanitarios`), `Convocatoria` (`convocatorias`) y `ConvocatoriaMunicipio` (`convocatoria_municipio`).
