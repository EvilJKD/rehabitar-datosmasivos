"""
Aplicación principal FastAPI del proyecto Re-Habitar PoC.
Implementa el patrón de Ingesta Híbrida (Carga Semilla + Hidratación Bajo Demanda)
y la Fusión en Memoria (Sección 7.3 y Diagrama Sección 9):
cuando el usuario selecciona un municipio, si aún no está hidratado en BD,
el backend invoca a las fuentes de datos materializadas (P1 IGN/SETELECO, P2 INE,
P3 CAM, P4 BDNS), calcula la ruta sanitaria en tiempo real con CartoCiudad (P5.1)
sin almacenar tiempos en PostgreSQL, y ejecuta el motor WLC en memoria (P5.2).
"""

import os
import time
from typing import Any, Dict, List, Optional

try:
    from fastapi import Depends, FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    _HAS_FASTAPI = True
except ImportError:  # pragma: no cover - permite pruebas unitarias del Mediador en host sin fastapi
    _HAS_FASTAPI = False

    class HTTPException(Exception):  # type: ignore
        """Excepción HTTP sustitutiva cuando FastAPI no está instalado."""

        def __init__(self, status_code: int, detail: Any = None):
            """Guarda el código de estado y el detalle del error HTTP."""
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    def Depends(dependency: Any = None) -> Any:  # type: ignore
        """Devuelve la dependencia sin envolverla cuando falta FastAPI."""
        return dependency

    def Query(default: Any = None, **kwargs: Any) -> Any:  # type: ignore
        """Devuelve el valor por defecto del parámetro de consulta."""
        return default

    class FastAPI:  # type: ignore
        """Aplicación mínima para registrar rutas en pruebas sin FastAPI."""

        def __init__(self, **kwargs: Any):
            """Inicializa la lista de rutas registradas."""
            self.routes: List[Dict[str, Any]] = []

        def add_middleware(self, *args: Any, **kwargs: Any) -> None:
            """Ignora el registro de middlewares en modo de compatibilidad."""
            return None

        def mount(self, *args: Any, **kwargs: Any) -> None:
            """Ignora el montaje de ficheros estáticos en modo de compatibilidad."""
            return None

        def get(self, path: str, **kwargs: Any):
            """Registra un endpoint GET en la lista interna de rutas."""
            def decorator(fn):
                """Añade la función decorada como ruta GET y la devuelve."""
                self.routes.append({"method": "GET", "path": path, "fn": fn})
                return fn

            return decorator

        def post(self, path: str, **kwargs: Any):
            """Registra un endpoint POST en la lista interna de rutas."""
            def decorator(fn):
                """Añade la función decorada como ruta POST y la devuelve."""
                self.routes.append({"method": "POST", "path": path, "fn": fn})
                return fn

            return decorator

    CORSMiddleware = object  # type: ignore
    FileResponse = object  # type: ignore
    StaticFiles = object  # type: ignore

from core.database import get_db
from schemas import (
    CentroSanitarioSchema,
    ConvocatoriaMunicipioItemSchema,
    DemografiaPuntoAnualSchema,
    DemografiaSerieResponseSchema,
    InfraestructuraSchema,
    MunicipioDetailSchema,
    MunicipioListItemSchema,
    RutaSanitariaSchema,
    WLCBreakdownSchema,
)
from services._sa_compat import AsyncSession, text
from services.p1_geo_service import (
    get_all_municipios_base,
    get_municipio_by_ine,
    hydrate_infraestructura_on_demand,
)
from services.p2_demo_service import (
    get_demografia_serie_by_municipio,
    get_demografia_summary_all,
    hydrate_demografia_on_demand,
)
from services.p3_health_service import (
    get_nearest_emergency_all,
    get_nearest_health_centers_for_municipio,
    hydrate_health_centers_on_demand,
    list_centros_sanitarios_service,
)
from services.p4_grants_service import (
    get_convocatorias,
    get_grants_summary_all,
    get_num_ayudas_abiertas,
    hydrate_grants_on_demand,
)
from services.p5_cartociudad import (
    CARTOCIUDAD_CACHE_TTL_SECONDS,
    _CARTOCIUDAD_MEM_CACHE,
    calculate_route_cartociudad,
    compute_fallback_route,
)
from services.p5_wlc_engine import (
    WEIGHTS_GLOBAL_5,
    evaluate_wlc_for_municipio,
    filter_viable_municipios_c1,
)

