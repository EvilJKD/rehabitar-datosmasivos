"""
Aplicación principal FastAPI del proyecto Re-Habitar PoC.
Implementa el patrón de Ingesta Híbrida (Carga Semilla + Hidratación Bajo Demanda):
cuando el usuario selecciona un municipio en el Frontend, si aún no está hidratado en BD,
el backend invoca a las fuentes de datos (INE, BDNS, CartoCiudad), persiste el registro
en PostgreSQL y lo devuelve al Frontend.
"""

import os
from typing import Dict, List, Optional
from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas import (
    ConvocatoriaMunicipioItemSchema,
    DemografiaSerieResponseSchema,
    MunicipioDetailSchema,
    MunicipioListItemSchema,
)

app = FastAPI(
    title="Re-Habitar PoC - Ingesta Híbrida y Viabilidad Demográfica (CAM)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def ensure_municipio_hydrated(
    db: AsyncSession, codigo_ine: str, force_refresh: bool = False
) -> str:
    """
    TODO (Orquestador de Ingesta Bajo Demanda en el Backend):
    1. Consultar en la tabla `municipios` si el pueblo `codigo_ine` tiene `hidratado == True`.
    2. Si `hidratado == True` y `not force_refresh`:
       - No necesita llamar a las APIs externas; retornar `origen_datos = "CACHE_POSTGRESQL"`.
    3. Si `hidratado == False` (o `force_refresh == True`):
       - Paso A (P1): Llamar a `await hydrate_infraestructura_on_demand(db, codigo_ine)` para guardar conectividad/vivienda.
       - Paso B (P2): Llamar a `await hydrate_demografia_on_demand(db, codigo_ine)` para descargar del INE e insertar la serie 2015-2025 en `demografia_anual`.
       - Paso C (P3 + P5): Obtener urgencias más cercana por KNN PostGIS y llamar a `await get_or_hydrate_route_for_municipio(...)` para consultar CartoCiudad y persistir la ruta en BD.
       - Paso D (P4): Llamar a `await hydrate_grants_on_demand(db, codigo_ine)` para cruzar e insertar sus ayudas BDNS en `convocatoria_municipio` y marcar `municipios.hidratado = TRUE`.
       - Retornar `origen_datos = "INGESTA_EN_VIVO_GUARDADA_EN_BD"`.
    """
    pass


@app.get("/api/health", tags=["Sistema"])
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict:
    """
    TODO: Verificar el estado de PostgreSQL/PostGIS y devolver cuántos municipios
    están ya hidratados en BD frente al total (`SELECT COUNT(*) FILTER (WHERE hidratado) ...`).
    """
    pass


@app.get(
    "/api/municipios",
    response_model=List[MunicipioListItemSchema],
    tags=["P1-P5 Consultas Territoriales y Motor WLC"],
)
async def list_municipios(
    semaforo: Optional[str] = Query(
        None, description="Filtrar por color semafórico: VERDE, AMBAR, ROJO o PENDIENTE"
    ),
    w_demo: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_health: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_grants: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_infra: Optional[float] = Query(None, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
) -> List[MunicipioListItemSchema]:
    """
    TODO: Devolver todos los municipios registrados en la carga inicial:
    - Los municipios con `hidratado == True` devuelven su índice WLC y semáforo calculado (`VERDE`, `AMBAR`, `ROJO`).
    - Los municipios con `hidratado == False` también se devuelven (con `hidratado = False` y estado preliminar/pendiente)
      para que aparezcan en el mapa y selector del Frontend listos para ser clicados e hidratados bajo demanda.
    """
    pass


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
    db: AsyncSession = Depends(get_db),
) -> MunicipioDetailSchema:
    """
    TODO: Endpoint clave de la Ingesta Híbrida cuando el usuario selecciona un pueblo en el Frontend:
    1. Llamar primero a `origen = await ensure_municipio_hydrated(db, codigo_ine, force_refresh)`.
       (Si el pueblo no tenía datos en BD, en este paso se consultan INE, BDNS y CartoCiudad y se guardan en PostgreSQL).
    2. Leer los datos ya persistidos en PostgreSQL (demografía, centro KNN, ruta CartoCiudad, ayudas BDNS).
    3. Evaluar el motor WLC (`evaluate_wlc_for_municipio`) y devolver `MunicipioDetailSchema` incluyendo `origen_datos = origen`.
    """
    pass


@app.post(
    "/api/municipios/{codigo_ine}/ingest",
    response_model=MunicipioDetailSchema,
    tags=["Ingesta Híbrida Bajo Demanda"],
)
async def trigger_municipio_ingestion(
    codigo_ine: str,
    db: AsyncSession = Depends(get_db),
) -> MunicipioDetailSchema:
    """
    TODO: Endpoint explícito para forzar desde el botón del Frontend la ingesta/actualización
    en vivo de un municipio contra las fuentes externas (`force_refresh=True`) y guardarlo en BD.
    """
    pass


@app.get(
    "/api/municipios/{codigo_ine}/demografia",
    response_model=DemografiaSerieResponseSchema,
    tags=["P2 Demografía INE (Consulta C3)"],
)
async def get_municipio_demografia(
    codigo_ine: str, db: AsyncSession = Depends(get_db)
) -> DemografiaSerieResponseSchema:
    """
    TODO: Asegurar que la demografía del municipio esté hidratada en BD y devolver
    la serie histórica 2015-2025 para el gráfico de Chart.js.
    """
    pass


@app.get(
    "/api/convocatorias",
    response_model=List[ConvocatoriaMunicipioItemSchema],
    tags=["P4 Subvenciones BDNS (Consulta C4)"],
)
async def list_convocatorias(
    codigo_ine: Optional[str] = Query(None, description="Filtrar por código INE del municipio"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría de la convocatoria"),
    db: AsyncSession = Depends(get_db),
) -> List[ConvocatoriaMunicipioItemSchema]:
    """
    TODO: Devolver las convocatorias de la BDNS filtradas por municipio y/o categoría.
    """
    pass


@app.get("/api/centros-sanitarios", tags=["P3 Sanidad CAM"])
async def list_centros_sanitarios(db: AsyncSession = Depends(get_db)) -> List[Dict]:
    """
    TODO: Devolver todos los centros sanitarios de `centros_sanitarios` para el mapa Leaflet.
    """
    pass


# Montaje de archivos estáticos del frontend (`frontend/`)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "frontend"))

if os.path.isdir(FRONTEND_DIR):
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
