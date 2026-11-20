# Esquemas Pydantic (`backend/schemas/`)

Define los esquemas Pydantic empleados para validar y serializar las respuestas JSON de la API REST definida en `backend/main.py`.

## Archivos principales

- `__init__.py`: Reexporta los esquemas públicos del paquete.
- `domain.py`: Contiene `WLCBreakdownSchema`, `CentroSanitarioSchema`, `RutaSanitariaSchema`, `ConvocatoriaMunicipioItemSchema`, `MunicipioListItemSchema`, `MunicipioDetailSchema`, `DemografiaPuntoAnualSchema` y `DemografiaSerieResponseSchema`.
- `p1_geo.py`: Define `InfraestructuraSchema` con las métricas físicas y de conectividad municipal.
- `_compat.py`: Proporciona una capa ligera de compatibilidad para `BaseModel`, `ConfigDict` y `Field` cuando las pruebas unitarias se ejecutan sin `pydantic` instalado.
