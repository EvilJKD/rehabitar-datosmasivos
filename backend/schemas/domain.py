"""Esquemas Pydantic de respuesta y serialización de la API de Re-Habitar PoC."""

from datetime import date
from typing import Any, Dict, List, Optional

from ._compat import BaseModel, ConfigDict, Field


class WLCBreakdownSchema(BaseModel):
    """Desglose de la puntuación WLC (0 a 100), semáforo de viabilidad y pesos aplicados."""
    indice_wlc: float = Field(..., description="Puntuación de Viabilidad Global 0-100 (ej. 96.05 en Madarcos)")
    semaforo: str = Field(..., description="VERDE, AMBAR, ROJO o PENDIENTE")
    etiqueta_viabilidad: str = Field(..., description="Etiqueta descriptiva de viabilidad")
    score_acceso_carretera: float = Field(..., description="Indicador 1: Acceso por carretera asfaltada")
    score_proximidad_sanitaria: float = Field(..., description="Indicador 2: Proximidad a urgencias (CartoCiudad)")
    score_conectividad_digital: float = Field(..., description="Indicador 3: Fibra óptica FTTH + móvil")
    score_acceso_hidrico: float = Field(..., description="Indicador 4: Cercanía a recursos hídricos")
    score_inercia_demografica: float = Field(..., description="Indicador 5: Inercia demográfica a 10 años")
    pesos_aplicados: Dict[str, float] = Field(..., description="Ponderaciones normalizadas aplicadas")


from .p1_geo import InfraestructuraSchema


class CentroSanitarioSchema(BaseModel):
    """Esquema de un centro sanitario de la Comunidad de Madrid y su distancia opcional al municipio."""
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
    """Centro sanitario más cercano obtenido por KNN en PostGIS junto con la ruta y tiempo estimados en tiempo real."""
    id_centro: str = Field(..., description="Identificador del centro sanitario (ej. 'CS-28027')")
    nombre: str = Field(..., description="Nombre del centro (ej. 'Consultorio Local Buitrago del Lozoya')")
    tipo: str = Field(..., description="Tipología del centro (ej. 'Centro de Salud / Urgencias')")
    tiene_urgencias: bool = Field(default=False, description="Indica si cuenta con servicio de urgencias")
    municipio_nombre: Optional[str] = Field(None, description="Municipio del centro sanitario")
    direccion: Optional[str] = Field(None, description="Dirección postal del centro")
    horario: Optional[str] = Field(None, description="Horario de atención")
    telefono: Optional[str] = Field(None, description="Teléfono de contacto")
    latitud: float = Field(..., description="Latitud WGS84 del centro")
    longitud: float = Field(..., description="Longitud WGS84 del centro")
    distancia_euclidea_km: float = Field(..., description="Distancia en línea recta obtenida por KNN PostGIS (km)")
    distancia_carretera_km: Optional[float] = Field(
        None, description="Distancia real por carretera CartoCiudad (ej. 11.4 km)"
    )
    tiempo_estimado_min: Optional[float] = Field(
        None, description="Tiempo estimado en coche CartoCiudad (ej. 12.2 min)"
    )
    fuente_ruta: Optional[str] = Field(
        None, description="'API CartoCiudad IGN (Tiempo Real)' o 'Fallback Haversine (45 km/h)'"
    )
    geometria_ruta: List[List[float]] = Field(
        default_factory=list,
        description="Polilínea [[lat, lon], ...] hacia el centro de urgencias",
    )


class ConvocatoriaMunicipioItemSchema(BaseModel):
    """
    Convocatoria de la BDNS con su órgano convocante, plazo, presupuesto, finalidad y umbral poblacional opcional.
    Incluye `regla_asignacion` cuando la consulta se filtra para un municipio concreto.
    """
    model_config = ConfigDict(from_attributes=True)

    codigo_bdns: str = Field(..., description="Código BDNS de la convocatoria (ej. '921084')")
    descripcion: str
    organo_nivel1: str = Field(..., description="'ESTADO', 'AUTONOMICA', 'LOCAL' u 'OTROS'")
    organo_nivel2: Optional[str] = None
    organo_nivel3: Optional[str] = None
    organo_convocante: str = Field(..., description="Órgano más específico (nivel3 > nivel2 > nivel1)")
    fecha_recepcion: date
    inicio_solicitud: Optional[date] = None
    fin_solicitud: Optional[date] = Field(None, description="Fin del plazo de solicitud (None = no publicado)")
    abierta: bool
    presupuesto_total: float = Field(..., ge=0)
    tipo_beneficiario: Optional[str] = None
    finalidad: Optional[str] = Field(None, description="Categoría BDNS (ej. 'Infraestructuras')")
    poblacion_max_objetivo: Optional[int] = Field(None, description="Umbral de habitantes (None = sin umbral)")
    url_bases: Optional[str] = None
    regla_asignacion: Optional[str] = Field(
        None, description="'organo_local' | 'umbral_poblacion' | 'region_completa' (solo al filtrar por municipio)"
    )


class MunicipioListItemSchema(BaseModel):
    """Resumen territorial de un municipio para el listado y mapa principal (`GET /api/municipios`)."""
    codigo_ine: str
    nombre: str
    provincia: str = Field(default="Madrid")
    comarca: str = Field(default="Sierra Norte")
    latitud: float
    longitud: float
    hidratado: bool = Field(default=False)
    poblacion_actual: Optional[int] = Field(default=None)
    variacion_10a_pct: Optional[float] = Field(default=None)
    cobertura_fibra_pct: Optional[float] = Field(default=None)
    num_ayudas_abiertas: int = Field(default=0)
    wlc: Optional[WLCBreakdownSchema] = Field(default=None)


class MunicipioDetailSchema(BaseModel):
    """Ficha completa de un municipio con demografía, infraestructura, índice WLC, urgencias y convocatorias."""
    codigo_ine: str
    nombre: str
    provincia: str = Field(default="Madrid")
    comarca: str = Field(default="Sierra Norte")
    latitud: float
    longitud: float
    hidratado: bool = Field(default=True)
    origen_datos: str = Field(default="CACHE_POSTGRESQL")
    poblacion_inicial_10a: Optional[int] = Field(default=None)
    poblacion_actual: Optional[int] = Field(default=None)
    variacion_10a_pct: Optional[float] = Field(default=None)
    preserva_masa_critica: bool = Field(default=False)
    inercia_demografica: str = Field(default="SIN_DATOS")
    infraestructura: Optional[InfraestructuraSchema] = Field(default=None)
    wlc: Optional[WLCBreakdownSchema] = Field(default=None)
    urgencias_mas_cercana: Optional[RutaSanitariaSchema] = Field(default=None)
    convocatorias: List[ConvocatoriaMunicipioItemSchema] = Field(default_factory=list)


class DemografiaPuntoAnualSchema(BaseModel):
    """
    Dato demográfico de un municipio en un año concreto para la serie histórica.
    Las columnas por grupo de edad admiten `None` cuando no hay desglose disponible en la fuente.
    """
    model_config = ConfigDict(from_attributes=True)

    anio: int
    poblacion: int
    poblacion_mayor_65: Optional[int] = None
    poblacion_menor_15: Optional[int] = None
    tasa_envejecimiento: Optional[float] = None


class DemografiaSerieResponseSchema(BaseModel):
    """
    Serie demográfica histórica de un municipio junto con sus variaciones e indicadores de contexto.
    La población inicial a 10 años y los indicadores de infraestructura, sanidad o ayudas admiten `None` si no están disponibles.
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
