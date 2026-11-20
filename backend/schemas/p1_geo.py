"""Esquema de respuesta de las métricas de P1."""

from datetime import date

from pydantic import BaseModel, Field


class InfraestructuraSchema(BaseModel):
    distancia_carretera_km: float = Field(ge=0)
    distancia_recurso_hidrico_km: float = Field(ge=0)
    cobertura_fibra_pct: float = Field(ge=0, le=100)
    cobertura_movil_pct: float = Field(ge=0, le=100)
    fecha_actualizacion: date
