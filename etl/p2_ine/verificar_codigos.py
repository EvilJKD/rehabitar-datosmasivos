#!/usr/bin/env python3
"""
Verificación de códigos INE de municipios (solo lectura).

Comprueba con los datos reales de la tabla 2881 (INE Tempus) si los códigos de municipio y los
nombres que aparecen en el repo cuadran entre sí.
El script es de solo lectura: descarga datos del INE, lee ficheros del repo e imprime por pantalla.
No modifica ningún fichero ni se conecta a la base de datos.

Uso:
    python etl/p2_ine/verificar_codigos.py              # imprime la comprobación (tablas Markdown)
    python etl/p2_ine/verificar_codigos.py --todos      # además lista todos los municipios de Madrid «código → nombre»
    python etl/p2_ine/verificar_codigos.py > codigos.md # lo guarda en un fichero para pasarlo al grupo
"""

import argparse
import re
import unicodedata
from pathlib import Path

# Está en la misma carpeta que etl_ine.py, así que reutilizamos su función de descarga (que también pide solo la tabla 2881)
from etl_ine import TABLA_POBLACION_TOTAL, _download_tabla

RAIZ_REPO = Path(__file__).resolve().parents[2]
CARPETAS_IGNORADAS = {".git", ".venv", "venv", "node_modules", "__pycache__"}
EXTENSIONES = {".py", ".md", ".yml", ".yaml", ".js", ".html", ".sql", ".json", ".txt", ".env", ".example"}

# Código de municipio de Madrid: 5 dígitos que empiezan por 28, sin otro dígito pegado delante ni detrás
PATRON_CODIGO = re.compile(r"(?<!\d)28\d{3}(?!\d)")


def _normalizar(texto: str) -> str:
    """Pasa a minúsculas y quita tildes, para que 'Robledillo' y 'robledillo' coincidan."""
    sin_tildes = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").lower()


def _variantes(nombre_ine: str) -> list[str]:
    """
    El INE pone el artículo al final: 'Hiruela, La'. Lo normal es escribir 'La Hiruela'. Buscamos las dos formas.
    """
    variantes = [nombre_ine]
    m = re.fullmatch(r"(.+), (La|El|Los|Las)", nombre_ine)
    if m:
        variantes.append(f"{m.group(2)} {m.group(1)}")
    return variantes


def municipios_desde_ine() -> dict[str, str]:
    """Saca {código: nombre} de la tabla 2881, quedándose solo con la serie Sexo=Total para no duplicar."""
    municipios: dict[str, str] = {}
    for serie in _download_tabla(TABLA_POBLACION_TOTAL):
        for md in serie.get("MetaData") or []:
            if md.get("T3_Variable") == "Municipios":
                municipios[str(md["Codigo"])] = str(md["Nombre"])
    return dict(sorted(municipios.items()))


def _archivos_repo():
    for ruta in RAIZ_REPO.rglob("*"):
        # Saltamos los entornos virtuales (.venv, .venv-1...), la carpeta de git y este mismo script
        if any(parte in CARPETAS_IGNORADAS or parte.startswith(".venv") for parte in ruta.parts):
            continue
        if ruta == Path(__file__).resolve():
            continue
        if ruta.is_file() and (ruta.suffix in EXTENSIONES or ruta.name.startswith(".env")):
            yield ruta


def _nombres_en_linea(linea: str, patrones: list[tuple[re.Pattern, str]]) -> list[str]:
    """
    Devuelve los códigos de los municipios que se nombran en esta línea (buscando por nombre).
    Se da prioridad a los nombres más largos, para que 'Buitrago del Lozoya' no se confunda con 'Lozoya'.
    """
    texto = _normalizar(linea)
    ocupado = [False] * len(texto)
    encontrados: list[str] = []
    for patron, codigo in patrones:   # patrones ya viene ordenado de más largo a más corto
        for m in patron.finditer(texto):
            if any(ocupado[m.start():m.end()]):
                continue
            ocupado[m.start():m.end()] = [True] * (m.end() - m.start())
            if codigo not in encontrados:
                encontrados.append(codigo)
    return encontrados


