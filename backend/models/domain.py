"""
Modelos ORM de SQLAlchemy alineados con el esquema normalizado y Citus-Ready (`db/schema.sql`).
"""

from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import Boolean, Float, ForeignKey, Integer, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class PuntoWGS84(sa.types.UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kwargs):
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
    """
    Tabla distribuida `demografia_anual` (Sección 7.1.2 - P2).
    """
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
    """
    Tabla de referencia (Reference Table) `centros_sanitarios` (Sección 7.1.4 - P3).
    Almacena el directorio de Centros de Salud, Consultorios Locales y Puntos de Urgencias
    extraídos del portal de Datos Abiertos de la Comunidad de Madrid.
    """
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
    TODO (Responsable P4): Mapear la tabla de referencia `convocatorias` (Sección 7.1.5) y retirar `__abstract__ = True`:
    - codigo_bdns (PK, String(30))
    - descripcion (Text)
    - organo_nivel1 (String(150))
    - organo_nivel2 (String(150))
    - organo_nivel3 (String(150))
    - fecha_recepcion (Date)
    - inicio_solicitud (Date)
    - fin_solicitud (Date)
    - abierta (Boolean)
    - presupuesto_total (Numeric(14, 2))
    - tipo_beneficiario (String(150))
    - poblacion_max_objetivo (Integer)
    - url_bases (Text)
    """
    __abstract__ = True
    __tablename__ = "convocatorias"


class ConvocatoriaMunicipio(Base):
    """
    TODO (Responsable P4): Mapear la tabla distribuida `convocatoria_municipio` (Sección 7.1.6) y retirar `__abstract__ = True`:
    - codigo_ine (PK compuesta 1/2, FK -> municipios.codigo_ine, String(5))
    - codigo_bdns (PK compuesta 2/2, FK -> convocatorias.codigo_bdns, String(30))
    - regla_asignacion (String(30): 'organo_local' | 'umbral_poblacion' | 'region_completa')
    - fecha_asignacion (DateTime)
    """
    __abstract__ = True
    __tablename__ = "convocatoria_municipio"

