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

from typing import Any, Dict, List, Optional

WEIGHTS_GLOBAL_5: Dict[str, float] = {
    "carretera": 0.25,
    "sanidad": 0.20,
    "conectividad": 0.20,
    "hidrico": 0.15,
    "demografia": 0.20,
}

WEIGHTS_POC_3: Dict[str, float] = {
    "carretera": 0.40,
    "sanidad": 0.30,
    "conectividad": 0.00,
    "hidrico": 0.00,
    "demografia": 0.30,
}


def clamp(val: float, low: float = 0.0, high: float = 100.0) -> float:
    """Limita un valor numérico al rango `[low, high]`."""
    return max(float(low), min(float(high), float(val)))


def compute_acceso_carretera_score(distancia_carretera_km: float) -> float:
    """
    Indicador 1 (Sección 4) - Basado en el Rural Access Index del Banco Mundial.
    - 0.0 km (conexión inmediata a carretera asfaltada, ej. Madarcos) -> 100.0 puntos.
    - Decae linealmente hasta 0.0 puntos a los 15.0 km de camino sin asfaltar.
    """
    dist = max(0.0, float(distancia_carretera_km))
    return round(clamp(100.0 - (dist / 15.0) * 100.0), 2)


def compute_proximidad_sanitaria_score(tiempo_conduccion_min: float) -> float:
    """
    Indicador 2 (Sección 4) - Siguiendo directrices europeas de tiempos de respuesta:
    - Desplazamientos <= 15.0 minutos en coche (ej. Madarcos = 12.2 min) -> 100.0 puntos.
    - Decae linealmente desde los 15 minutos hasta los 45 minutos (0.0 puntos a los >= 45 min).
    """
    tiempo = max(0.0, float(tiempo_conduccion_min))
    if tiempo <= 15.0:
        return 100.0
    if tiempo >= 45.0:
        return 0.0
    return round(clamp(100.0 * (45.0 - tiempo) / 30.0), 2)


def compute_conectividad_digital_score(
    cobertura_fibra_pct: float, cobertura_movil_pct: float
) -> float:
    """
    Indicador 3 (Sección 4) - Basado en el marco europeo PoliRURAL.
    Combina el porcentaje de cobertura de fibra óptica FTTH (60%) y cobertura móvil
    de alta velocidad 4G/5G (40%) en una escala de 0 a 100.
    """
    fibra = clamp(float(cobertura_fibra_pct))
    movil = clamp(float(cobertura_movil_pct))
    return round(clamp(0.60 * fibra + 0.40 * movil), 2)


def compute_acceso_hidrico_score(distancia_recurso_hidrico_km: float) -> float:
    """
    Indicador 4 (Sección 4) - Mide la cercanía a cursos de agua continuos o fuentes
    de abastecimiento (`distancia_recurso_hidrico_km`, ej. 0.35 km en Madarcos -> 96.50 pts).
    """
    dist = max(0.0, float(distancia_recurso_hidrico_km))
    return round(clamp(100.0 - 10.0 * dist), 2)


def compute_inercia_demografica_score(
    poblacion_actual: int, variacion_10a_pct: float
) -> float:
    """
    Indicador 5 (Sección 4) - A partir de las series del INE a 10 años,
    identifica municipios con pérdidas moderadas o recuperación donde la masa social
    aún es rescatable, penalizando situaciones de despoblación crítica (< 30 hab).
    """
    pob = int(poblacion_actual)
    if pob <= 0:
        return 0.0

    var_pct = float(variacion_10a_pct)
    if var_pct >= 0.0:
        score = 95.0 + 0.5 * var_pct
    else:
        score = 95.0 + 1.4694 * var_pct

    if pob < 30:
        score -= 25.0

    return round(clamp(score), 2)


