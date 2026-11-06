"""
Servicio P5.2 - Motor WLC (Weighted Linear Combination) en Memoria (Escala 0 - 100)
Responsable: Desarrollador P5
"""

from typing import Dict, Optional


def clamp(val: float, low: float = 0.0, high: float = 100.0) -> float:
    """
    TODO: Limitar un valor numérico `val` para garantizar que permanezca en el rango `[low, high]`.
    """
    pass


def compute_demografia_score(
    poblacion_actual: int, variacion_10a_pct: float, tasa_envejecimiento: float
) -> float:
    """
    TODO: Calcular el Subíndice de Vitalidad Demográfica normalizado de 0 a 100:
    - Mayor variación poblacional en 10 años -> mayor puntuación.
    - Menor tasa de envejecimiento (>65 años) -> mayor puntuación.
    - Mayor masa crítica poblacional -> mayor puntuación.
    """
    pass


def compute_accesibilidad_sanitaria_score(distancia_urgencias_km: float) -> float:
    """
    TODO: Calcular el Subíndice de Accesibilidad Sanitaria normalizado de 0 a 100
    a partir de la distancia al centro de urgencias 24h más cercano (criterio de coste invertido:
    a menor distancia, mayor puntuación).
    """
    pass


def compute_capilaridad_ayudas_score(
    num_ayudas_activas: int, importe_total_ayudas_hab: float
) -> float:
    """
    TODO: Calcular el Subíndice de Capilaridad y Tracción de Subvenciones Públicas (0 a 100)
    combinando el número de convocatorias activas asignadas al municipio y el importe
    estimado por habitante (€/hab).
    """
    pass


def compute_infraestructura_score(
    cobertura_5g_pct: float,
    cobertura_fibra_pct: float,
    viviendas_vacias_pct: float,
    servicios_basicos_score: float,
) -> float:
    """
    TODO: Calcular el Subíndice de Conectividad Digital y Vivienda (0 a 100)
    combinando cobertura de fibra óptica, 5G, dotación de servicios básicos y porcentaje
    de viviendas vacías.
    """
    pass


def evaluate_wlc_for_municipio(
    poblacion_actual: int,
    variacion_10a_pct: float,
    tasa_envejecimiento: float,
    distancia_urgencias_km: float,
    num_ayudas_activas: int,
    importe_total_ayudas_hab: float,
    cobertura_5g_pct: float,
    cobertura_fibra_pct: float,
    viviendas_vacias_pct: float,
    servicios_basicos_score: float,
    custom_weights: Optional[Dict[str, float]] = None,
) -> Dict:
    """
    TODO: Ejecutar la Combinación Lineal Ponderada (WLC):
    1. Normalizar los 4 pesos (`w_demo`, `w_health`, `w_grants`, `w_infra`) para que sumen 1.0.
    2. Calcular los 4 subíndices (0-100) llamando a las funciones auxiliares anteriores.
    3. Calcular `indice_wlc = w_demo * s_demo + w_health * s_health + w_grants * s_grants + w_infra * s_infra`.
    4. Clasificar el semáforo según umbrales:
       - `VERDE` (ej. `>= 65.0`): Viabilidad Alta / Cabecera Resiliente
       - `AMBAR` (ej. `46.0` a `64.9`): Vulnerabilidad Media / En Transición
       - `ROJO` (ej. `< 46.0`): Riesgo Demográfico Crítico / Prioridad Máxima
    5. Retornar el diccionario compatible con `WLCBreakdownSchema`.
    """
    pass
