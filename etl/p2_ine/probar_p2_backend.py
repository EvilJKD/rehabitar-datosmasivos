#!/usr/bin/env python3
"""
Pruebas locales de la parte de backend de P2 (ORM, schema y p2_demo_service).

Necesita un PostgreSQL temporal (sin volume, se borra al pararlo):
    docker run --rm -d --name p2_test -p 5433:5432 -e POSTGRES_USER=rehabitar \
        -e POSTGRES_PASSWORD=rehabitar_pwd -e POSTGRES_DB=rehabitar_db postgres:15
Ejecución:
    python etl/p2_ine/probar_p2_backend.py

Ojo: al arrancar, el script hace DROP y vuelve a crear en esta BD de prueba la tabla municipios
(versión provisional, solo dos columnas) y demografia_anual (ejecutando directamente el bloque de
P2 de db/schema.sql).
Para no conectarnos por error a la base de datos del grupo, si el puerto no es 5433 se niega a ejecutarse.
"""

import ast
import asyncio
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ / "backend"), str(RAIZ / "etl")]

# El ETL (psycopg2) lee estas variables de entorno; el backend (asyncpg) usa la URL que montamos abajo. Los dos van contra la misma BD de prueba.
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5433")
os.environ.pop("DATABASE_URL_SYNC", None)   # así el ETL no puede tirar de otra cadena de conexión
PUERTO = os.environ["POSTGRES_PORT"]
if PUERTO != "5433":
    sys.exit(f"Por seguridad este script solo usa el puerto 5433 (p2_test), no {PUERTO}.")
URL_ASYNC = f"postgresql+asyncpg://rehabitar:rehabitar_pwd@localhost:{PUERTO}/rehabitar_db"

from sqlalchemy import Column, MetaData, String, Table, select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.orm import DeclarativeBase  # noqa: E402

from schemas.domain import DemografiaPuntoAnualSchema, DemografiaSerieResponseSchema  # noqa: E402
from services import p2_demo_service as p2  # noqa: E402

RESULTADOS: list[tuple[bool, str]] = []


def comprobar(condicion: bool, descripcion: str, detalle: str = "") -> None:
    RESULTADOS.append((bool(condicion), descripcion))
    marca = "OK  " if condicion else "FAIL"
    print(f"  [{marca}] {descripcion}" + (f"  ({detalle})" if detalle else ""))


# =============================================================================
# Preparación de la BD de prueba
# =============================================================================

def _sql_paso3() -> str:
    """Extrae solo el bloque de P2 de db/schema.sql (desde CREATE TABLE demografia_anual hasta su índice)."""
    lineas, dentro = [], False
    for linea in (RAIZ / "db" / "schema.sql").read_text(encoding="utf-8").splitlines():
        if linea.startswith("CREATE TABLE IF NOT EXISTS demografia_anual"):
            dentro = True
        if dentro:
            lineas.append(linea)
            if linea.startswith("CREATE INDEX IF NOT EXISTS idx_demografia_anio_codigo"):
                break
    return "\n".join(lineas)


async def preparar_bd(engine) -> None:
    paso3 = _sql_paso3()
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS demografia_anual"))
        await conn.execute(text("DROP TABLE IF EXISTS municipios"))
        # municipios provisional: solo está para que la FK funcione, no es la definición oficial de P1
        await conn.execute(text(
            "CREATE TABLE municipios (codigo_ine VARCHAR(5) PRIMARY KEY, nombre VARCHAR(120) NOT NULL)"
        ))
        await conn.execute(text(
            "INSERT INTO municipios VALUES "
            "('28069', 'La Hiruela'), ('28027', 'Buitrago del Lozoya'), ('28078', 'Madarcos')"
        ))
        # asyncpg solo ejecuta una sentencia cada vez, así que partimos por ';' (en este SQL ningún literal lleva punto y coma)
        for sentencia in paso3.split(";"):
            if sentencia.strip():
                await conn.execute(text(sentencia))


# =============================================================================
# Pruebas
# =============================================================================

