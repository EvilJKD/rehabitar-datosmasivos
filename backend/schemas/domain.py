"""
Schemas Pydantic de entrada y salida para validar las respuestas JSON de FastAPI.
"""

from pydantic import BaseModel


class WLCBreakdownSchema(BaseModel):
    """
    TODO (Responsable P5): Definir los campos del resultado del motor WLC:
    - indice_wlc: float (0 a 100)
    - semaforo: str ('VERDE', 'AMBAR', 'ROJO')
    - etiqueta_viabilidad: str
    - score_demografia: float
    - score_accesibilidad_sanitaria: float
    - score_capilaridad_ayudas: float
    - score_infraestructura: float
    - pesos_aplicados: dict
    """
    pass


class InfraestructuraSchema(BaseModel):
    """
    TODO (Responsable P1): Definir campos de infraestructura municipal:
    - cobertura_5g_pct: float
    - cobertura_fibra_pct: float
    - viviendas_vacias_pct: float
    - precio_m2_eur: float
    - servicios_basicos_score: float
    """
    pass


class RutaSanitariaSchema(BaseModel):
    """
    TODO (Responsables P3 y P5): Definir campos del centro sanitario más cercano y su ruta:
    - id_centro: str
    - nombre: str
    - tipo_centro: str
    - municipio_nombre: str
    - direccion: Optional[str]
    - telefono: Optional[str]
    - horario: Optional[str]
    - tiene_urgencias: bool
    - latitud: float
    - longitud: float
    - distancia_euclidea_km: float (calculada en PostGIS KNN)
    - distancia_carretera_km: float (calculada con CartoCiudad o fallback Haversine)
    - tiempo_estimado_min: float
    - fuente_ruta: str
    - geometria_ruta: List[List[float]] (lista de coordenadas [lat, lon] para Leaflet)
    """
    pass


class ConvocatoriaMunicipioItemSchema(BaseModel):
    """
    TODO (Responsable P4): Definir campos de una convocatoria BDNS:
    - codigo_bdns: str
    - titulo: str
    - organo_convocante: str
    - presupuesto_total: float
    - fecha_inicio: date
    - fecha_fin: date
    - categoria: str
    - poblacion_max_objetivo: int
    - url_ficha: Optional[str]
    - activa: bool
    - importe_estimado_hab: Optional[float]
    - prioridad_asignacion: Optional[str]
    - justificacion_cruce: Optional[str]
    """
    pass


class MunicipioListItemSchema(BaseModel):
    """
    TODO: Schema resumido para cada elemento de `GET /api/municipios`:
    - codigo_ine, nombre, comarca, altitud_m, superficie_km2, latitud, longitud
    - poblacion_actual, variacion_10a_pct, tasa_envejecimiento
    - distancia_urgencias_km, centro_urgencias_nombre
    - num_ayudas_activas, importe_total_ayudas_hab
    - wlc: WLCBreakdownSchema
    """
    pass


class MunicipioDetailSchema(BaseModel):
    """
    TODO: Schema detallado para `GET /api/municipios/{codigo_ine}`:
    - Datos territoriales base + densidad_hab_km2
    - Indicadores demográficos C3 (poblacion_2015, poblacion_actual, variacion_10a_pct,
      variacion_5a_pct, tasa_envejecimiento, ratio_reemplazo_pct, inercia_demografica)
    - infraestructura: InfraestructuraSchema
    - wlc: WLCBreakdownSchema
    - urgencias_mas_cercana: RutaSanitariaSchema
    - consultorio_mas_cercano: Optional[RutaSanitariaSchema]
    - convocatorias: List[ConvocatoriaMunicipioItemSchema]
    """
    pass


class DemografiaPuntoAnualSchema(BaseModel):
    """
    TODO (Responsable P2): Punto anual de la serie histórica (2015-2025):
    - anio: int
    - poblacion_total: int
    - poblacion_mayor_65: int
    - poblacion_menor_15: int
    - tasa_envejecimiento: float
    - ayudas_estimadas_hab_anio: float
    """
    pass


class DemografiaSerieResponseSchema(BaseModel):
    """
    TODO (Responsable P2): Respuesta completa para `GET /api/municipios/{codigo_ine}/demografia`:
    - codigo_ine: str
    - nombre: str
    - poblacion_2015: int
    - poblacion_2025: int
    - variacion_10a_pct: float
    - tasa_envejecimiento_actual: float
    - inercia_tendencia: str
    - serie_anual: List[DemografiaPuntoAnualSchema]
    """
    pass
