#!/usr/bin/env python3
"""
Análisis offline de la Consulta 3 sobre todos los municipios de Madrid con la tabla 2881
del INE (no hace falta base de datos).

Los cálculos reutilizan tal cual calcular_indicadores() de backend/services/p2_demo_service.py,
así que los resultados siguen el mismo criterio que la API del backend. Solo lectura: se limita
a descargar los datos del INE e imprimirlos.

    python etl/p2_ine/analisis_179.py
"""

import statistics
import sys
import unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))

from etl_ine import TABLA_POBLACION_TOTAL, fetch_ine_series_api  # noqa: E402
from services import p2_demo_service as p2  # noqa: E402
from verificar_codigos import municipios_desde_ine  # noqa: E402

# Códigos que aparecen de verdad en el repo (28070 es el que se tomó por error como La Hiruela)
CODIGOS_REPO = ["28069", "28027", "28078", "28070"]

# ⚠️ POR VERIFICAR: lista habitual de los 42 municipios de la Sierra Norte, hecha de memoria,
# no sale de la tabla 2881 del INE (la 2881 no tiene dimensión de comarca). El ámbito oficial
# debe tomarse de los datos de P1 (municipios.comarca).
SIERRA_NORTE_POR_VERIFICAR = [
    "La Acebeda", "Alameda del Valle", "El Atazar", "El Berrueco", "Berzosa del Lozoya",
    "Braojos", "Buitrago del Lozoya", "Bustarviejo", "Cabanillas de la Sierra", "La Cabrera",
    "Canencia", "Cervera de Buitrago", "Garganta de los Montes",
    "Gargantilla del Lozoya y Pinilla de Buitrago", "Gascones", "La Hiruela",
    "Horcajo de la Sierra-Aoslos", "Horcajuelo de la Sierra", "Lozoya",
    "Lozoyuela-Navas-Sieteiglesias", "Madarcos", "Montejo de la Sierra", "Navalafuente",
    "Navarredonda y San Mamés", "Patones", "Pinilla del Valle", "Piñuécar-Gandullas",
    "Prádena del Rincón", "Puebla de la Sierra", "Puentes Viejas", "Rascafría", "Redueña",
    "Robledillo de la Jara", "Robregordo", "La Serna del Monte", "Somosierra", "Torrelaguna",
    "Torremocha de Jarama", "Valdemanco", "El Vellón", "Venturada", "Villavieja del Lozoya",
]

ORDEN_ETIQUETAS = [p2.COLAPSO, p2.DECLIVE, p2.REPUNTE_RECIENTE, p2.ESTANCAMIENTO,
                   p2.RECUPERACION, p2.SIN_DATOS]


def _norm(nombre: str) -> str:
    """Normaliza 'Hiruela, La' y 'La Hiruela' a la misma clave: sin tildes, en minúsculas y con el artículo delante."""
    if ", " in nombre:
        base, articulo = nombre.rsplit(", ", 1)
        nombre = f"{articulo} {base}"
    sin = unicodedata.normalize("NFD", nombre)
    return "".join(c for c in sin if unicodedata.category(c) != "Mn").lower()


def _fmt(v) -> str:
    return "—" if v is None else (f"{v:+.2f}%" if isinstance(v, float) else str(v))


