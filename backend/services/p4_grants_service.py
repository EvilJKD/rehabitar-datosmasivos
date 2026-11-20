"""
Servicio P4 - Consulta C4 e Ingesta Bajo Demanda de Subvenciones (BDNS)
Responsable: Desarrollador P4

Consulta 4 (Sección 6.5): "¿Qué convocatorias aplicables al municipio seleccionado están abiertas,
y con qué órgano convocante, presupuesto y fecha de fin de plazo?"

Las convocatorias ya están materializadas en PostgreSQL por el ETL P4 (`convocatorias` y
`convocatoria_municipio`); este servicio solo las consulta. La asignación de un municipio nuevo
(hidratación bajo demanda) reutiliza la misma función del ETL para que las reglas estén en un único sitio.
"""

import asyncio
import os
import sys
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
    datos = dict(fila)
    datos["presupuesto_total"] = float(datos.get("presupuesto_total") or 0)
    return datos


async def hydrate_grants_on_demand(db: AsyncSession, codigo_ine: str) -> int:
    """
    Ingesta híbrida bajo demanda (P4): cuando el usuario selecciona en el Frontend un municipio
    todavía no cruzado con la BDNS, aplica las reglas de asignación (organo_local, umbral_poblacion,
    region_completa) sobre el catálogo `convocatorias`, guarda el resultado en `convocatoria_municipio`
    y marca `municipios.hidratado = TRUE`.

    El ETL usa psycopg2 (síncrono), así que se ejecuta en un hilo para no bloquear el bucle de FastAPI.
    `db` no se usa aquí: el ETL abre y confirma su propia conexión. Devuelve el nº de ayudas asignadas.
    """
    return await asyncio.to_thread(etl_bdns.ingest_bdns_for_municipio, codigo_ine)


async def get_grants_summary_all(db: AsyncSession) -> Dict[str, Dict]:
    """
    Resumen de ayudas por municipio (para el mapa, el listado y el motor WLC):
    {codigo_ine: {"num_ayudas_abiertas", "num_ayudas_total", "presupuesto_abiertas"}}.
    Los municipios sin ninguna asignación no aparecen (quien llama debe tratarlos como 0).
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
    """Número de convocatorias abiertas asignadas a un municipio (campo `num_ayudas_abiertas` de P2/P5)."""
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
    Consulta 4: convocatorias de la BDNS, ordenadas por fin de plazo más próximo.
    - `codigo_ine`: solo las asignadas a ese municipio (incluye `regla_asignacion`).
    - `categoria`: coincidencia parcial, sin distinguir mayúsculas, con la finalidad BDNS (ej. 'vivienda').
    - `solo_abiertas`: por defecto solo las que siguen abiertas hoy.
    Todos los valores van como parámetros enlazados (sin concatenar texto del usuario en el SQL).
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