def main() -> None:
    parser = argparse.ArgumentParser(description="Verificar códigos INE usados en el repositorio")
    parser.add_argument("--todos", action="store_true",
                        help="Listar también todos los municipios de Madrid (código → nombre)")
    args = parser.parse_args()

    municipios = municipios_desde_ine()

    # Una regex por cada variante del nombre. 'Madrid' sale por todas partes (Comunidad de Madrid, etc.), así que no lo usamos para buscar.
    patrones = []
    for codigo, nombre in municipios.items():
        if nombre == "Madrid":
            continue
        for v in _variantes(nombre):
            patrones.append((re.compile(rf"(?<!\w){re.escape(_normalizar(v))}(?!\w)"), codigo))
    patrones.sort(key=lambda p: len(p[0].pattern), reverse=True)

    filas_codigos = []   # códigos que aparecen en el repo
    nombres_sueltos = {} # nombre de municipio en el repo → dónde aparece
    for ruta in _archivos_repo():
        try:
            lineas = ruta.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        rel = ruta.relative_to(RAIZ_REPO)
        nombres_por_linea = [_nombres_en_linea(l, patrones) for l in lineas]
        for i, linea in enumerate(lineas):
            for c in nombres_por_linea[i]:
                nombres_sueltos.setdefault(c, []).append(f"{rel}:{i + 1}")
            # A menudo el nombre va en la línea de antes o de después del código, así que miramos una línea por cada lado
            cercanos = []
            for j in (i, i - 1, i + 1):
                if 0 <= j < len(lineas):
                    cercanos += [c for c in nombres_por_linea[j] if c not in cercanos]
            for codigo in sorted(set(PATRON_CODIGO.findall(linea))):
                filas_codigos.append((f"{rel}:{i + 1}", codigo, cercanos))

    print(f"# Verificación de códigos INE (fuente: INE Tempus, tabla {TABLA_POBLACION_TOTAL})\n")
    print(f"Municipios de Madrid en la tabla: {len(municipios)}\n")

    print("## 1. Códigos que aparecen en el repositorio\n")
    print("| Ubicación | Código en el repo | Nombre según INE | Municipios nombrados cerca (±1 línea) | Estado |")
    print("|---|---|---|---|---|")
    for ubicacion, codigo, nombres in filas_codigos:
        nombre_ine = municipios.get(codigo, "— (no existe en la tabla)")
        mencionados = ", ".join(f"{municipios[c]} ({c})" for c in nombres) or "—"
        if codigo not in municipios:
            estado = "❌ código inexistente"
        elif not nombres:
            estado = "sin nombre cerca"
        elif codigo in nombres:
            estado = "✅ coincide"
        else:
            estado = "❌ no coincide"
        print(f"| `{ubicacion}` | {codigo} | {nombre_ine} | {mencionados} | {estado} |")

    print("\n## 2. Municipios nombrados en el repositorio y su código INE correcto\n")
    print("| Código INE | Nombre INE | Apariciones |")
    print("|---|---|---|")
    for codigo in sorted(nombres_sueltos):
        lugares = nombres_sueltos[codigo]
        resumen = ", ".join(f"`{l}`" for l in lugares[:4]) + (f" (+{len(lugares) - 4})" if len(lugares) > 4 else "")
        print(f"| {codigo} | {municipios[codigo]} | {resumen} |")

    if args.todos:
        print("\n## 3. Todos los municipios de la Comunidad de Madrid\n")
        print("| Código INE | Nombre INE |")
        print("|---|---|")
        for codigo, nombre in municipios.items():
            print(f"| {codigo} | {nombre} |")


if __name__ == "__main__":
    main()