def probar_clasificacion() -> None:
    print("\n== 1. Funciones puras: variación y clasificación (valores frontera) ==")
    v = p2.calcular_variacion_pct
    comprobar(v(2034, 1865) == 9.06, "variación normal (Buitrago 2015→2025)", f"{v(2034, 1865)}")
    comprobar(v(100, 0) is None, "base = 0 → None (no divide entre 0)")
    comprobar(v(100, None) is None and v(None, 100) is None, "año ausente → None")
    comprobar(v(0, 50) == -100.0, "pueblo que llega a 0 habitantes → -100%")

    c = p2.classify_demographic_inertia
    casos = [
        # (var_10a, var_5a, pob, esperado, motivo)
        (None, 3.0, 500, p2.SIN_DATOS, "sin dato a 10 años"),
        (-20.0, 5.0, 500, p2.COLAPSO, "-20% exacto es COLAPSO (≤)"),
        (-19.99, -1.0, 500, p2.DECLIVE, "-19.99% ya no es COLAPSO"),
        (-1.0, -1.0, 49, p2.COLAPSO, "<50 hab y bajando → COLAPSO"),
        (-1.0, 10.0, 49, p2.COLAPSO, "COLAPSO tiene prioridad sobre REPUNTE"),
        (-1.0, -1.0, 50, p2.ESTANCAMIENTO, "50 hab ya no cuenta como <50"),
        (0.0, -1.0, 30, p2.ESTANCAMIENTO, "<50 hab pero var_10a = 0 (no baja)"),
        (-10.0, 0.01, 500, p2.REPUNTE_RECIENTE, "baja a 10a pero sube a 5a"),
        (-10.0, 0.0, 500, p2.DECLIVE, "var_5a = 0 no es repunte (> 0)"),
        (-10.0, None, 500, p2.DECLIVE, "var_5a ausente no es repunte"),
        (-2.0, 1.0, 500, p2.REPUNTE_RECIENTE, "REPUNTE tiene prioridad sobre ESTANCAMIENTO"),
        (-5.0, -1.0, 500, p2.DECLIVE, "-5% exacto es DECLIVE (≤)"),
        (-4.99, -1.0, 500, p2.ESTANCAMIENTO, "-4.99% es ESTANCAMIENTO"),
        (4.99, 3.0, 500, p2.ESTANCAMIENTO, "+4.99% es ESTANCAMIENTO"),
        (5.0, 0.01, 500, p2.RECUPERACION, "+5% exacto y var_5a > 0 → RECUPERACION"),
        (12.0, 0.0, 500, p2.ESTANCAMIENTO, "caso no cubierto: +12% pero var_5a = 0"),
        (12.0, -3.0, 500, p2.ESTANCAMIENTO, "caso no cubierto: +12% pero var_5a < 0"),
    ]
    for var_10a, var_5a, pob, esperado, motivo in casos:
        obtenido = c(var_10a, var_5a, None, pob)
        comprobar(obtenido == esperado, motivo, f"{var_10a}, {var_5a}, pob={pob} → {obtenido}")
    comprobar(c(-10.0, 1.0, 35.5, 500) == c(-10.0, 1.0, None, 500), "tasa_env no cambia el resultado")

    comprobar(p2.preserva_masa_critica(100) and not p2.preserva_masa_critica(99),
              "masa crítica: 100 sí, 99 no")
    comprobar(p2.preserva_masa_critica(None) is False, "masa crítica sin dato → False")

    ind = p2.calcular_indicadores({2025: 88, 2020: 65})
    comprobar(ind["variacion_10a_pct"] is None and ind["inercia_demografica"] == p2.SIN_DATOS,
              "calcular_indicadores sin año -10 → SIN_DATOS")
    comprobar(p2.calcular_indicadores({}) is None, "calcular_indicadores con serie vacía → None")