app = FastAPI(
    title="Re-Habitar PoC - Ingesta Híbrida y Viabilidad Demográfica (CAM)",
    version="1.0.0",
)

if _HAS_FASTAPI:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _is_numeric_weight(val: Any) -> bool:
    """Comprueba si un peso recibido en la petición es un número válido."""
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def _build_custom_weights(
    w_demo: Optional[float] = None,
    w_health: Optional[float] = None,
    w_grants: Optional[float] = None,
    w_infra: Optional[float] = None,
    w_carretera: Optional[float] = None,
    w_sanidad: Optional[float] = None,
    w_conectividad: Optional[float] = None,
    w_hidrico: Optional[float] = None,
    w_demografia: Optional[float] = None,
) -> Optional[Dict[str, float]]:
    """Traduce los query params del API al diccionario de pesos de `evaluate_wlc_for_municipio`."""
    custom: Dict[str, float] = {}
    mapping = {
        "w_demo": w_demo,
        "w_health": w_health,
        "w_infra": w_infra,
        "w_carretera": w_carretera,
        "w_sanidad": w_sanidad,
        "w_conectividad": w_conectividad,
        "w_hidrico": w_hidrico,
        "w_demografia": w_demografia,
    }
    for key, val in mapping.items():
        if _is_numeric_weight(val):
            custom[key] = float(val)
    return custom or None


def _estimate_health_travel_minutes(
    lat_orig: float, lon_orig: float, urg: Optional[Dict[str, Any]]
) -> float:
    """
    Obtiene el tiempo de traslado en minutos desde la caché efímera en RAM de CartoCiudad
    o mediante estimación Haversine rural (45 km/h) sin generar llamadas N+1 en el listado.
    """
    if not urg:
        return 30.0
    lat_dest = float(urg["latitud"])
    lon_dest = float(urg["longitud"])
    cache_key = (
        round(float(lat_orig), 5),
        round(float(lon_orig), 5),
        round(lat_dest, 5),
        round(lon_dest, 5),
    )
    entry = _CARTOCIUDAD_MEM_CACHE.get(cache_key)
    if entry and (time.time() - float(entry["timestamp"])) < CARTOCIUDAD_CACHE_TTL_SECONDS:
        return float(entry["data"]["tiempo_estimado_min"])
    return float(compute_fallback_route(lat_orig, lon_orig, lat_dest, lon_dest)["tiempo_estimado_min"])


async def ensure_municipio_hydrated(
    db: AsyncSession, codigo_ine: str, force_refresh: bool = False
) -> str:
    """
    Asegura que el municipio exista y esté hidratado en PostgreSQL antes de evaluarlo.
    Reutiliza la caché en BD si ya tiene datos o ejecuta los módulos P1-P4 bajo demanda.
    """
    municipio = await get_municipio_by_ine(db, codigo_ine)
    if municipio is None:
        raise HTTPException(
            status_code=404,
            detail=f"Municipio {codigo_ine} no encontrado en el catálogo municipal.",
        )

    if (
        bool(municipio.get("hidratado"))
        and municipio.get("fecha_actualizacion") is not None
        and not force_refresh
    ):
        return "CACHE_POSTGRESQL"

    await hydrate_infraestructura_on_demand(db, codigo_ine)
    await hydrate_demografia_on_demand(db, codigo_ine)
    await hydrate_health_centers_on_demand(
        db, codigo_ine=codigo_ine, force_refresh=force_refresh
    )
    await hydrate_grants_on_demand(db, codigo_ine)
    return "INGESTA_EN_VIVO_GUARDADA_EN_BD"