def main() -> None:
    nombres = municipios_desde_ine()
    filas = fetch_ine_series_api(None)          # todos los municipios de Madrid, una fila por municipio y año

    series: dict[str, dict[int, int]] = {}
    for f in filas:
        series.setdefault(f["codigo_ine"], {})[f["anio"]] = f["poblacion"]

    resultados = {c: p2.calcular_indicadores(s) for c, s in sorted(series.items())}
    n = len(resultados)

    print(f"# Consulta 3 sobre los {n} municipios de la Comunidad de Madrid (INE tabla {TABLA_POBLACION_TOTAL})\n")
    anios = Counter(r["anio_actual"] for r in resultados.values())
    print(f"Año actual usado: {dict(anios)}  ·  municipios sin dato a 10 años: "
          f"{sum(r['variacion_10a_pct'] is None for r in resultados.values())}\n")

    # ---- 1. Cuántos municipios caen en cada etiqueta ----
    print("## 1. Municipios por etiqueta\n")
    print("| Etiqueta | Municipios | % | con masa crítica (≥100 hab) | sin masa crítica |")
    print("|---|---:|---:|---:|---:|")
    conteo = Counter(r["inercia_demografica"] for r in resultados.values())
    for e in ORDEN_ETIQUETAS:
        con = sum(1 for r in resultados.values() if r["inercia_demografica"] == e and r["preserva_masa_critica"])
        print(f"| {e} | {conteo[e]} | {conteo[e] / n * 100:.1f}% | {con} | {conteo[e] - con} |")
    masa = sum(r["preserva_masa_critica"] for r in resultados.values())
    print(f"| **Total** | **{n}** | 100% | {masa} | {n - masa} |")

    # ---- 2. Estadísticas para valorar los umbrales ----
    print("\n## 2. Datos para valorar los umbrales\n")
    v10 = sorted(r["variacion_10a_pct"] for r in resultados.values() if r["variacion_10a_pct"] is not None)
    cuart = statistics.quantiles(v10, n=4)
    print(f"- var_10a: mín {v10[0]:+.2f}% · Q1 {cuart[0]:+.2f}% · mediana {cuart[1]:+.2f}% · "
          f"Q3 {cuart[2]:+.2f}% · máx {v10[-1]:+.2f}%")
    print(f"- var_10a < 0 (pierden población en 10 años): {sum(v < 0 for v in v10)}")
    print(f"- var_10a ≤ -20%: {sum(v <= p2.UMBRAL_COLAPSO_PCT for v in v10)}")
    pequenos = [r for r in resultados.values() if r["poblacion_actual"] < p2.POBLACION_MINIMA_COLAPSO]
    print(f"- municipios con < {p2.POBLACION_MINIMA_COLAPSO} hab: {len(pequenos)} "
          f"(de ellos bajando a 10 años: {sum((r['variacion_10a_pct'] or 0) < 0 for r in pequenos)})")
    no_cubierto = [c for c, r in resultados.items()
                   if r["variacion_10a_pct"] is not None and r["variacion_10a_pct"] >= p2.UMBRAL_CRECIMIENTO_PCT
                   and not (r["variacion_5a_pct"] is not None and r["variacion_5a_pct"] > 0)]
    detalle = [
        f"{nombres[c]} {_fmt(resultados[c]['variacion_10a_pct'])} / {_fmt(resultados[c]['variacion_5a_pct'])}"
        for c in no_cubierto
    ]
    print(f"- caso no cubierto (var_10a ≥ +5% pero var_5a ≤ 0) → ESTANCAMIENTO: {len(no_cubierto)}"
          + (f" ({'; '.join(detalle)})" if detalle else ""))
    exactos = [nombres[c] for c, r in resultados.items() if r["poblacion_actual"] == 100]
    print(f"- municipios con exactamente 100 hab (donde ≥100 y >100 difieren): {len(exactos)}"
          + (f" ({', '.join(exactos)})" if exactos else ""))

    # ---- 3. Municipios que aparecen en el repo ----
    def tabla(codigos):
        print("| Código | Municipio | 2015 | 2020 | 2025 | var_10a | var_5a | Etiqueta | Masa crítica |")
        print("|---|---|---:|---:|---:|---:|---:|---|---|")
        for c in codigos:
            r = resultados[c]
            print(f"| {c} | {nombres[c]} | {_fmt(r['poblacion_inicial_10a'])} | {_fmt(r['poblacion_5a'])} | "
                  f"{r['poblacion_actual']} | {_fmt(r['variacion_10a_pct'])} | {_fmt(r['variacion_5a_pct'])} | "
                  f"{r['inercia_demografica']} | {'sí' if r['preserva_masa_critica'] else 'no'} |")

    print("\n## 3. Municipios que aparecen en el repositorio\n")
    tabla(CODIGOS_REPO)

    # ---- 4. Sierra Norte (lista pendiente de verificar) ----
    por_nombre = {_norm(nombre): c for c, nombre in nombres.items()}
    sierra = [por_nombre[_norm(x)] for x in SIERRA_NORTE_POR_VERIFICAR if _norm(x) in por_nombre]
    sin_match = [x for x in SIERRA_NORTE_POR_VERIFICAR if _norm(x) not in por_nombre]
    print(f"\n## 4. Sierra Norte (lista POR VERIFICAR, {len(sierra)} de {len(SIERRA_NORTE_POR_VERIFICAR)} "
          f"nombres encontrados en la tabla INE)\n")
    if sin_match:
        print(f"Nombres sin coincidencia en el INE: {', '.join(sin_match)}\n")
    tabla(sorted(sierra))
    c_sierra = Counter(resultados[c]["inercia_demografica"] for c in sierra)
    print("\nResumen Sierra Norte: " + " · ".join(f"{e} {c_sierra[e]}" for e in ORDEN_ETIQUETAS if c_sierra[e])
          + f" · con masa crítica {sum(resultados[c]['preserva_masa_critica'] for c in sierra)}/{len(sierra)}")


if __name__ == "__main__":
    main()