def _resolve_weights(
    modo_pesos: str = "GLOBAL_5",
    custom_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Selecciona y normaliza a suma 1.0 el diccionario de ponderaciones de los 5 indicadores."""
    modo_norm = (modo_pesos or "GLOBAL_5").strip().upper()
    base_weights = dict(
        WEIGHTS_POC_3 if modo_norm in ("POC_3", "POC", "POC3") else WEIGHTS_GLOBAL_5
    )

    if not custom_weights:
        return base_weights

    aliases = {
        "carretera": ("carretera", "w_carretera", "acceso_carretera"),
        "sanidad": ("sanidad", "w_sanidad", "w_health", "proximidad_sanitaria"),
        "conectividad": ("conectividad", "w_conectividad", "conectividad_digital"),
        "hidrico": ("hidrico", "w_hidrico", "acceso_hidrico"),
        "demografia": ("demografia", "w_demografia", "w_demo", "inercia_demografica"),
    }

    raw: Dict[str, Optional[float]] = {}
    for canonical_key, candidate_names in aliases.items():
        val: Optional[float] = None
        for alias in candidate_names:
            if alias in custom_weights and custom_weights[alias] is not None:
                val = max(0.0, float(custom_weights[alias]))
                break
        raw[canonical_key] = val

    # Soporte para parámetro legado `w_infra` / `infra` de backend/main.py:
    # Si llega `w_infra` sin desglose específico, se reparte proporcionalmente entre
    # los 3 pilares físicos/digitales (carretera 25%, conectividad 20%, hídrico 15%).
    legacy_infra = custom_weights.get("w_infra", custom_weights.get("infra"))
    if legacy_infra is not None:
        infra_val = max(0.0, float(legacy_infra))
        if raw["carretera"] is None and raw["hidrico"] is None:
            infra_base_total = (
                WEIGHTS_GLOBAL_5["carretera"]
                + WEIGHTS_GLOBAL_5["conectividad"]
                + WEIGHTS_GLOBAL_5["hidrico"]
            )
            raw["carretera"] = infra_val * (WEIGHTS_GLOBAL_5["carretera"] / infra_base_total)
            raw["conectividad"] = (
                infra_val * (WEIGHTS_GLOBAL_5["conectividad"] / infra_base_total)
                if raw["conectividad"] is None
                else raw["conectividad"]
            )
            raw["hidrico"] = infra_val * (WEIGHTS_GLOBAL_5["hidrico"] / infra_base_total)
        elif raw["conectividad"] is None:
            raw["conectividad"] = infra_val

    specified_keys = [k for k, v in raw.items() if v is not None]
    if not specified_keys:
        return base_weights

    unspecified_keys = [k for k, v in raw.items() if v is None]
    specified_sum = sum(float(raw[k]) for k in specified_keys)

    resolved: Dict[str, float] = {
        k: float(raw[k]) if raw[k] is not None else 0.0 for k in raw
    }

    # Si solo se enviaron algunos pesos parciales (< 1.0), distribuir el presupuesto
    # restante proporcionalmente entre los indicadores no especificados según `base_weights`.
    if unspecified_keys and specified_sum < (1.0 - 1e-9):
        remaining_budget = 1.0 - specified_sum
        base_unspecified_sum = sum(base_weights[k] for k in unspecified_keys)
        if base_unspecified_sum > 0.0:
            for k in unspecified_keys:
                resolved[k] = remaining_budget * (base_weights[k] / base_unspecified_sum)

    total = sum(resolved.values())
    if total > 0.0:
        return {k: v / total for k, v in resolved.items()}

    return base_weights


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
) -> Dict[str, Any]:
    """
    Fusión en Memoria (Sección 4, 7.3 y Diagrama Sección 9):
    1. Calcula los 5 subíndices (0-100).
    2. Aplica las ponderaciones (`GLOBAL_5`, `POC_3` o `custom_weights`).
    3. Clasifica el semáforo (`VERDE` >= 75, `AMBAR` 50 a 74.99, `ROJO` < 50).
    4. Retorna el diccionario compatible con `WLCBreakdownSchema`.
    """
    s_carretera = compute_acceso_carretera_score(distancia_carretera_km)
    s_sanidad = compute_proximidad_sanitaria_score(tiempo_urgencias_min)
    s_conectividad = compute_conectividad_digital_score(
        cobertura_fibra_pct, cobertura_movil_pct
    )
    s_hidrico = compute_acceso_hidrico_score(distancia_recurso_hidrico_km)
    s_demografia = compute_inercia_demografica_score(
        poblacion_actual, variacion_10a_pct
    )

    weights = _resolve_weights(modo_pesos=modo_pesos, custom_weights=custom_weights)

    indice_wlc = round(
        clamp(
            s_carretera * weights["carretera"]
            + s_sanidad * weights["sanidad"]
            + s_conectividad * weights["conectividad"]
            + s_hidrico * weights["hidrico"]
            + s_demografia * weights["demografia"]
        ),
        2,
    )

    if indice_wlc >= 75.0:
        semaforo = "VERDE"
        etiqueta_viabilidad = "Alta Viabilidad / Prioridad Rescate"
    elif indice_wlc >= 50.0:
        semaforo = "AMBAR"
        etiqueta_viabilidad = "Viabilidad Media / Requiere Refuerzo"
    else:
        semaforo = "ROJO"
        etiqueta_viabilidad = "Vulnerabilidad Crítica"

    return {
        "indice_wlc": indice_wlc,
        "semaforo": semaforo,
        "etiqueta_viabilidad": etiqueta_viabilidad,
        "score_acceso_carretera": s_carretera,
        "score_proximidad_sanitaria": s_sanidad,
        "score_conectividad_digital": s_conectividad,
        "score_acceso_hidrico": s_hidrico,
        "score_inercia_demografica": s_demografia,
        "pesos_aplicados": {k: round(v, 4) for k, v in weights.items()},
    }


def _get_field(obj: Any, key: str) -> Any:
    """Extrae un campo tanto de un diccionario como de un objeto o schema Pydantic."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _extract_wlc_score(item: Any) -> Optional[float]:
    """Obtiene el índice WLC desde `item.wlc.indice_wlc` o `item.indice_wlc`."""
    wlc_obj = _get_field(item, "wlc")
    raw_sub = _get_field(wlc_obj, "indice_wlc")
    raw_top = _get_field(item, "indice_wlc")
    raw_val = raw_sub if raw_sub is not None else raw_top
    return None if raw_val is None else float(raw_val)


def filter_viable_municipios_c1(
    municipios: List[Any],
    min_wlc: float = 75.0,
    requiere_fibra: bool = True,
    min_fibra_pct: float = 50.0,
) -> List[Any]:
    """
    Resuelve en memoria la Consulta 1 (Sección 6.5):
    Filtra los municipios con Índice WLC superior/igual al umbral (`min_wlc`, por defecto 75)
    y con cobertura de fibra óptica suficiente cuando `requiere_fibra=True`.
    Soporta tanto diccionarios como instancias de schemas (`MunicipioListItemSchema`, `WLCBreakdownSchema`).
    Ordena los resultados de mayor a menor puntuación WLC.
    """
    viables: List[Any] = []
    for item in municipios:
        wlc_score = _extract_wlc_score(item)
        if wlc_score is None or wlc_score < float(min_wlc):
            continue

        if requiere_fibra:
            raw_fibra_top = _get_field(item, "cobertura_fibra_pct")
            infra_obj = _get_field(item, "infraestructura")
            raw_fibra_sub = _get_field(infra_obj, "cobertura_fibra_pct")
            raw_fibra = raw_fibra_top if raw_fibra_top is not None else raw_fibra_sub
            fibra_pct = float(raw_fibra) if raw_fibra is not None else 0.0
            if min_fibra_pct <= 0.0:
                if fibra_pct <= 0.0:
                    continue
            elif fibra_pct < float(min_fibra_pct):
                continue

        viables.append(item)

    viables.sort(
        key=lambda m: _extract_wlc_score(m) or 0.0,
        reverse=True,
    )
    return viables
