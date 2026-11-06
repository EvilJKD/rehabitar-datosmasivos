"""
Schemas Pydantic alineados con las Secciones 4, 6.4, 6.5, 7.1, 7.2 y 7.3 de la Propuesta.
"""

from pydantic import BaseModel


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


class InfraestructuraSchema(BaseModel):
    """
    TODO (Responsable P1 - Sección 7.1.3):
    - distancia_carretera_km: float
    - distancia_recurso_hidrico_km: float
    - cobertura_fibra_pct: float
    - cobertura_movil_pct: float
    - fecha_actualizacion: date
    """
    pass


class RutaSanitariaSchema(BaseModel):
    """
    TODO (Responsables P3 y P5 - Consulta 2 y Sección 7.3):
    Resultado de la fusión en tiempo real entre KNN PostGIS y API CartoCiudad:
    - id_centro: str (ej. 'CS-28027')
    - nombre: str (ej. 'Consultorio Local Buitrago del Lozoya')
    - tipo: str (ej. 'Centro de Salud / Urgencias')
    - tiene_urgencias: bool
    - latitud: float
    - longitud: float
    - distancia_euclidea_km: float (KNN PostGIS)
    - distancia_carretera_km: float (En tiempo real desde CartoCiudad, ej. 11.4 km)
    - tiempo_estimado_min: float (En tiempo real desde CartoCiudad, ej. 12.2 min)
    - fuente_ruta: str ('API CartoCiudad IGN (Tiempo Real)' o 'Fallback Haversine')
    - geometria_ruta: List[List[float]]
    """
    pass


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
    """
    pass


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
    """
    pass
