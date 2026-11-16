"""
Schemas Pydantic alineados con las Secciones 4, 6.4, 6.5, 7.1, 7.2 y 7.3 de la Propuesta.
"""

from typing import Any, Callable, Dict, List, Optional

try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover - permite ejecutar pruebas unitarias en host sin pydantic

    class _DefaultFactory:
        def __init__(self, factory: Callable[[], Any]):
            self.factory = factory

    class BaseModel:  # type: ignore
        def __init__(self, **data: Any):
            for cls in reversed(type(self).__mro__):
                if cls is object or cls is BaseModel:
                    continue
                for attr_name, attr_val in cls.__dict__.items():
                    if attr_name.startswith("_"):
                        continue
                    if isinstance(attr_val, _DefaultFactory):
                        setattr(self, attr_name, attr_val.factory())
            for k, v in data.items():
                setattr(self, k, v)

        def model_dump(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

        def dict(self) -> Dict[str, Any]:
            return self.model_dump()

    def Field(  # type: ignore
        default: Any = None,
        *,
        default_factory: Optional[Callable[[], Any]] = None,
        **kwargs: Any,
    ) -> Any:
        if default_factory is not None:
            return _DefaultFactory(default_factory)
        return None if default is Ellipsis else default


class WLCBreakdownSchema(BaseModel):
    """
    Responsable P5 - Sección 4, 6.4 y 7.3:
    Desglose pormenorizado de los 5 parámetros de habitabilidad (0 a 100).
    """
    indice_wlc: float = Field(..., description="Puntuación de Viabilidad Global 0-100 (ej. 96.05 en Madarcos)")
    semaforo: str = Field(..., description="VERDE, AMBAR, ROJO o PENDIENTE")
    etiqueta_viabilidad: str = Field(..., description="Etiqueta descriptiva de viabilidad")
    score_acceso_carretera: float = Field(..., description="Indicador 1: Acceso por carretera asfaltada")
    score_proximidad_sanitaria: float = Field(..., description="Indicador 2: Proximidad a urgencias (CartoCiudad)")
    score_conectividad_digital: float = Field(..., description="Indicador 3: Fibra óptica FTTH + móvil")
    score_acceso_hidrico: float = Field(..., description="Indicador 4: Cercanía a recursos hídricos")
    score_inercia_demografica: float = Field(..., description="Indicador 5: Inercia demográfica a 10 años")
    pesos_aplicados: Dict[str, float] = Field(..., description="Ponderaciones normalizadas aplicadas")


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
    Responsables P3 y P5 - Consulta 2 y Sección 7.3:
    Resultado de la fusión en tiempo real entre KNN PostGIS y API CartoCiudad.
    """
    id_centro: str = Field(..., description="Identificador del centro sanitario (ej. 'CS-28027')")
    nombre: str = Field(..., description="Nombre del centro (ej. 'Consultorio Local Buitrago del Lozoya')")
    tipo: str = Field(..., description="Tipología del centro (ej. 'Centro de Salud / Urgencias')")
    tiene_urgencias: bool = Field(default=False, description="Indica si cuenta con servicio de urgencias")
    latitud: float = Field(..., description="Latitud WGS84 del centro")
    longitud: float = Field(..., description="Longitud WGS84 del centro")
    distancia_euclidea_km: float = Field(..., description="Distancia en línea recta obtenida por KNN PostGIS (km)")
    distancia_carretera_km: float = Field(..., description="Distancia real por carretera CartoCiudad (km)")
    tiempo_estimado_min: float = Field(..., description="Tiempo estimado en coche CartoCiudad (min)")
    fuente_ruta: str = Field(..., description="'API CartoCiudad IGN (Tiempo Real)' o 'Fallback Haversine (45 km/h)'")
    geometria_ruta: List[List[float]] = Field(
        default_factory=list,
        description="Polilínea [[lat, lon], ...] hacia el centro de urgencias",
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
