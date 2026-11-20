"""
Servicio P3 de accesibilidad sanitaria con consultas espaciales KNN (`<->`) en PostGIS.

Gestiona la hidratación bajo demanda de `centros_sanitarios` desde la API de la CAM
y calcula los centros de urgencias y consultorios más cercanos a cada municipio usando
índices GiST y `ST_DistanceSphere`.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional

try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:  # pragma: no cover - permite pruebas unitarias sin entorno Docker

    def text(sql: str) -> str:  # type: ignore
        """Devuelve la consulta SQL sin modificar cuando SQLAlchemy no está disponible."""
        return sql

    AsyncSession = Any  # type: ignore

ETL_P3_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "etl", "p3_cam")
)
if os.path.isdir(ETL_P3_DIR) and ETL_P3_DIR not in sys.path:
    sys.path.insert(0, ETL_P3_DIR)

import etl_sanidad as cam_etl  # noqa: E402

logger = logging.getLogger("backend.p3_health_service")

SQL_GET_MUNICIPIO_NAME = text(
    """
    SELECT nombre
    FROM municipios
    WHERE codigo_ine = :codigo_ine
    LIMIT 1;
    """
)

SQL_COUNT_CENTROS_URGENCIAS = text(
    """
    SELECT COUNT(*) AS total_urg
    FROM centros_sanitarios
    WHERE tiene_urgencias = TRUE;
    """
)

SQL_COUNT_CENTROS_MUNICIPIO = text(
    """
    SELECT COUNT(*) AS total_mun
    FROM centros_sanitarios
    WHERE UPPER(municipio_nombre) = UPPER(:municipio_nombre);
    """
)

SQL_UPSERT_CENTRO_SANITARIO = text(
    """
    INSERT INTO centros_sanitarios (
        id_centro, nombre, tipo, tiene_urgencias,
        municipio_nombre, direccion, horario, telefono,
        latitud, longitud, geom
    )
    VALUES (
        :id_centro, :nombre, :tipo, :tiene_urgencias,
        :municipio_nombre, :direccion, :horario, :telefono,
        :latitud, :longitud, ST_SetSRID(ST_MakePoint(:longitud, :latitud), 4326)
    )
    ON CONFLICT (id_centro) DO UPDATE SET
        nombre = EXCLUDED.nombre,
        tipo = EXCLUDED.tipo,
        tiene_urgencias = EXCLUDED.tiene_urgencias,
        municipio_nombre = EXCLUDED.municipio_nombre,
        direccion = EXCLUDED.direccion,
        horario = EXCLUDED.horario,
        telefono = EXCLUDED.telefono,
        latitud = EXCLUDED.latitud,
        longitud = EXCLUDED.longitud,
        geom = EXCLUDED.geom;
    """
)

# Consulta espacial KNN (PostGIS <->) para obtener el centro con urgencias más cercano
# a cada municipio registrado en la tabla `municipios`.
SQL_KNN_NEAREST_EMERGENCY_ALL = text(
    """
    SELECT
        m.codigo_ine,
        m.nombre AS municipio_origen,
        cs.id_centro,
        cs.nombre,
        cs.tipo,
        cs.tiene_urgencias,
        cs.municipio_nombre,
        cs.direccion,
        cs.horario,
        cs.telefono,
        cs.latitud,
        cs.longitud,
        ROUND((ST_DistanceSphere(m.geom, cs.geom) / 1000.0)::numeric, 2) AS distancia_euclidea_km
    FROM municipios m
    CROSS JOIN LATERAL (
        SELECT
            c.id_centro,
            c.nombre,
            c.tipo,
            c.tiene_urgencias,
            c.municipio_nombre,
            c.direccion,
            c.horario,
            c.telefono,
            c.latitud,
            c.longitud,
            c.geom
        FROM centros_sanitarios c
        WHERE c.tiene_urgencias = TRUE
        ORDER BY m.geom <-> c.geom
        LIMIT 1
    ) cs
    ORDER BY m.codigo_ine;
    """
)

# Consulta espacial KNN para el centro de urgencias más cercano a un municipio específico
SQL_KNN_URGENCIA_FOR_MUNICIPIO = text(
    """
    SELECT
        cs.id_centro,
        cs.nombre,
        cs.tipo,
        cs.tiene_urgencias,
        cs.municipio_nombre,
        cs.direccion,
        cs.horario,
        cs.telefono,
        cs.latitud,
        cs.longitud,
        ROUND((ST_DistanceSphere(m.geom, cs.geom) / 1000.0)::numeric, 2) AS distancia_euclidea_km
    FROM municipios m
    CROSS JOIN LATERAL (
        SELECT
            c.id_centro,
            c.nombre,
            c.tipo,
            c.tiene_urgencias,
            c.municipio_nombre,
            c.direccion,
            c.horario,
            c.telefono,
            c.latitud,
            c.longitud,
            c.geom
        FROM centros_sanitarios c
        WHERE c.tiene_urgencias = TRUE
        ORDER BY m.geom <-> c.geom
        LIMIT 1
    ) cs
    WHERE m.codigo_ine = :codigo_ine;
    """
)

# Consulta espacial KNN para el consultorio o centro sanitario más cercano (con o sin urgencias)
SQL_KNN_CONSULTORIO_FOR_MUNICIPIO = text(
    """
    SELECT
        cs.id_centro,
        cs.nombre,
        cs.tipo,
        cs.tiene_urgencias,
        cs.municipio_nombre,
        cs.direccion,
        cs.horario,
        cs.telefono,
        cs.latitud,
        cs.longitud,
        ROUND((ST_DistanceSphere(m.geom, cs.geom) / 1000.0)::numeric, 2) AS distancia_euclidea_km
    FROM municipios m
    CROSS JOIN LATERAL (
        SELECT
            c.id_centro,
            c.nombre,
            c.tipo,
            c.tiene_urgencias,
            c.municipio_nombre,
            c.direccion,
            c.horario,
            c.telefono,
            c.latitud,
            c.longitud,
            c.geom
        FROM centros_sanitarios c
        ORDER BY m.geom <-> c.geom
        LIMIT 1
    ) cs
    WHERE m.codigo_ine = :codigo_ine;
    """
)


def _row_to_health_center_dict(row_mapping: Any) -> Dict[str, Any]:
    """Convierte una fila devuelta por SQLAlchemy en un diccionario serializable para la API."""
    return {
        "id_centro": str(row_mapping["id_centro"]),
        "nombre": str(row_mapping["nombre"]),
        "tipo": str(row_mapping["tipo"]),
        "tiene_urgencias": bool(row_mapping["tiene_urgencias"]),
        "municipio_nombre": row_mapping.get("municipio_nombre"),
        "direccion": row_mapping.get("direccion"),
        "horario": row_mapping.get("horario"),
        "telefono": row_mapping.get("telefono"),
        "latitud": float(row_mapping["latitud"]),
        "longitud": float(row_mapping["longitud"]),
        "distancia_euclidea_km": (
            float(row_mapping["distancia_euclidea_km"])
            if row_mapping.get("distancia_euclidea_km") is not None
            else None
        ),
    }


async def hydrate_health_centers_on_demand(
    db: AsyncSession,
    municipio_nombre: Optional[str] = None,
    codigo_ine: Optional[str] = None,
    force_refresh: bool = False,
) -> int:
    """
    Descarga e inserta bajo demanda los centros sanitarios de la CAM si el municipio
    o la red de urgencias aún no están en PostgreSQL (o si `force_refresh=True`).
    Devuelve el número de centros insertados o actualizados.
    """
    resolved_municipio = municipio_nombre.strip() if municipio_nombre else None
    if codigo_ine and not resolved_municipio:
        res_mun = await db.execute(SQL_GET_MUNICIPIO_NAME, {"codigo_ine": codigo_ine})
        row_mun = res_mun.mappings().first()
        if row_mun and row_mun.get("nombre"):
            resolved_municipio = str(row_mun["nombre"]).strip()

    res_urg_count = await db.execute(SQL_COUNT_CENTROS_URGENCIAS)
    row_urg_count = res_urg_count.mappings().first()
    total_urg = int(row_urg_count["total_urg"]) if row_urg_count else 0

    total_mun = 0
    if resolved_municipio:
        res_mun_count = await db.execute(
            SQL_COUNT_CENTROS_MUNICIPIO, {"municipio_nombre": resolved_municipio}
        )
        row_mun_count = res_mun_count.mappings().first()
        total_mun = int(row_mun_count["total_mun"]) if row_mun_count else 0

    if not force_refresh and total_urg > 0 and (not resolved_municipio or total_mun > 0):
        return 0

    logger.info(
        "Hidratación bajo demanda P3 desde API CAM (municipio=%s, codigo_ine=%s, force_refresh=%s)",
        resolved_municipio,
        codigo_ine,
        force_refresh,
    )
    all_centers = await asyncio.to_thread(
        cam_etl.fetch_cam_health_centers_api, None, True, force_refresh
    )

    if resolved_municipio:
        target_mun = cam_etl._normalize_text(resolved_municipio)
        centers_to_upsert = [
            c
            for c in all_centers
            if cam_etl._normalize_text(c.get("municipio_nombre")) == target_mun
            or (total_urg == 0 and bool(c.get("tiene_urgencias")))
        ]
    elif total_urg == 0:
        urg_centers = [c for c in all_centers if bool(c.get("tiene_urgencias"))]
        centers_to_upsert = urg_centers if urg_centers else list(all_centers)
    else:
        centers_to_upsert = list(all_centers)

    if not centers_to_upsert:
        return 0

    await db.execute(SQL_UPSERT_CENTRO_SANITARIO, centers_to_upsert)
    await db.commit()
    return len(centers_to_upsert)


async def get_nearest_emergency_all(db: AsyncSession) -> Dict[str, Dict[str, Any]]:
    """
    Obtiene para cada municipio el centro con urgencias más cercano mediante una
    búsqueda KNN (`<->`) y distancia geodésica en PostGIS. Devuelve un diccionario
    indexado por `codigo_ine`.
    """
    result = await db.execute(SQL_KNN_NEAREST_EMERGENCY_ALL)
    rows = result.mappings().all()

    nearest_by_ine: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        codigo_ine = str(row["codigo_ine"])
        nearest_by_ine[codigo_ine] = _row_to_health_center_dict(row)

    return nearest_by_ine


async def get_nearest_health_centers_for_municipio(
    db: AsyncSession,
    codigo_ine: str,
    force_refresh: bool = False,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Hidrata bajo demanda los centros del municipio si faltan en la base de datos y
    busca en PostGIS con KNN (`<->`) el centro de urgencias y el consultorio más cercanos.
    Devuelve un diccionario con las claves `"urgencias"` y `"consultorio"`.
    """
    await hydrate_health_centers_on_demand(
        db, codigo_ine=codigo_ine, force_refresh=force_refresh
    )

    res_urg = await db.execute(
        SQL_KNN_URGENCIA_FOR_MUNICIPIO, {"codigo_ine": codigo_ine}
    )
    row_urg = res_urg.mappings().first()

    res_cons = await db.execute(
        SQL_KNN_CONSULTORIO_FOR_MUNICIPIO, {"codigo_ine": codigo_ine}
    )
    row_cons = res_cons.mappings().first()

    return {
        "urgencias": _row_to_health_center_dict(row_urg) if row_urg else None,
        "consultorio": _row_to_health_center_dict(row_cons) if row_cons else None,
    }


