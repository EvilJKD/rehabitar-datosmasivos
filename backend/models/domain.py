"""
Modelos ORM de SQLAlchemy que representan las tablas definidas en `db/schema.sql`.
"""

from core.database import Base


class Municipio(Base):
    """
    TODO (Responsable P1): Mapear la tabla `municipios`:
    - codigo_ine (PK, String)
    - nombre (String)
    - comarca (String)
    - altitud_m (Integer)
    - superficie_km2 (Numeric)
    - latitud (Float)
    - longitud (Float)
    - created_at (DateTime)
    """
    __tablename__ = "municipios"
    pass


class DemografiaAnual(Base):
    """
    TODO (Responsable P2): Mapear la tabla `demografia_anual`:
    - id (PK, Integer)
    - codigo_ine (FK -> municipios.codigo_ine)
    - anio (Integer)
    - poblacion_total (Integer)
    - poblacion_mayor_65 (Integer)
    - poblacion_menor_15 (Integer)
    - tasa_envejecimiento (Numeric)
    """
    __tablename__ = "demografia_anual"
    pass


class CentroSanitario(Base):
    """
    TODO (Responsable P3): Mapear la tabla `centros_sanitarios`:
    - id_centro (PK, String)
    - nombre (String)
    - tipo_centro (String)
    - municipio_nombre (String)
    - direccion (String)
    - tiene_urgencias (Boolean)
    - horario (String)
    - telefono (String)
    - latitud (Float)
    - longitud (Float)
    """
    __tablename__ = "centros_sanitarios"
    pass


class Convocatoria(Base):
    """
    TODO (Responsable P4): Mapear la tabla `convocatorias`:
    - codigo_bdns (PK, String)
    - titulo (Text)
    - organo_convocante (String)
    - presupuesto_total (Numeric)
    - fecha_inicio (Date)
    - fecha_fin (Date)
    - categoria (String)
    - poblacion_max_objetivo (Integer)
    - url_ficha (Text)
    - activa (Boolean)
    """
    __tablename__ = "convocatorias"
    pass


class ConvocatoriaMunicipio(Base):
    """
    TODO (Responsable P4): Mapear la tabla puente `convocatoria_municipio`:
    - id (PK, Integer)
    - codigo_bdns (FK -> convocatorias.codigo_bdns)
    - codigo_ine (FK -> municipios.codigo_ine)
    - importe_estimado_hab (Numeric)
    - prioridad_asignacion (String)
    - justificacion_cruce (Text)
    """
    __tablename__ = "convocatoria_municipio"
    pass


class MetricaInfraestructura(Base):
    """
    TODO (Responsables P1 / P5): Mapear la tabla `metricas_infraestructura`:
    - codigo_ine (PK, FK -> municipios.codigo_ine)
    - cobertura_5g_pct (Numeric)
    - cobertura_fibra_pct (Numeric)
    - viviendas_vacias_pct (Numeric)
    - precio_m2_eur (Numeric)
    - servicios_basicos_score (Numeric)
    """
    __tablename__ = "metricas_infraestructura"
    pass
