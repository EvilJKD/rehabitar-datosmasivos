"""
Modelos ORM de SQLAlchemy alineados con el esquema normalizado y Citus-Ready (`db/schema.sql`).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Computed, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Municipio(Base):
    """
    TODO (Responsable P1): Mapear la tabla `municipios` (Sección 7.1.1) y retirar `__abstract__ = True`:
    - codigo_ine (PK, String(5))
    - nombre (String(120))
    - provincia (String(80), default='Madrid')
    - comarca (String(100), default='Sierra Norte')
    - latitud (Float)
    - longitud (Float)
    - hidratado (Boolean, default=False)
    - fecha_hidratacion (DateTime)
    - created_at (DateTime)
    """
    __abstract__ = True
    __tablename__ = "municipios"


class DemografiaAnual(Base):
    """
    TODO (Responsable P2): Mapear la tabla distribuida `demografia_anual` (Sección 7.1.2) y retirar `__abstract__ = True`:
    - codigo_ine (PK compuesta 1/2, FK -> municipios.codigo_ine, String(5))
    - anio (PK compuesta 2/2, SmallInteger)
    - poblacion (Integer)
    - poblacion_mayor_65 (Integer)
    - poblacion_menor_15 (Integer)
    - tasa_envejecimiento (Numeric(5, 2))
    """
    __abstract__ = True
    __tablename__ = "demografia_anual"


class MetricaInfraestructura(Base):
    """
    TODO (Responsable P1): Mapear la tabla distribuida `metricas_infraestructura` (Sección 7.1.3) y retirar `__abstract__ = True`:
    - codigo_ine (PK, FK -> municipios.codigo_ine, String(5))
    - distancia_carretera_km (Numeric(6, 2))
    - distancia_recurso_hidrico_km (Numeric(6, 2))
    - cobertura_fibra_pct (Numeric(5, 2))
    - cobertura_movil_pct (Numeric(5, 2))
    - fecha_actualizacion (Date)
    """
    __abstract__ = True
    __tablename__ = "metricas_infraestructura"


class CentroSanitario(Base):
    """
    TODO (Responsable P3): Mapear la tabla de referencia `centros_sanitarios` (Sección 7.1.4) y retirar `__abstract__ = True`:
    - id_centro (PK, String(40))
    - nombre (String(200))
    - tipo (String(100))
    - tiene_urgencias (Boolean)
    - municipio_nombre (String(120))
    - direccion (String(250))
    - horario (String(120))
    - telefono (String(30))
    - latitud (Float)
    - longitud (Float)
    """
    __abstract__ = True
    __tablename__ = "centros_sanitarios"


class Convocatoria(Base):
    """
    Tabla de referencia `convocatorias` (Sección 7.1.5 - P4): catálogo de convocatorias de la BDNS.

    Se corresponde columna a columna con la sección 5.1 de db/schema.sql:
    - `organo_convocante` es una columna GENERATED de PostgreSQL; con `Computed` el ORM sabe que
      no debe incluirla en los INSERT/UPDATE y solo la lee.
    - `poblacion_max_objetivo` NULL = la convocatoria no tiene umbral de población.
    - `finalidad` (añadida por P4) = `descripcionFinalidad` de la BDNS; alimenta el filtro `categoria`.
    - Los CHECK e índices solo viven en schema.sql: la tabla la crea schema.sql, el ORM no usa create_all().
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
    Tabla distribuida `convocatoria_municipio` (Sección 7.1.6 - P4): resultado de asignar cada
    convocatoria a los municipios a los que aplica.

    Clave primaria compuesta (codigo_ine, codigo_bdns), con codigo_ine primero (columna de reparto en Citus,
    co-localizada con demografia_anual y metricas_infraestructura).
    `regla_asignacion` ∈ {'organo_local', 'umbral_poblacion', 'region_completa'} (CHECK en schema.sql).
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
