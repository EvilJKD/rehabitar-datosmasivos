"""
Modelos ORM de SQLAlchemy alineados con el esquema normalizado y Citus-Ready (`db/schema.sql`).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import Boolean, Computed, Date, DateTime, Float, ForeignKey, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class PuntoWGS84(sa.types.UserDefinedType):
    """Tipo SQLAlchemy personalizado para columnas espaciales geometry(Point, 4326) de PostGIS."""

    cache_ok = True

    def get_col_spec(self, **kwargs):
        """Devuelve la especificación SQL del tipo espacial en PostGIS."""
        return "geometry(Point, 4326)"


class Municipio(Base):
    """Catálogo maestro de municipios del IGN."""

    __tablename__ = "municipios"

    codigo_ine = sa.Column(sa.String(5), primary_key=True)
    nombre = sa.Column(sa.String(120), nullable=False)
    provincia = sa.Column(sa.String(80), nullable=False, server_default="Madrid")
    comarca = sa.Column(sa.String(100), nullable=False, server_default="Sin clasificar")
    latitud = sa.Column(sa.Double, nullable=False)
    longitud = sa.Column(sa.Double, nullable=False)
    geom = sa.Column(PuntoWGS84(), nullable=False)
    hidratado = sa.Column(sa.Boolean, nullable=False, server_default=sa.false())
    fecha_hidratacion = sa.Column(sa.DateTime(timezone=True))
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


class DemografiaAnual(Base):
    """Serie demográfica anual por municipio (`demografia_anual`)."""

    __tablename__ = "demografia_anual"

    codigo_ine: Mapped[str] = mapped_column(
        String(5),
        ForeignKey("municipios.codigo_ine", ondelete="CASCADE"),
        primary_key=True,
    )
    anio: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    poblacion: Mapped[int] = mapped_column(Integer, nullable=False)
    poblacion_mayor_65: Mapped[Optional[int]] = mapped_column(Integer)
    poblacion_menor_15: Mapped[Optional[int]] = mapped_column(Integer)
    # Numeric se lee en Python como Decimal (decimal exacto), no como float
    tasa_envejecimiento: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))


class MetricaInfraestructura(Base):
    """Métricas físicas y de conectividad persistidas por P1."""

    __tablename__ = "metricas_infraestructura"

    codigo_ine = sa.Column(
        sa.String(5), sa.ForeignKey("municipios.codigo_ine", ondelete="CASCADE"), primary_key=True
    )
    distancia_carretera_km = sa.Column(sa.Numeric(6, 2), nullable=False)
    distancia_recurso_hidrico_km = sa.Column(sa.Numeric(6, 2), nullable=False)
    cobertura_fibra_pct = sa.Column(sa.Numeric(5, 2), nullable=False)
    cobertura_movil_pct = sa.Column(sa.Numeric(5, 2), nullable=False)
    fecha_actualizacion = sa.Column(sa.Date, nullable=False, server_default=sa.func.current_date())


class CentroSanitario(Base):
    """Directorio de centros sanitarios y puntos de urgencias de la Comunidad de Madrid (`centros_sanitarios`)."""

    __tablename__ = "centros_sanitarios"

    id_centro: Mapped[str] = mapped_column(String(40), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(100), nullable=False)
    tiene_urgencias: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    municipio_nombre: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    direccion: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    horario: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    latitud: Mapped[float] = mapped_column(Float, nullable=False)
    longitud: Mapped[float] = mapped_column(Float, nullable=False)


class Convocatoria(Base):
    """
    Catálogo de convocatorias de subvenciones de la BDNS (`convocatorias`).
    `organo_convocante` es una columna generada en PostgreSQL y `poblacion_max_objetivo` admite NULL si no hay umbral.
    """

    __tablename__ = "convocatorias"

    codigo_bdns: Mapped[str] = mapped_column(String(30), primary_key=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    organo_nivel1: Mapped[str] = mapped_column(String(150), nullable=False)
    organo_nivel2: Mapped[Optional[str]] = mapped_column(String(150))
    organo_nivel3: Mapped[Optional[str]] = mapped_column(String(150))
    organo_convocante: Mapped[Optional[str]] = mapped_column(
        Text, Computed("COALESCE(organo_nivel3, organo_nivel2, organo_nivel1)", persisted=True)
    )
    fecha_recepcion: Mapped[date] = mapped_column(Date, nullable=False)
    inicio_solicitud: Mapped[Optional[date]] = mapped_column(Date)
    fin_solicitud: Mapped[Optional[date]] = mapped_column(Date)
    abierta: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    presupuesto_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    tipo_beneficiario: Mapped[Optional[str]] = mapped_column(String(150))
    finalidad: Mapped[Optional[str]] = mapped_column(String(150))
    poblacion_max_objetivo: Mapped[Optional[int]] = mapped_column(Integer)
    url_bases: Mapped[Optional[str]] = mapped_column(Text)
    fecha_extraccion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConvocatoriaMunicipio(Base):
    """
    Relación de convocatorias asignadas a cada municipio (`convocatoria_municipio`).
    Usa clave primaria compuesta (`codigo_ine`, `codigo_bdns`) y registra la `regla_asignacion` aplicada.
    """

    __tablename__ = "convocatoria_municipio"

    codigo_ine: Mapped[str] = mapped_column(
        String(5),
        ForeignKey("municipios.codigo_ine", ondelete="CASCADE"),
        primary_key=True,
    )
    codigo_bdns: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("convocatorias.codigo_bdns", ondelete="CASCADE"),
        primary_key=True,
    )
    regla_asignacion: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha_asignacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