@app.get("/api/health", tags=["Sistema"])
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Verifica PostgreSQL/PostGIS y reporta el avance de hidratación municipal."""
    res = await db.execute(
        text(
            """
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE hidratado) AS hidratados
            FROM municipios
            """
        )
    )
    row = res.mappings().first() or {"total": 0, "hidratados": 0}
    return {
        "status": "ok",
        "database": "postgresql+postgis",
        "total_municipios": int(row["total"]),
        "municipios_hidratados": int(row["hidratados"]),
    }


@app.get(
    "/api/municipios",
    response_model=List[MunicipioListItemSchema],
    tags=["P1-P5 Consultas Territoriales y Motor WLC"],
)
async def list_municipios(
    semaforo: Optional[str] = Query(
        None, description="Filtrar por color semafórico: VERDE, AMBAR, ROJO o PENDIENTE"
    ),
    min_wlc: Optional[float] = Query(
        None, ge=0.0, le=100.0, description="Consulta 1: Índice WLC mínimo (ej. 75.0)"
    ),
    requiere_fibra: Optional[bool] = Query(
        None, description="Consulta 1: Si es True, exige cobertura de fibra óptica"
    ),
    min_fibra_pct: float = Query(
        50.0, ge=0.0, le=100.0, description="Porcentaje mínimo de cobertura de fibra (por defecto 50%)"
    ),
    con_ayuda_abierta: Optional[bool] = Query(
        None, description="Filtrar municipios con ayudas BDNS abiertas asignadas"
    ),
    w_demo: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_health: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_grants: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_infra: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_carretera: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_sanidad: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_conectividad: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_hidrico: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_demografia: Optional[float] = Query(None, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
) -> List[MunicipioListItemSchema]:
    """
    Consulta 1 y listado territorial para Mapa V1:
    - Municipios hidratados (o con métricas + demografía en BD) calculan su índice WLC y semáforo.
    - Municipios aún no hidratados devuelven `hidratado=False` y `semaforo="PENDIENTE"`.
    """
    municipios = await get_all_municipios_base(db)
    demo_by_ine = await get_demografia_summary_all(db)
    health_by_ine = await get_nearest_emergency_all(db)
    grants_by_ine = await get_grants_summary_all(db)
    custom_weights = _build_custom_weights(
        w_demo=w_demo,
        w_health=w_health,
        w_grants=w_grants,
        w_infra=w_infra,
        w_carretera=w_carretera,
        w_sanidad=w_sanidad,
        w_conectividad=w_conectividad,
        w_hidrico=w_hidrico,
        w_demografia=w_demografia,
    )

    items: List[MunicipioListItemSchema] = []
    for m in municipios:
        codigo = m["codigo_ine"]
        demo = demo_by_ine.get(codigo)
        urg = health_by_ine.get(codigo)
        grants = grants_by_ine.get(codigo, {})
        num_ayudas = int(grants.get("num_ayudas_abiertas", 0))
        has_metrics = m.get("fecha_actualizacion") is not None

        if has_metrics and demo is not None:
            tiempo_min = _estimate_health_travel_minutes(
                float(m["latitud"]), float(m["longitud"]), urg
            )
            var_10a = demo.get("variacion_10a_pct")
            wlc_data = evaluate_wlc_for_municipio(
                distancia_carretera_km=float(m["distancia_carretera_km"]),
                tiempo_urgencias_min=tiempo_min,
                cobertura_fibra_pct=float(m["cobertura_fibra_pct"]),
                cobertura_movil_pct=float(m["cobertura_movil_pct"]),
                distancia_recurso_hidrico_km=float(m["distancia_recurso_hidrico_km"]),
                poblacion_actual=int(demo["poblacion_actual"]),
                variacion_10a_pct=float(var_10a if var_10a is not None else 0.0),
                custom_weights=custom_weights,
            )
            wlc_schema = WLCBreakdownSchema(**wlc_data)
        else:
            wlc_schema = WLCBreakdownSchema(
                indice_wlc=0.0,
                semaforo="PENDIENTE",
                etiqueta_viabilidad="Pendiente de hidratación bajo demanda",
                score_acceso_carretera=0.0,
                score_proximidad_sanitaria=0.0,
                score_conectividad_digital=0.0,
                score_acceso_hidrico=0.0,
                score_inercia_demografica=0.0,
                pesos_aplicados=dict(WEIGHTS_GLOBAL_5),
            )

        items.append(
            MunicipioListItemSchema(
                codigo_ine=codigo,
                nombre=m["nombre"],
                provincia=m["provincia"],
                comarca=m["comarca"],
                latitud=float(m["latitud"]),
                longitud=float(m["longitud"]),
                hidratado=bool(m.get("hidratado")),
                poblacion_actual=int(demo["poblacion_actual"]) if demo else None,
                variacion_10a_pct=demo.get("variacion_10a_pct") if demo else None,
                cobertura_fibra_pct=(
                    float(m["cobertura_fibra_pct"])
                    if m.get("cobertura_fibra_pct") is not None
                    else None
                ),
                num_ayudas_abiertas=num_ayudas,
                wlc=wlc_schema,
            )
        )

    if con_ayuda_abierta is not None:
        if con_ayuda_abierta:
            items = [it for it in items if it.num_ayudas_abiertas > 0]
        else:
            items = [it for it in items if it.num_ayudas_abiertas == 0]

    if min_wlc is not None or requiere_fibra is not None:
        items = filter_viable_municipios_c1(
            items,
            min_wlc=min_wlc if min_wlc is not None else 0.0,
            requiere_fibra=bool(requiere_fibra),
            min_fibra_pct=min_fibra_pct if requiere_fibra else 0.0,
        )

    if semaforo:
        target = semaforo.strip().upper()
        items = [it for it in items if it.wlc and it.wlc.semaforo.upper() == target]

    return items


@app.get(
    "/api/municipios/{codigo_ine}",
    response_model=MunicipioDetailSchema,
    tags=["P1-P5 Consultas Territoriales y Motor WLC"],
)
async def get_municipio_detail(
    codigo_ine: str,
    force_refresh: bool = Query(
        False, description="Si es True, fuerza la re-ingesta en vivo desde las fuentes externas"
    ),
    w_demo: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_health: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_grants: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_infra: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_carretera: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_sanidad: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_conectividad: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_hidrico: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_demografia: Optional[float] = Query(None, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
) -> MunicipioDetailSchema:
    """
    Devuelve la ficha completa de un municipio asegurando su hidratación previa en BD.
    Calcula en tiempo real la ruta sanitaria con CartoCiudad y evalúa el índice WLC en memoria.
    """
    origen = await ensure_municipio_hydrated(db, codigo_ine, force_refresh=force_refresh)

    municipio = await get_municipio_by_ine(db, codigo_ine)
    if municipio is None:
        raise HTTPException(status_code=404, detail=f"Municipio {codigo_ine} no encontrado.")

    demo = await get_demografia_serie_by_municipio(db, codigo_ine)
    centers = await get_nearest_health_centers_for_municipio(
        db, codigo_ine, force_refresh=force_refresh
    )
    urg = centers.get("urgencias") or centers.get("consultorio")
    convocatorias_raw = await get_convocatorias(db, codigo_ine=codigo_ine, solo_abiertas=True)

    ruta_schema: Optional[RutaSanitariaSchema] = None
    tiempo_urgencias_min = 45.0
    if urg is not None:
        route = await calculate_route_cartociudad(
            float(municipio["latitud"]),
            float(municipio["longitud"]),
            float(urg["latitud"]),
            float(urg["longitud"]),
            force_refresh=force_refresh,
        )
        tiempo_urgencias_min = float(route["tiempo_estimado_min"])
        ruta_schema = RutaSanitariaSchema(
            id_centro=urg["id_centro"],
            nombre=urg["nombre"],
            tipo=urg["tipo"],
            tiene_urgencias=bool(urg["tiene_urgencias"]),
            municipio_nombre=urg.get("municipio_nombre"),
            direccion=urg.get("direccion"),
            horario=urg.get("horario"),
            telefono=urg.get("telefono"),
            latitud=float(urg["latitud"]),
            longitud=float(urg["longitud"]),
            distancia_euclidea_km=(
                float(urg["distancia_euclidea_km"])
                if urg.get("distancia_euclidea_km") is not None
                else float(route["distancia_euclidea_km"])
            ),
            distancia_carretera_km=float(route["distancia_carretera_km"]),
            tiempo_estimado_min=tiempo_urgencias_min,
            fuente_ruta=route["fuente_ruta"],
            geometria_ruta=route["geometria_ruta"],
        )

    infra_schema = (
        InfraestructuraSchema(
            distancia_carretera_km=float(municipio["distancia_carretera_km"]),
            distancia_recurso_hidrico_km=float(municipio["distancia_recurso_hidrico_km"]),
            cobertura_fibra_pct=float(municipio["cobertura_fibra_pct"]),
            cobertura_movil_pct=float(municipio["cobertura_movil_pct"]),
            fecha_actualizacion=municipio["fecha_actualizacion"],
        )
        if municipio.get("fecha_actualizacion") is not None
        else None
    )

    custom_weights = _build_custom_weights(
        w_demo=w_demo,
        w_health=w_health,
        w_grants=w_grants,
        w_infra=w_infra,
        w_carretera=w_carretera,
        w_sanidad=w_sanidad,
        w_conectividad=w_conectividad,
        w_hidrico=w_hidrico,
        w_demografia=w_demografia,
    )
    wlc_schema: Optional[WLCBreakdownSchema] = None
    if infra_schema is not None and demo is not None:
        var_10a = demo.get("variacion_10a_pct")
        wlc_data = evaluate_wlc_for_municipio(
            distancia_carretera_km=infra_schema.distancia_carretera_km,
            tiempo_urgencias_min=tiempo_urgencias_min,
            cobertura_fibra_pct=infra_schema.cobertura_fibra_pct,
            cobertura_movil_pct=infra_schema.cobertura_movil_pct,
            distancia_recurso_hidrico_km=infra_schema.distancia_recurso_hidrico_km,
            poblacion_actual=int(demo["poblacion_actual"]),
            variacion_10a_pct=float(var_10a if var_10a is not None else 0.0),
            custom_weights=custom_weights,
        )
        wlc_schema = WLCBreakdownSchema(**wlc_data)

    return MunicipioDetailSchema(
        codigo_ine=municipio["codigo_ine"],
        nombre=municipio["nombre"],
        provincia=municipio["provincia"],
        comarca=municipio["comarca"],
        latitud=float(municipio["latitud"]),
        longitud=float(municipio["longitud"]),
        hidratado=bool(municipio.get("hidratado", True)),
        origen_datos=origen,
        poblacion_inicial_10a=demo.get("poblacion_inicial_10a") if demo else None,
        poblacion_actual=demo.get("poblacion_actual") if demo else None,
        variacion_10a_pct=demo.get("variacion_10a_pct") if demo else None,
        preserva_masa_critica=bool(demo.get("preserva_masa_critica", False)) if demo else False,
        inercia_demografica=demo.get("inercia_demografica", "SIN_DATOS") if demo else "SIN_DATOS",
        infraestructura=infra_schema,
        wlc=wlc_schema,
        urgencias_mas_cercana=ruta_schema,
        convocatorias=[ConvocatoriaMunicipioItemSchema(**c) for c in convocatorias_raw],
    )


@app.post(
    "/api/municipios/{codigo_ine}/ingest",
    response_model=MunicipioDetailSchema,
    tags=["Ingesta Híbrida Bajo Demanda"],
)
async def trigger_municipio_ingestion(
    codigo_ine: str,
    db: AsyncSession = Depends(get_db),
) -> MunicipioDetailSchema:
    """Fuerza la ingesta/actualización en vivo de un municipio y devuelve su ficha completa."""
    return await get_municipio_detail(
        codigo_ine=codigo_ine,
        force_refresh=True,
        w_demo=None,
        w_health=None,
        w_grants=None,
        w_infra=None,
        db=db,
    )


@app.get(
    "/api/municipios/{codigo_ine}/demografia",
    response_model=DemografiaSerieResponseSchema,
    tags=["P2 Demografía INE (Consulta C3)"],
)
async def get_municipio_demografia(
    codigo_ine: str, db: AsyncSession = Depends(get_db)
) -> DemografiaSerieResponseSchema:
    """
    Consulta 3 (P2) enriquecida para Visualización 2 (Chart.js):
    asegura hidratación y devuelve la serie histórica 2015-2025 junto a fibra, distancia a urgencias y ayudas.
    """
    await ensure_municipio_hydrated(db, codigo_ine)

    municipio = await get_municipio_by_ine(db, codigo_ine)
    centers = await get_nearest_health_centers_for_municipio(db, codigo_ine)
    urg = centers.get("urgencias") or centers.get("consultorio")
    num_ayudas = await get_num_ayudas_abiertas(db, codigo_ine)

    serie = await get_demografia_serie_by_municipio(
        db,
        codigo_ine,
        cobertura_fibra_pct=(
            float(municipio["cobertura_fibra_pct"])
            if municipio and municipio.get("cobertura_fibra_pct") is not None
            else None
        ),
        distancia_urgencias_km=(
            float(urg["distancia_euclidea_km"])
            if urg and urg.get("distancia_euclidea_km") is not None
            else None
        ),
        num_ayudas_abiertas=num_ayudas,
    )
    if serie is None:
        raise HTTPException(
            status_code=404,
            detail=f"No existe serie demográfica para el municipio {codigo_ine}.",
        )

    return DemografiaSerieResponseSchema(
        codigo_ine=serie["codigo_ine"],
        nombre=serie["nombre"],
        poblacion_inicial_10a=serie.get("poblacion_inicial_10a"),
        poblacion_actual=int(serie["poblacion_actual"]),
        variacion_10a_pct=serie.get("variacion_10a_pct"),
        cobertura_fibra_pct=serie.get("cobertura_fibra_pct"),
        distancia_urgencias_km=serie.get("distancia_urgencias_km"),
        num_ayudas_abiertas=serie.get("num_ayudas_abiertas"),
        serie_anual=[DemografiaPuntoAnualSchema(**p) for p in serie["serie_anual"]],
    )


@app.get(
    "/api/convocatorias",
    response_model=List[ConvocatoriaMunicipioItemSchema],
    tags=["P4 Subvenciones BDNS (Consulta C4)"],
)
async def list_convocatorias(
    codigo_ine: Optional[str] = Query(None, description="Filtrar por código INE del municipio"),
    categoria: Optional[str] = Query(
        None, description="Filtrar por finalidad/categoría de la convocatoria (ej. 'Infraestructuras', 'vivienda')"
    ),
    solo_abiertas: bool = Query(True, description="Si es True, solo convocatorias con el plazo abierto hoy"),
    abierta: Optional[bool] = Query(None, description="Alias de solo_abiertas para compatibilidad con el frontend"),
    db: AsyncSession = Depends(get_db),
) -> List[ConvocatoriaMunicipioItemSchema]:
    """
    Consulta 4 (P4): convocatorias de la BDNS aplicables al municipio (`codigo_ine`), con órgano
    convocante, presupuesto, fin de plazo y la regla por la que se asignaron
    (`organo_local | umbral_poblacion | region_completa`). Sin `codigo_ine`, lista el catálogo completo.
    """
    effective_solo_abiertas = solo_abiertas if (abierta is None or not isinstance(abierta, bool)) else abierta
    return await get_convocatorias(
        db, codigo_ine=codigo_ine, categoria=categoria, solo_abiertas=effective_solo_abiertas
    )


@app.get(
    "/api/centros-sanitarios",
    response_model=List[CentroSanitarioSchema],
    tags=["P3 Sanidad CAM"],
)
async def list_centros_sanitarios(
    solo_urgencias: Optional[bool] = Query(
        None, description="Filtrar solo centros con servicio de urgencias"
    ),
    municipio_nombre: Optional[str] = Query(
        None, description="Filtrar por nombre del municipio (ej. 'Buitrago del Lozoya')"
    ),
    force_refresh: bool = Query(
        False,
        description="Si es True, fuerza la consulta en vivo al endpoint de Datos Abiertos de la CAM",
    ),
    db: AsyncSession = Depends(get_db),
) -> List[Dict]:
    """
    Devuelve los centros sanitarios de `centros_sanitarios` para el mapa Leaflet (P3).
    Permite filtrar por disponibilidad de urgencias o municipio y activa la hidratación
    bajo demanda desde la API de Datos Abiertos de la Comunidad de Madrid cuando faltan datos.
    """
    return await list_centros_sanitarios_service(
        db,
        solo_urgencias=solo_urgencias,
        municipio_nombre=municipio_nombre,
        force_refresh=force_refresh,
    )


# Montaje opcional de archivos estáticos del frontend anterior (`frontend/`)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "frontend"))

if (
    _HAS_FASTAPI
    and os.path.isfile(os.path.join(FRONTEND_DIR, "index.html"))
    and os.path.isdir(os.path.join(FRONTEND_DIR, "css"))
    and os.path.isdir(os.path.join(FRONTEND_DIR, "js"))
):
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        """Sirve la página principal de la interfaz web."""
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
