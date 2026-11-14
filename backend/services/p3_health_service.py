"""
Servicio P3 - Análisis Espacial PostGIS de Accesibilidad Sanitaria (KNN <->)
Responsable: Desarrollador P3

Implementa la Consulta 2 de la Propuesta (Sección 7.2) empleando el operador
espacial KNN (`<->`) acelerado mediante índices GiST (`idx_centros_sanitarios_geom`
e `idx_centros_urgencias_geom`) y el cálculo geodésico `ST_DistanceSphere`.
"""

import logging
from typing import Any, Dict, List, Optional

try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:  # pragma: no cover - permite pruebas unitarias sin entorno Docker

    def text(sql: str) -> str:  # type: ignore
        return sql

    AsyncSession = Any  # type: ignore

logger = logging.getLogger("backend.p3_health_service")

# Consulta espacial KNN (PostGIS <->) para obtener el centro con urgencias más cercano
# a cada municipio registrado en la tabla `municipios` (Consulta 2 de la Propuesta).
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


async def get_nearest_emergency_all(db: AsyncSession) -> Dict[str, Dict[str, Any]]:
    """
    Ejecuta una consulta espacial en PostGIS que obtiene para cada municipio
    su centro sanitario con urgencias 24h (`tiene_urgencias = TRUE`) más cercano.
    - Usa `CROSS JOIN LATERAL` ordenando por el operador espacial KNN `ORDER BY m.geom <-> c.geom LIMIT 1`
      para aprovechar el índice GiST parcial `idx_centros_urgencias_geom`.
    - Calcula la distancia en línea recta en kilómetros usando `ST_DistanceSphere(m.geom, cs.geom) / 1000.0`.
    Devuelve un diccionario indexado por `codigo_ine`.
    """
    result = await db.execute(SQL_KNN_NEAREST_EMERGENCY_ALL)
    rows = result.mappings().all()

    nearest_by_ine: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        codigo_ine = str(row["codigo_ine"])
        nearest_by_ine[codigo_ine] = _row_to_health_center_dict(row)

    return nearest_by_ine


async def get_nearest_health_centers_for_municipio(
    db: AsyncSession, codigo_ine: str
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Dado un `codigo_ine`, ejecuta la búsqueda KNN en PostGIS (`ORDER BY m.geom <-> c.geom LIMIT 1`)
    para encontrar:
    1. `"urgencias"`: El centro con `tiene_urgencias = TRUE` más cercano.
    2. `"consultorio"`: El centro sanitario o consultorio local más cercano (con o sin urgencias).
    Devuelve un diccionario `{"urgencias": ..., "consultorio": ...}`.
    """
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
) -> List[Dict[str, Any]]:
    """
    Lista los centros sanitarios almacenados en `centros_sanitarios` para su representación
    en la capa cartográfica Leaflet (Visualización 1), permitiendo filtrar por disponibilidad
    de urgencias o nombre del municipio.
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

    result = await db.execute(query, params)
    rows = result.mappings().all()

    return [
        {
            "id_centro": str(r["id_centro"]),
            "nombre": str(r["nombre"]),
            "tipo": str(r["tipo"]),
            "tiene_urgencias": bool(r["tiene_urgencias"]),
            "municipio_nombre": r.get("municipio_nombre"),
            "direccion": r.get("direccion"),
            "horario": r.get("horario"),
            "telefono": r.get("telefono"),
            "latitud": float(r["latitud"]),
            "longitud": float(r["longitud"]),
        }
        for r in rows
    ]

