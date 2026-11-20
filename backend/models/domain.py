"""
Modelos ORM de SQLAlchemy alineados con el esquema normalizado y Citus-Ready (`db/schema.sql`).
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Municipio(Base):
    """
    TODO (Responsable P1): Mapear la tabla `municipios` (Sección 7.1.1):
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
    __tablename__ = "municipios"
    pass


class DemografiaAnual(Base):
    """
    TODO (Responsable P2): Mapear la tabla distribuida `demografia_anual` (Sección 7.1.2):
    - codigo_ine (PK compuesta 1/2, FK -> municipios.codigo_ine, String(5))
    - anio (PK compuesta 2/2, SmallInteger)
    - poblacion (Integer)
    - poblacion_mayor_65 (Integer)
    - poblacion_menor_15 (Integer)
    - tasa_envejecimiento (Numeric(5, 2))

    Se corresponde columna a columna con el Paso 3 de db/schema.sql. Notas:
    - Estilo SQLAlchemy 2.0: Mapped[tipo] fija el tipo en Python y si admite NULL;
      Mapped[Optional[int]] → la columna admite NULL; Mapped[int] → NOT NULL.
    - Al marcar las dos columnas con primary_key=True se forma la clave primaria compuesta
      (codigo_ine, anio). Mismo orden que en schema.sql: codigo_ine primero (columna de reparto en Citus).
    - Las tres columnas de edad son Optional: de momento no hay fuente de datos por edad
      (la tabla 69744 no tiene dimensión de edad), en la BD están a NULL y se leen como None.
    - Los CHECK y el índice solo se definen en schema.sql: la tabla la crea schema.sql y el ORM
      solo lee y escribe (no se usa create_all()), así que aquí no se repiten.
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
    """
    TODO (Responsable P1): Mapear la tabla distribuida `metricas_infraestructura` (Sección 7.1.3):
    - codigo_ine (PK, FK -> municipios.codigo_ine, String(5))
    - distancia_carretera_km (Numeric(6, 2))
    - distancia_recurso_hidrico_km (Numeric(6, 2))
    - cobertura_fibra_pct (Numeric(5, 2))
    - cobertura_movil_pct (Numeric(5, 2))
    - fecha_actualizacion (Date)
    """
    __tablename__ = "metricas_infraestructura"
    pass


class CentroSanitario(Base):
    """
    TODO (Responsable P3): Mapear la tabla de referencia `centros_sanitarios` (Sección 7.1.4):
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
    __tablename__ = "centros_sanitarios"
    pass


class Convocatoria(Base):
    """
    TODO (Responsable P4): Mapear la tabla de referencia `convocatorias` (Sección 7.1.5):
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
    __tablename__ = "convocatorias"
    pass


class ConvocatoriaMunicipio(Base):
    """
    TODO (Responsable P4): Mapear la tabla distribuida `convocatoria_municipio` (Sección 7.1.6):
    - codigo_ine (PK compuesta 1/2, FK -> municipios.codigo_ine, String(5))
    - codigo_bdns (PK compuesta 2/2, FK -> convocatorias.codigo_bdns, String(30))
    - regla_asignacion (String(30): 'organo_local' | 'umbral_poblacion' | 'region_completa')
    - fecha_asignacion (DateTime)
    """
    __tablename__ = "convocatoria_municipio"
    pass
