"""
Modelos ORM de SQLAlchemy alineados con el esquema normalizado y Citus-Ready (`db/schema.sql`).
"""

from core.database import Base

import sqlalchemy as sa


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
    TODO (Responsable P2): Mapear la tabla distribuida `demografia_anual` (Sección 7.1.2):
    - codigo_ine (PK compuesta 1/2, FK -> municipios.codigo_ine, String(5))
    - anio (PK compuesta 2/2, SmallInteger)
    - poblacion (Integer)
    - poblacion_mayor_65 (Integer)
    - poblacion_menor_15 (Integer)
    - tasa_envejecimiento (Numeric(5, 2))
    """
    __tablename__ = "demografia_anual"
    pass


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