async def list_centros_sanitarios_service(
    db: AsyncSession,
    solo_urgencias: Optional[bool] = None,
    municipio_nombre: Optional[str] = None,
    force_refresh: bool = False,
) -> List[Dict[str, Any]]:
    """
    Lista los centros sanitarios almacenados filtrando opcionalmente por urgencias
    o municipio. Si no hay resultados locales (o `force_refresh=True`), hidrata los
    datos bajo demanda desde la API de la CAM.
    """
    conditions = []
    params: Dict[str, Any] = {}

    if solo_urgencias is not None:
        conditions.append("tiene_urgencias = :solo_urgencias")
        params["solo_urgencias"] = solo_urgencias

    if municipio_nombre:
        conditions.append("UPPER(municipio_nombre) LIKE UPPER(:municipio_nombre)")
        params["municipio_nombre"] = f"%{municipio_nombre.strip()}%"

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = text(
        f"""
        SELECT
            id_centro,
            nombre,
            tipo,
            tiene_urgencias,
            municipio_nombre,
            direccion,
            horario,
            telefono,
            latitud,
            longitud
        FROM centros_sanitarios
        {where_clause}
        ORDER BY tiene_urgencias DESC, nombre ASC;
        """
    )

    if force_refresh:
        await hydrate_health_centers_on_demand(
            db, municipio_nombre=municipio_nombre, force_refresh=True
        )

    result = await db.execute(query, params)
    rows = result.mappings().all()

    if not rows and not force_refresh:
        inserted = await hydrate_health_centers_on_demand(
            db, municipio_nombre=municipio_nombre, force_refresh=False
        )
        if inserted > 0:
            result = await db.execute(query, params)
            rows = result.mappings().all()

    return [_row_to_health_center_dict(r) for r in rows]

