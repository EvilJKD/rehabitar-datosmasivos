"""
Schemas Pydantic alineados con las Secciones 4, 6.4, 6.5, 7.1, 7.2 y 7.3 de la Propuesta.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class WLCBreakdownSchema(BaseModel):
    """
    TODO (Responsable P5 - Sección 4 y 6.4):
    Desglose pormenorizado de los 5 parámetros de habitabilidad (0 a 100):
    - indice_wlc: float (Puntuación de Viabilidad Global 0-100, ej. 96.05 en Madarcos)
    - semaforo: str ('VERDE', 'AMBAR', 'ROJO' o 'PENDIENTE')
    - etiqueta_viabilidad: str
    - score_acceso_carretera: float       (Indicador 1: Acceso por carretera asfaltada)
    - score_proximidad_sanitaria: float   (Indicador 2: Proximidad a urgencias en minutos CartoCiudad)
    - score_conectividad_digital: float   (Indicador 3: Fibra óptica + móvil)
    - score_acceso_hidrico: float         (Indicador 4: Cercanía a recursos hídricos)
    - score_inercia_demografica: float    (Indicador 5: Variación demográfica a 10 años)
    - pesos_aplicados: dict
    """
    pass


from .p1_geo import InfraestructuraSchema


class CentroSanitarioSchema(BaseModel):
    """
    Schema Pydantic para el directorio de Centros Sanitarios de la CAM (Sección 7.1.4 - P3).
    """
    id_centro: str = Field(..., description="Identificador único del centro (ej. 'CS-28027')")
    nombre: str = Field(..., description="Nombre oficial del centro sanitario")
    tipo: str = Field(..., description="Tipología: Centro de Salud, Consultorio Local, etc.")
    tiene_urgencias: bool = Field(
        default=False, description="Indica si dispone de atención continuada / urgencias 24h"
    )
    municipio_nombre: Optional[str] = Field(None, description="Nombre del municipio donde se ubica")
    direccion: Optional[str] = Field(None, description="Dirección postal completa")
    horario: Optional[str] = Field(None, description="Horario de atención")
    telefono: Optional[str] = Field(None, description="Teléfono de contacto")
    latitud: float = Field(..., description="Latitud en WGS84 (EPSG:4326)")
    longitud: float = Field(..., description="Longitud en WGS84 (EPSG:4326)")
    distancia_euclidea_km: Optional[float] = Field(
        None, description="Distancia en línea recta calculada en PostGIS (km)"
    )


class RutaSanitariaSchema(BaseModel):
    """
    Resultado de la consulta espacial KNN en PostGIS (P3) enriquecida bajo demanda
    con la integración virtual en tiempo real de CartoCiudad (P5 - Consulta 2 y Sección 7.3).
    """
    id_centro: str = Field(..., description="Identificador del centro (ej. 'CS-28027')")
    nombre: str = Field(..., description="Nombre del centro (ej. 'Consultorio Local Buitrago del Lozoya')")
    tipo: str = Field(..., description="Tipología del centro sanitario")
    tiene_urgencias: bool = Field(..., description="True si cuenta con servicio de urgencias")
    municipio_nombre: Optional[str] = Field(None, description="Municipio del centro sanitario")
    direccion: Optional[str] = Field(None, description="Dirección postal del centro")
    horario: Optional[str] = Field(None, description="Horario de atención")
    telefono: Optional[str] = Field(None, description="Teléfono de contacto")
    latitud: float = Field(..., description="Latitud WGS84 (EPSG:4326)")
    longitud: float = Field(..., description="Longitud WGS84 (EPSG:4326)")
    distancia_euclidea_km: float = Field(
        ..., description="Distancia en línea recta obtenida por KNN PostGIS (km)"
    )
    distancia_carretera_km: Optional[float] = Field(
        None, description="Distancia real por carretera desde CartoCiudad (ej. 11.4 km)"
    )
    tiempo_estimado_min: Optional[float] = Field(
        None, description="Tiempo estimado de conducción en minutos desde CartoCiudad (ej. 12.2 min)"
    )
    fuente_ruta: Optional[str] = Field(
        None, description="'API CartoCiudad IGN (Tiempo Real)' o 'Fallback Haversine'"
    )
    geometria_ruta: List[List[float]] = Field(
        default_factory=list,
        description="Lista de coordenadas [[lat, lon], ...] de la polilínea hacia el centro sanitario",
    )


class ConvocatoriaMunicipioItemSchema(BaseModel):
    """
    TODO (Responsable P4 - Consulta 4 y Sección 7.1.5 / 7.1.6):
    - codigo_bdns: str (ej. '921084')
    - descripcion: str
    - organo_nivel1: str
    - organo_nivel2: Optional[str]
    - organo_nivel3: Optional[str]
    - organo_convocante: str
    - fecha_recepcion: date
    - inicio_solicitud: Optional[date]
    - fin_solicitud: Optional[date]
    - abierta: bool
    - presupuesto_total: float
    - tipo_beneficiario: Optional[str]
    - url_bases: Optional[str]
    - regla_asignacion: Optional[str] ('organo_local' | 'umbral_poblacion' | 'region_completa')
    """
    pass


class MunicipioListItemSchema(BaseModel):
    """
    TODO: Elemento de `GET /api/municipios` (Consulta 1 y Mapa V1):
    - codigo_ine, nombre, provincia, comarca, latitud, longitud
    - hidratado: bool
    - poblacion_actual: int
    - variacion_10a_pct: float
    - cobertura_fibra_pct: float
    - num_ayudas_abiertas: int
    - wlc: WLCBreakdownSchema
    """
    pass


class MunicipioDetailSchema(BaseModel):
    """
    TODO: Ficha completa de `GET /api/municipios/{codigo_ine}` (Consultas 1, 2, 3, 4 y Fusión en Memoria):
    - codigo_ine, nombre, provincia, comarca, latitud, longitud
    - hidratado: bool
    - origen_datos: str
    - poblacion_inicial_10a: int
    - poblacion_actual: int
    - variacion_10a_pct: float
    - preserva_masa_critica: bool
    - inercia_demografica: str
    - infraestructura: InfraestructuraSchema
    - wlc: WLCBreakdownSchema
    - urgencias_mas_cercana: RutaSanitariaSchema
    - convocatorias: List[ConvocatoriaMunicipioItemSchema]
    """
    pass


class DemografiaPuntoAnualSchema(BaseModel):
    """
    TODO (Responsable P2 - Sección 7.1.2):
    - anio: int
    - poblacion: int
    - poblacion_mayor_65: Optional[int]
    - poblacion_menor_15: Optional[int]
    - tasa_envejecimiento: Optional[float]

    Dato de un año (un punto de la gráfica de líneas de Chart.js).
    Las tres columnas de edad son Optional con None por defecto, que corresponde al NULL de la BD
    (de momento no hay fuente de datos por edad); así el frontend puede distinguir «sin dato» de «0».
    """
    # from_attributes=True: además de con un dict, se puede construir directamente desde un objeto ORM (DemografiaAnual)
    model_config = ConfigDict(from_attributes=True)

    anio: int
    poblacion: int
    poblacion_mayor_65: Optional[int] = None
    poblacion_menor_15: Optional[int] = None
    tasa_envejecimiento: Optional[float] = None


class DemografiaSerieResponseSchema(BaseModel):
    """
    TODO (Responsable P2 - Consulta 3 y Visualización 2 en Chart.js):
    - codigo_ine: str
    - nombre: str
    - poblacion_inicial_10a: int
    - poblacion_actual: int
    - variacion_10a_pct: float
    - cobertura_fibra_pct: float
    - distancia_urgencias_km: float
    - num_ayudas_abiertas: int
    - serie_anual: List[DemografiaPuntoAnualSchema]

    Cambios respecto a la descripción original de arriba (todos para que, si falta un dato,
    no se rompa nada ni se invente nada):
    - poblacion_inicial_10a / variacion_10a_pct pasan a ser Optional:
      si al INE le falta el año de hace 10 años, o la población de entonces es 0, no se puede
      calcular y se devuelve None.
    - cobertura_fibra_pct (P1), distancia_urgencias_km (P3) y num_ayudas_abiertas (P4)
      pasan a ser Optional con None por defecto: salen de tablas de otros compañeros, el service
      de P2 no las consulta; las pasa quien llama (main.py) después de pedírselas a los services
      de P1/P3/P4. Si no se pasan, quedan en None.
    """
    codigo_ine: str
    nombre: str
    poblacion_inicial_10a: Optional[int] = None
    poblacion_actual: int
    variacion_10a_pct: Optional[float] = None
    cobertura_fibra_pct: Optional[float] = None
    distancia_urgencias_km: Optional[float] = None
    num_ayudas_abiertas: Optional[int] = None
    serie_anual: List[DemografiaPuntoAnualSchema]
