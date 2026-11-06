"""
Aplicación principal FastAPI del proyecto Re-Habitar PoC.
Define los endpoints REST para las consultas C1-C4 y el montaje del frontend estático.
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
    title="Re-Habitar PoC - Viabilidad Demográfica y Ayudas Rurales (CAM)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["Sistema"])
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict:
    """
    TODO: Comprobar la conexión a la base de datos ejecutando `SELECT PostGIS_Full_Version();`
    y devolver un JSON `{"status": "ok", "postgis": ...}`.
    """
    pass


@app.get(
    "/api/municipios",
    response_model=List[MunicipioListItemSchema],
    tags=["P1-P5 Consultas Territoriales y Motor WLC"],
)
async def list_municipios(
    semaforo: Optional[str] = Query(
        None, description="Filtrar por color semafórico: VERDE, AMBAR o ROJO"
    ),
    w_demo: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_health: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_grants: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_infra: Optional[float] = Query(None, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
) -> List[MunicipioListItemSchema]:
    """
    TODO: Endpoint principal para el listado y mapa semafórico de municipios:
    1. Obtener municipios base con `get_all_municipios_base(db)` (P1).
    2. Obtener resumen demográfico con `get_demografia_summary_all(db)` (P2).
    3. Obtener centro de urgencias más cercano con `get_nearest_emergency_all(db)` (P3).
    4. Obtener resumen de ayudas activas con `get_grants_summary_all(db)` (P4).
    5. Evaluar para cada municipio su puntuación y semáforo con `evaluate_wlc_for_municipio(...)` (P5).
    6. Filtrar por `semaforo` si se especificó en la query y retornar la lista de `MunicipioListItemSchema`.
    """
    pass


@app.get(
    "/api/municipios/{codigo_ine}",
    response_model=MunicipioDetailSchema,
    tags=["P1-P5 Consultas Territoriales y Motor WLC"],
)
async def get_municipio_detail(
    codigo_ine: str,
    w_demo: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_health: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_grants: Optional[float] = Query(None, ge=0.0, le=1.0),
    w_infra: Optional[float] = Query(None, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
) -> MunicipioDetailSchema:
    """
    TODO: Endpoint de detalle de un municipio al hacer clic en el mapa:
    1. Buscar el municipio con `get_municipio_by_ine(db, codigo_ine)` (lanzar HTTP 404 si no existe).
    2. Obtener sus indicadores demográficos (P2) y sus centros sanitarios más cercanos vía KNN PostGIS (P3).
    3. Invocar en vivo a `calculate_route_cartociudad(...)` (P5) para obtener los km por carretera,
       minutos estimados y polilínea hacia el centro de urgencias más cercano.
    4. Obtener la lista de ayudas activas del municipio con `get_convocatorias(db, codigo_ine=codigo_ine)` (P4).
    5. Calcular el desglose WLC con `evaluate_wlc_for_municipio(...)` (P5) y devolver `MunicipioDetailSchema`.
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
    TODO: Endpoint para alimentar la gráfica histórica 2015-2025 en Chart.js:
    1. Consultar el importe total de ayudas por habitante del municipio.
    2. Llamar a `get_demografia_serie_by_municipio(db, codigo_ine, importe_total_ayudas_hab)`.
    3. Si no existe el municipio, lanzar `HTTPException(status_code=404)`.
    4. Retornar `DemografiaSerieResponseSchema`.
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
    TODO: Endpoint de listado de convocatorias de la BDNS:
    - Llamar a `get_convocatorias(db, codigo_ine=codigo_ine, categoria=categoria)` y
      devolver la lista validada con `ConvocatoriaMunicipioItemSchema`.
    """
    pass


@app.get("/api/centros-sanitarios", tags=["P3 Sanidad CAM"])
async def list_centros_sanitarios(db: AsyncSession = Depends(get_db)) -> List[Dict]:
    """
    TODO: Devolver todos los centros sanitarios de la tabla `centros_sanitarios`
    para poder representarlos como capa adicional sobre el mapa Leaflet.
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
