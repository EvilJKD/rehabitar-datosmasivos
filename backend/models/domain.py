"""
Modelos ORM de SQLAlchemy alineados con el esquema normalizado y Citus-Ready (`db/schema.sql`).
"""

from typing import Optional
from sqlalchemy import Boolean, Float, String
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