async def probar_orm(Session) -> None:
    """
    models/domain.py no se puede importar entero todavía: la clase Municipio (P1) no tiene
    columnas y SQLAlchemy da error al definirla. Por eso aquí se extrae solo el código de
    la clase DemografiaAnual y se ejecuta con una Base nueva, sin tocar el archivo de P1.
    """
    print("\n== 2. ORM DemografiaAnual (solo la clase de P2) ==")
    fuente = (RAIZ / "backend" / "models" / "domain.py").read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    clase = next(n for n in arbol.body if isinstance(n, ast.ClassDef) and n.name == "DemografiaAnual")
    imports = [n for n in arbol.body if isinstance(n, (ast.Import, ast.ImportFrom))
               and getattr(n, "module", "") != "core.database"]

    class BasePrueba(DeclarativeBase):
        metadata = MetaData()

    # municipios mínima en el mismo MetaData para que la ForeignKey se pueda resolver
    Table("municipios", BasePrueba.metadata, Column("codigo_ine", String(5), primary_key=True))
    # __name__ hace falta: sin él la clase queda con __module__ = 'builtins'
    # y pydantic (from_attributes) la rechaza como si fuera un tipo interno.
    espacio = {"Base": BasePrueba, "__name__": "models.domain"}
    exec(compile(ast.Module(body=imports + [clase], type_ignores=[]), "domain.py", "exec"), espacio)
    DemografiaAnual = espacio["DemografiaAnual"]

    tabla = DemografiaAnual.__table__
    comprobar([c.name for c in tabla.primary_key.columns] == ["codigo_ine", "anio"],
              "clave primaria compuesta (codigo_ine, anio)")
    nulables = {c.name: c.nullable for c in tabla.columns}
    comprobar(not nulables["poblacion"] and nulables["poblacion_mayor_65"]
              and nulables["poblacion_menor_15"] and nulables["tasa_envejecimiento"],
              "poblacion NOT NULL; las 3 columnas de edad admiten NULL")
    fk = next(iter(tabla.c.codigo_ine.foreign_keys))
    comprobar(fk.target_fullname == "municipios.codigo_ine" and fk.ondelete == "CASCADE",
              "FK → municipios.codigo_ine ON DELETE CASCADE")

    async with Session() as db:
        filas = (await db.execute(
            select(DemografiaAnual).where(DemografiaAnual.codigo_ine == "28069").order_by(DemografiaAnual.anio)
        )).scalars().all()
    comprobar(len(filas) == 11 and filas[0].anio == 2015 and filas[0].poblacion == 54,
              "lectura ORM de 28069", f"{len(filas)} filas, 2015 = {filas[0].poblacion if filas else '-'}")
    comprobar(all(f.poblacion_mayor_65 is None and f.tasa_envejecimiento is None for f in filas),
              "edades leídas como None")
    punto = DemografiaPuntoAnualSchema.model_validate(filas[-1])
    comprobar(punto.anio == 2025 and punto.poblacion == 88 and punto.poblacion_mayor_65 is None,
              "DemografiaPuntoAnualSchema desde objeto ORM (from_attributes)", repr(punto))


