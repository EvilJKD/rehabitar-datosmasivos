"""
Servicio P5.2 - Motor WLC (Weighted Linear Combination) en Memoria (Escala 0 - 100)
Responsable: Desarrollador P5

Alineado con la Sección 4 ("Metodología: Índice de Viabilidad WLC"), Sección 7.3
("Fusión en Memoria") y el Diagrama de la Sección 9 de la Propuesta:
Normaliza los 5 indicadores de habitabilidad a una escala común de 0 a 100 puntos:
  1. Acceso por carretera asfaltada (`distancia_carretera_km`) -> Peso PoC: 40% | Peso Global: 25%
  2. Proximidad a servicios sanitarios y de urgencia (`tiempo_urgencias_min` de CartoCiudad:
     <= 15 min = 100 pts; decae linealmente hasta 0 pts a los >= 45 min) -> Peso PoC: 30% | Peso Global: 20%
  3. Conectividad digital (`cobertura_fibra_pct` y `cobertura_movil_pct`) -> Peso Global: 20%
  4. Acceso a recursos hídricos (`distancia_recurso_hidrico_km`) -> Peso Global: 15%
  5. Inercia demográfica a 10 años (`variacion_10a_pct` y masa crítica) -> Peso PoC: 30% | Peso Global: 20%
"""

from typing import Dict, Optional


def clamp(val: float, low: float = 0.0, high: float = 100.0) -> float:
    """
    TODO: Limitar un valor numérico al rango `[low, high]`.
    """
    pass


def compute_acceso_carretera_score(distancia_carretera_km: float) -> float:
    """
    TODO (Indicador 1 - Sección 4): Basado en el Rural Access Index del Banco Mundial.
    - 0.0 km (conexión inmediata a carretera asfaltada, ej. Madarcos) -> 100 puntos.
    - Penaliza progresivamente conforme aumenta la distancia a carretera pavimentada.
    """
    pass


def compute_proximidad_sanitaria_score(tiempo_conduccion_min: float) -> float:
    """
    TODO (Indicador 2 - Sección 4): Siguiendo directrices europeas de tiempos de respuesta:
    - Desplazamientos <= 15.0 minutos en coche (ej. Madarcos = 12.2 min) -> 100 puntos.
    - Decae linealmente desde los 15 minutos hasta los 45 minutos (0 puntos a los >= 45 min).
    """
    pass


def compute_conectividad_digital_score(
    cobertura_fibra_pct: float, cobertura_movil_pct: float
) -> float:
    """
    TODO (Indicador 3 - Sección 4): Basado en el marco europeo PoliRURAL.
    Combina el porcentaje de cobertura de fibra óptica FTTH (ej. 60%) y cobertura móvil
    de alta velocidad 4G/5G (ej. 40%) en una escala de 0 a 100.
    """
    pass


def compute_acceso_hidrico_score(distancia_recurso_hidrico_km: float) -> float:
    """
    TODO (Indicador 4 - Sección 4): Mide la cercanía a cursos de agua continuos o fuentes
    de abastecimiento (`distancia_recurso_hidrico_km`, ej. 0.35 km en Madarcos -> ~95-100 pts).
    """
    pass


def compute_inercia_demografica_score(
    poblacion_actual: int, variacion_10a_pct: float
) -> float:
    """
    TODO (Indicador 5 - Sección 4): A partir de las series del INE a 10 años,
    identifica municipios con pérdidas moderadas o recuperación donde la masa social
    aún es rescatable, penalizando situaciones de colapso irreversible.
    """
    pass


def evaluate_wlc_for_municipio(
    distancia_carretera_km: float,
    tiempo_urgencias_min: float,
    cobertura_fibra_pct: float,
    cobertura_movil_pct: float,
    distancia_recurso_hidrico_km: float,
    poblacion_actual: int,
    variacion_10a_pct: float,
    modo_pesos: str = "GLOBAL_5",
    custom_weights: Optional[Dict[str, float]] = None,
) -> Dict:
    """
    TODO (Fusión en Memoria - Sección 4, 7.3 y Diagrama Sección 9):
    1. Calcular los 5 subíndices (0-100) llamando a las funciones anteriores.
    2. Aplicar las ponderaciones:
       - Modo 5 indicadores (Sección 4): Carretera 25%, Sanidad 20%, Conectividad 20%, Hídrico 15%, Demografía 20%.
       - Modo PoC 3 indicadores (Diagrama Sección 9): Carretera 40%, Sanidad 30%, Demografía 30%.
       - O `custom_weights` si el usuario ajusta los sliders en el Frontend.
    3. Clasificar el semáforo (`VERDE` >= 75, `AMBAR` 50 a 74.9, `ROJO` < 50).
    4. Retornar el diccionario con `indice_wlc`, `semaforo` y los 5 subíndices.
    """
    pass
