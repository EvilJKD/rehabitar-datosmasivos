"""
Servicio P4 para consultar las convocatorias de la BDNS almacenadas en
PostgreSQL (Consulta 4) y asignar ayudas bajo demanda a municipios.
"""

import asyncio
import os
import sys
from typing import Dict, List, Optional

from ._sa_compat import AsyncSession, text

# En Docker PYTHONPATH ya incluye /app/etl; en local (tests, VS Code) se añade aquí.
ETL_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "etl"))
if os.path.isdir(ETL_DIR) and ETL_DIR not in sys.path:
    sys.path.insert(0, ETL_DIR)

from p4_bdns import etl_bdns  # noqa: E402

# "Abierta" se vuelve a comprobar con la fecha de hoy: el flag guardado es el del momento de la extracción.
_SQL_ABIERTA = "(c.abierta AND (c.fin_solicitud IS NULL OR c.fin_solicitud >= CURRENT_DATE))"

_COLUMNAS = """
    c.codigo_bdns, c.descripcion, c.organo_nivel1, c.organo_nivel2, c.organo_nivel3,
    c.organo_convocante, c.fecha_recepcion, c.inicio_solicitud, c.fin_solicitud,
    {abierta} AS abierta, c.presupuesto_total, c.tipo_beneficiario, c.finalidad,
    c.poblacion_max_objetivo, c.url_bases
""".format(abierta=_SQL_ABIERTA)


def _fila_a_dict(fila) -> Dict:
    """Convierte una fila de resultado SQL en diccionario asegurando presupuesto_total como float."""
    datos = dict(fila)
    datos["presupuesto_total"] = float(datos.get("presupuesto_total") or 0)
    return datos


async def hydrate_grants_on_demand(db: AsyncSession, codigo_ine: str) -> int:
    """
    Asigna bajo demanda las convocatorias del catálogo a un municipio y lo marca como hidratado.
    Ejecuta la función síncrona del ETL en un hilo separado para no bloquear FastAPI.
    """
    return await asyncio.to_thread(etl_bdns.ingest_bdns_for_municipio, codigo_ine)


async def get_grants_summary_all(db: AsyncSession) -> Dict[str, Dict]:
    """
    Devuelve el resumen de ayudas abiertas, totales y presupuesto acumulado por municipio.
    Los municipios sin asignaciones no se incluyen en el diccionario resultante.
    """
    resultado = await db.execute(
        text(
            f"""
            SELECT cm.codigo_ine,
                   COUNT(*) FILTER (WHERE {_SQL_ABIERTA})                              AS num_ayudas_abiertas,
                   COUNT(*)                                                            AS num_ayudas_total,
                   COALESCE(SUM(c.presupuesto_total) FILTER (WHERE {_SQL_ABIERTA}), 0) AS presupuesto_abiertas
            FROM convocatoria_municipio cm
            JOIN convocatorias c ON c.codigo_bdns = cm.codigo_bdns
            GROUP BY cm.codigo_ine
            """
        )
    )
    return {
        fila["codigo_ine"]: {
            "num_ayudas_abiertas": int(fila["num_ayudas_abiertas"]),
            "num_ayudas_total": int(fila["num_ayudas_total"]),
            "presupuesto_abiertas": float(fila["presupuesto_abiertas"]),
        }
        for fila in resultado.mappings().all()
    }


async def get_num_ayudas_abiertas(db: AsyncSession, codigo_ine: str) -> int:
    """Devuelve el número de convocatorias abiertas asignadas al municipio indicado."""
    resultado = await db.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM convocatoria_municipio cm
            JOIN convocatorias c ON c.codigo_bdns = cm.codigo_bdns
            WHERE cm.codigo_ine = :codigo_ine AND {_SQL_ABIERTA}
            """
        ),
        {"codigo_ine": codigo_ine},
    )
    return int(resultado.scalar() or 0)


async def get_convocatorias(
    db: AsyncSession,
    codigo_ine: Optional[str] = None,
    categoria: Optional[str] = None,
    solo_abiertas: bool = True,
) -> List[Dict]:
    """
    Implementa la Consulta 4 devolviendo convocatorias ordenadas por fin de plazo más próximo.
    Permite filtrar opcionalmente por código INE del municipio, finalidad y estado abierto.
    """
    params: Dict[str, object] = {}
    condiciones: List[str] = []

    if codigo_ine:
        origen = "FROM convocatoria_municipio cm JOIN convocatorias c ON c.codigo_bdns = cm.codigo_bdns"
        regla = "cm.regla_asignacion"
        condiciones.append("cm.codigo_ine = :codigo_ine")
        params["codigo_ine"] = codigo_ine
    else:
        origen = "FROM convocatorias c"
        regla = "NULL::varchar"

    if solo_abiertas:
        condiciones.append(_SQL_ABIERTA)
    if categoria:
        condiciones.append("c.finalidad ILIKE :categoria")
        params["categoria"] = f"%{categoria.strip()}%"

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    sql = f"""
        SELECT {_COLUMNAS}, {regla} AS regla_asignacion
        {origen}
        {where}
        ORDER BY c.fin_solicitud ASC NULLS LAST, c.presupuesto_total DESC, c.codigo_bdns
    """
    resultado = await db.execute(text(sql), params)
    return [_fila_a_dict(fila) for fila in resultado.mappings().all()]
