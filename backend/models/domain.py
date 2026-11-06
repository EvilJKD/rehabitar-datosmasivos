"""
Modelos ORM de SQLAlchemy alineados con el esquema normalizado y Citus-Ready (`db/schema.sql`).
"""

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
    """
    __tablename__ = "demografia_anual"
    pass


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