async def probar_servicio(Session) -> None:
    print("\n== 3. Ingesta bajo demanda ==")
    async with Session() as db:
        n = (await db.execute(text("SELECT count(*) FROM demografia_anual"))).scalar()
        comprobar(n == 0, "tabla vacía al empezar", f"{n} filas")

        # Mientras se descarga del INE, una tarea "reloj" sigue contando cada 20 ms.
        # Si la ingesta bloqueara el event loop, el reloj se quedaría parado.
        ticks = 0
        async def reloj():
            nonlocal ticks
            while True:
                await asyncio.sleep(0.02)
                ticks += 1
        tarea = asyncio.create_task(reloj())
        insertados = await p2.hydrate_demografia_on_demand(db, "28069")
        tarea.cancel()
        comprobar(insertados == 11, "28069 no estaba → se descarga e inserta", f"{insertados} filas")
        comprobar(ticks >= 5, "el event loop sigue libre durante la descarga (asyncio.to_thread)",
                  f"{ticks} ticks del reloj")

        n = (await db.execute(text("SELECT count(*) FROM demografia_anual WHERE codigo_ine='28069'"))).scalar()
        comprobar(n == 11, "las filas se ven desde la sesión async (commit de psycopg2)", f"{n} filas")
        comprobar(await p2.hydrate_demografia_on_demand(db, "28069") == 0,
                  "segunda llamada → 0 (ya está en BD, no se llama al INE)")
        comprobar(await p2.hydrate_demografia_on_demand(db, "28070") == 0,
                  "código que no está en municipios → 0, sin excepción")

    await probar_orm(Session)

    print("\n== 4. get_demografia_serie_by_municipio ==")
    async with Session() as db:
        d = await p2.get_demografia_serie_by_municipio(
            db, "28027", cobertura_fibra_pct=87.5, num_ayudas_abiertas=3
        )
    comprobar(d is not None, "28027 se hidrata automáticamente dentro de la llamada")
    s = DemografiaSerieResponseSchema(**d)
    print(f"     → {s.nombre}: {s.poblacion_inicial_10a} → {s.poblacion_actual}, "
          f"var_10a={s.variacion_10a_pct}%, var_5a={d['variacion_5a_pct']}%, "
          f"{d['inercia_demografica']}, masa crítica={d['preserva_masa_critica']}")
    comprobar(s.nombre == "Buitrago del Lozoya" and len(s.serie_anual) == 11, "nombre y 11 puntos")
    comprobar(s.poblacion_inicial_10a == 1865 and s.poblacion_actual == 2034 and s.variacion_10a_pct == 9.06,
              "valores de 2015 y 2025 y var_10a")
    comprobar([p.anio for p in s.serie_anual] == list(range(2015, 2026)), "serie ordenada 2015→2025")
    comprobar(all(p.poblacion_mayor_65 is None and p.tasa_envejecimiento is None for p in s.serie_anual),
              "edades None en toda la serie")
    comprobar(s.cobertura_fibra_pct == 87.5 and s.num_ayudas_abiertas == 3 and s.distancia_urgencias_km is None,
              "campos de P1/P3/P4 se pasan tal cual (lo no pasado queda None)")

    async with Session() as db:
        comprobar(await p2.get_demografia_serie_by_municipio(db, "28070") is None,
                  "código fuera de municipios → None (main.py puede devolver 404)")

    print("\n== 5. get_demografia_summary_all ==")
    async with Session() as db:
        await p2.hydrate_demografia_on_demand(db, "28078")
        resumen = await p2.get_demografia_summary_all(db)
    for codigo, r in resumen.items():
        print(f"     {codigo}: {r['poblacion_inicial_10a']} → {r['poblacion_actual']}  "
              f"var_10a={r['variacion_10a_pct']}  var_5a={r['variacion_5a_pct']}  "
              f"{r['inercia_demografica']}  masa={r['preserva_masa_critica']}")
    comprobar(sorted(resumen) == ["28027", "28069", "28078"], "incluye solo los 3 municipios hidratados")
    comprobar(resumen["28027"]["variacion_10a_pct"] == d["variacion_10a_pct"]
              and resumen["28027"]["inercia_demografica"] == d["inercia_demografica"],
              "summary_all y serie_by_municipio dan el mismo resultado")

    print("\n== 6. Año ausente (se borra 2015 de 28027 en la BD de prueba) ==")
    async with Session() as db:
        await db.execute(text("DELETE FROM demografia_anual WHERE codigo_ine='28027' AND anio=2015"))
        await db.commit()
        r = (await p2.get_demografia_summary_all(db))["28027"]
        d2 = await p2.get_demografia_serie_by_municipio(db, "28027")
    comprobar(r["variacion_10a_pct"] is None and r["inercia_demografica"] == p2.SIN_DATOS
              and r["variacion_5a_pct"] is not None,
              "summary_all: var_10a None → SIN_DATOS, var_5a se sigue calculando", str(r["variacion_5a_pct"]))
    s2 = DemografiaSerieResponseSchema(**d2)
    comprobar(s2.poblacion_inicial_10a is None and s2.variacion_10a_pct is None and len(s2.serie_anual) == 10,
              "serie_by_municipio: no se rehidrata (ya hay filas) y el schema acepta None")


async def main() -> None:
    probar_clasificacion()

    engine = create_async_engine(URL_ASYNC)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        await preparar_bd(engine)
        await probar_servicio(Session)
    finally:
        await engine.dispose()

    fallos = [d for ok, d in RESULTADOS if not ok]
    print(f"\n== Resultado: {len(RESULTADOS) - len(fallos)}/{len(RESULTADOS)} comprobaciones OK ==")
    for d in fallos:
        print(f"  FAIL: {d}")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    asyncio.run(main())
