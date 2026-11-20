#!/usr/bin/env bash
# =============================================================================
# Prueba local completa de P2: un solo comando que ejecuta toda la parte de P2 desde cero
#
# Uso:
#   tests/run_local_test.sh          # al terminar borra automáticamente la BD temporal
#   tests/run_local_test.sh --keep   # al terminar deja la BD temporal para mirarla con psql
#
# Qué hace (cada paso imprime «[n/9] ...»):
#   1. Comprueba Docker               2. Para el p2_test anterior   3. Arranca un PostgreSQL temporal
#   4. Crea la tabla municipios temporal  5. Ejecuta el bloque SQL de P2 de schema.sql
#   6. Ejecuta el ETL (28069, 28027)  7. Imprime demografia_anual   8. Ejecuta probar_p2_backend.py
#   9. Limpieza (o, con --keep, deja el contenedor y muestra cómo conectarse)
#
# Seguridad: solo usa un contenedor temporal p2_test (puerto 5433, --rm, sin volume);
# no toca el docker compose del grupo, ni rehabitar_pgdata, ni el puerto 5432.
# =============================================================================

# -----------------------------------------------------------------------------
# [Qué significa set -euo pipefail]
#   -e         Si cualquier comando falla (código de salida distinto de 0), el script se corta
#              en el acto en vez de seguir adelante arrastrando el error.
#              Excepción: los comandos dentro de la condición de un if / while, o recogidos
#              con ||, no provocan la salida aunque fallen.
#   -u         Usar una variable que no se ha definido es un error y el script sale
#              (evita que una errata en el nombre se convierta en una cadena vacía sin avisar).
#   -o pipefail  En una tubería a | b, basta con que falle un comando para que falle toda la tubería
#              (por defecto solo cuenta el resultado del último, b).
# -----------------------------------------------------------------------------
set -euo pipefail

# ---------------------------- Configuración ----------------------------
CONTENEDOR="p2_test"
IMAGEN="postgres:15"
PUERTO="5433"
PG_USER="rehabitar"
PG_PASSWORD="rehabitar_pwd"
PG_DB="rehabitar_db"
ESPERA_MAX=60          # segundos máximos de espera hasta que la BD esté lista
FILAS_ESPERADAS=22     # 28069 + 28027, 11 años cada uno (2015–2025)

# Localizar la raíz del repo: este script vive en <raíz>/tests/, así que subiendo un nivel llegamos.
# BASH_SOURCE[0] es la ruta del propio script; da igual desde qué carpeta se lance, el resultado es el mismo.
# La ruta lleva caracteres chinos y espacios, por eso todas las variables van entre comillas dobles "...";
# si no, la shell partiría "Datos Masivos y Encadenados" por los espacios en varios argumentos.
# Además: si justo detrás de una variable va un carácter no ASCII (chino, una letra con tilde...),
# hay que escribirla como ${VARIABLE} (con llaves), por ejemplo "${IMAGEN}, puerto".
# Sin llaves, el bash 3.2 de macOS toma los bytes de ese carácter como parte del nombre y da unbound variable.
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCHEMA_SQL="$RAIZ/db/schema.sql"
PYTHON="$RAIZ/.venv/bin/python"
ETL="$RAIZ/etl/p2_ine/etl_ine.py"
PRUEBAS="$RAIZ/tests/probar_p2_backend.py"

# ---------------------------- Argumentos ----------------------------
KEEP=0
for arg in "$@"; do
    case "$arg" in
        --keep) KEEP=1 ;;
        -h|--help)
            sed -n '2,17p' "$0"    # imprime la explicación de la cabecera del fichero
            exit 0 ;;
        *)
            echo "Argumento no reconocido: ${arg} (opciones: --keep, --help)" >&2
            exit 2 ;;
    esac
done

# ---------------------------- Funciones auxiliares ----------------------------
paso() { echo; echo "[$1/9] $2"; }

# Ejecuta psql dentro del contenedor. -v ON_ERROR_STOP=1: si el SQL falla, psql devuelve distinto de 0
# y, junto con set -e, el script se para.
# "$@" pasa tal cual todos los argumentos que recibe psql_c (cada uno entero, sin partirse por espacios).
psql_c() {
    docker exec -i "$CONTENEDOR" psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$PG_DB" "$@"
}

contenedor_existe() {
    # docker ps -a lista todos los contenedores (también los parados); grep -qx busca la línea exacta y -q no imprime nada, solo devuelve el resultado
    docker ps -a --format '{{.Names}}' | grep -qx "$CONTENEDOR"
}

detener_contenedor() {
    if contenedor_existe; then
        docker stop "$CONTENEDOR" >/dev/null
        # Un contenedor con --rm se borra solo al pararlo, pero el borrado es asíncrono: esperamos
        # a que desaparezca de verdad, porque si no, un docker run inmediato con el mismo nombre
        # falla con «el nombre ya está en uso»
        for _ in $(seq 1 20); do
            contenedor_existe || return 0
            sleep 0.5
        done
    fi
}

# ---------------------------- trap: limpieza garantizada ----------------------------
# [Qué es trap]
#   trap 'comando' señal : cuando el script recibe esa «señal», ejecuta antes ese comando.
#   EXIT es una señal especial de bash: salta siempre que el script termina, sea como sea
#   (termina normal, set -e lo corta por un error o se llama a exit). Por eso la limpieza va aquí:
#   aunque algo falle a medias, no se queda sin hacer.
#   INT es Ctrl+C y TERM es un kill; aquí las convertimos en exit para que también pasen por la limpieza de EXIT.
CONTENEDOR_INICIADO=0
TERMINADO=0             # solo se pone a 1 en la última línea del flujo principal
limpiar() {
    local codigo=$?     # tiene que ir en la primera línea: $? es el código de salida del script y cualquier comando posterior lo machaca
    # Trampa del bash 3.2 que trae macOS: si el script sale por set -u (variable sin definir), aquí $? puede llegar como 0.
    # Así que no basta con mirar $?: si el flujo principal no llegó a su última línea, lo tratamos siempre como fallo.
    if [[ "$TERMINADO" != 1 && "$codigo" == 0 ]]; then
        codigo=1
    fi
    if [[ "$CONTENEDOR_INICIADO" == 1 ]]; then
        if [[ "$KEEP" == 1 && "$codigo" == 0 ]]; then
            echo
            echo "[9/9] --keep: se mantiene el contenedor ${CONTENEDOR}; los datos son los que se imprimieron en el paso 7."
            echo "  Para entrar en la base de datos (no hace falta tener psql instalado en el equipo):"
            echo "    docker exec -it $CONTENEDOR psql -U $PG_USER -d $PG_DB"
            echo "  O conéctate con un cliente local (VS Code, DBeaver, psql, etc.):"
            echo "    postgresql://$PG_USER:$PG_PASSWORD@localhost:$PUERTO/$PG_DB"
            echo "  Cuando acabes, páralo a mano (se lanzó con --rm, así que al pararlo se borra sin dejar datos):"
            echo "    docker stop $CONTENEDOR"
        else
            echo
            if [[ "$codigo" != 0 ]]; then
                echo "✗ Salida con error (código ${codigo}), limpiando el contenedor $CONTENEDOR ..."
            else
                echo "[9/9] Parando y borrando el contenedor temporal $CONTENEDOR ..."
            fi
            detener_contenedor || true   # si la propia limpieza falla, que no dé otro error
            echo "  Limpieza hecha."
        fi
    fi
    [[ "$codigo" == 0 ]] && echo && echo "✓ Prueba local de P2 completada."
    exit "$codigo"
}
trap limpiar EXIT
trap 'exit 130' INT TERM

# ---------------------------- Funciones de los pasos 4–6 (con --keep se vuelven a usar tras el paso 8) ----------------------------
crear_municipios() {
    # [Qué es un heredoc]
    #   comando <<'SQL' ... SQL : las líneas entre las dos marcas SQL se pasan como entrada estándar del comando.
    #   Es como «darle de comer» ese texto a psql, igual que si lo tecleáramos dentro de psql.
    #   Poner la marca entre comillas simples ('SQL') hace que el contenido pase tal cual:
    #   la shell no sustituye $variables ni ejecuta `comandos`. La marca de cierre SQL tiene que ir sola en su línea, sin sangría.
    psql_c -q <<'SQL'
-- Tabla temporal de prueba: solo existe para satisfacer la FK de demografia_anual, no es la definición oficial de P1
-- Ocultamos los NOTICE (DROP IF EXISTS avisa "does not exist, skipping" si la tabla no existe; no es un error)
SET client_min_messages = warning;
DROP TABLE IF EXISTS demografia_anual;
DROP TABLE IF EXISTS municipios;
CREATE TABLE municipios (
    codigo_ine VARCHAR(5)   PRIMARY KEY,
    nombre     VARCHAR(120) NOT NULL
);
INSERT INTO municipios (codigo_ine, nombre) VALUES
    ('28069', 'La Hiruela'),
    ('28027', 'Buitrago del Lozoya'),
    ('28078', 'Madarcos');
SQL
    psql_c -At -c "SELECT '  municipios: ' || string_agg(codigo_ine || ' ' || nombre, ', ' ORDER BY codigo_ine) FROM municipios"
}

extraer_paso3() {
    # Saca el bloque SQL de P2 de db/schema.sql (no lo duplicamos en el script: si cambia schema.sql, esto cambia con él).
    # awk lee el fichero línea a línea:
    #   /^CREATE TABLE IF NOT EXISTS demografia_anual/{p=1}  al llegar a la línea del CREATE TABLE, activa el interruptor p
    #   p{print}                                              mientras p está activo, imprime la línea tal cual
    #   /^CREATE INDEX IF NOT EXISTS idx_demografia_anio_codigo/{exit}  tras imprimir la línea del índice, termina
    # Es decir: coge desde «CREATE TABLE ... demografia_anual» hasta «CREATE INDEX ... idx_demografia_anio_codigo».
    # Las dos marcas son el comienzo fijo del bloque de P2 en schema.sql; si se edita schema.sql, hay que conservar cómo empiezan esas dos líneas.
    awk '/^CREATE TABLE IF NOT EXISTS demografia_anual/{p=1}
         p{print}
         /^CREATE INDEX IF NOT EXISTS idx_demografia_anio_codigo/{exit}' "$SCHEMA_SQL"
}

crear_demografia() {
    local sql
    sql="$(extraer_paso3)"
    # Comprobamos lo extraído: tiene que incluir el CREATE TABLE y el índice, por si cambia el formato de schema.sql y sale medio bloque sin avisar
    if [[ "$sql" != *"CREATE TABLE IF NOT EXISTS demografia_anual"* || \
          "$sql" != *"idx_demografia_anio_codigo"* ]]; then
        echo "✗ No se ha podido extraer el SQL completo de demografia_anual de ${SCHEMA_SQL}." >&2
        exit 1
    fi
    echo "  Extraídas $(printf '%s\n' "$sql" | wc -l | tr -d ' ') líneas de SQL de schema.sql, ejecutando..."
    # <<< es un here-string: pasa el contenido de una variable como entrada estándar; como un heredoc, pero el texto sale de la variable
    psql_c -q <<< "$sql"
    psql_c -At -c "SELECT '  Creado: ' || string_agg(indexname, ', ') FROM pg_indexes WHERE tablename = 'demografia_anual'"
}

ejecutar_etl() {
    # VAR=valor comando: define la variable de entorno solo para ese comando, sin afectar al resto del script.
    # De paso vaciamos DATABASE_URL_SYNC, por si la tienes definida en tu terminal y el ETL acaba en otra base de datos.
    DATABASE_URL_SYNC="" POSTGRES_HOST=localhost POSTGRES_PORT="$PUERTO" \
        "$PYTHON" "$ETL" 28069 28027
    # Ante un error de red el ETL solo lo registra en el log y devuelve 0 (no para el script), así que contamos las filas para confirmarlo
    local filas
    filas="$(psql_c -At -c "SELECT count(*) FROM demografia_anual")"
    if [[ "$filas" != "$FILAS_ESPERADAS" ]]; then
        echo "✗ demografia_anual tiene $filas filas y se esperaban $FILAS_ESPERADAS (¿ha fallado el acceso al INE?)." >&2
        exit 1
    fi
    echo "  ✓ demografia_anual tiene $filas filas."
}

# =============================================================================
# Flujo principal
# =============================================================================

paso 1 "Comprobando Docker..."
# En una terminal no interactiva puede que el docker de OrbStack no esté en el PATH; añadimos su ruta de instalación por defecto
if ! command -v docker >/dev/null 2>&1 && [[ -x "$HOME/.orbstack/bin/docker" ]]; then
    export PATH="$HOME/.orbstack/bin:$PATH"
fi
if ! command -v docker >/dev/null 2>&1; then
    echo "✗ No se encuentra el comando docker. Instala y abre OrbStack primero." >&2
    exit 1
fi
if ! docker info >/dev/null 2>&1; then
    echo "✗ Docker no está en marcha. Abre OrbStack, espera a que termine de arrancar y vuelve a lanzar este script." >&2
    exit 1
fi
if [[ ! -x "$PYTHON" ]]; then
    echo "✗ No se encuentra ${PYTHON}; crea primero el .venv en la raíz del repo." >&2
    exit 1
fi
echo "  ✓ Docker $(docker version --format '{{.Server.Version}}'), Python: $("$PYTHON" --version)"

paso 2 "Comprobando si ya existe el contenedor ${CONTENEDOR}..."
if contenedor_existe; then
    echo "  Hay un ${CONTENEDOR} anterior, parándolo (se lanzó con --rm, así que se borra al pararse)..."
    detener_contenedor
    echo "  ✓ Parado."
else
    echo "  ✓ No hay contenedor anterior."
fi

paso 3 "Arrancando la BD temporal (${IMAGEN}, puerto ${PUERTO}, --rm, sin volume)..."
# La barra invertida \ al final de la línea significa «el comando no ha terminado, sigue en la línea de abajo»
docker run --rm -d --name "$CONTENEDOR" -p "$PUERTO:5432" \
    -e POSTGRES_USER="$PG_USER" \
    -e POSTGRES_PASSWORD="$PG_PASSWORD" \
    -e POSTGRES_DB="$PG_DB" \
    "$IMAGEN" >/dev/null
CONTENEDOR_INICIADO=1   # a partir de aquí, al salir, el trap sí tiene que limpiar el contenedor

# Por qué -h 127.0.0.1 (por TCP) y no el socket unix por defecto:
#   la primera vez que arranca, la imagen de postgres levanta un «servidor temporal» para crear el usuario
#   y la base de datos, y luego se reinicia. Ese servidor temporal solo escucha en el socket unix, no en TCP.
#   Si comprobáramos por socket, podría salir «listo» durante la fase temporal, reiniciarse justo después
#   y hacer fallar los psql siguientes. Por TCP solo pasa la comprobación cuando ya está el servidor definitivo.
echo -n "  Esperando a que la BD esté lista"
listo=0
for _ in $(seq 1 "$ESPERA_MAX"); do
    if docker exec "$CONTENEDOR" pg_isready -q -h 127.0.0.1 -U "$PG_USER" -d "$PG_DB" 2>/dev/null; then
        listo=1
        break
    fi
    echo -n "."
    sleep 1
done
echo
if [[ "$listo" != 1 ]]; then
    echo "✗ Tras $ESPERA_MAX segundos la BD sigue sin estar lista. Últimas líneas del log:" >&2
    docker logs --tail 20 "$CONTENEDOR" >&2 || true
    exit 1
fi
echo "  ✓ $(psql_c -At -c 'SELECT version()' | cut -d' ' -f1-2) lista."

paso 4 "Creando la tabla municipios temporal (28069, 28027, 28078)..."
crear_municipios

paso 5 "Extrayendo de db/schema.sql y ejecutando el SQL de demografia_anual..."
crear_demografia

paso 6 "Ejecutando el ETL (POSTGRES_PORT=${PUERTO}, 28069 y 28027)..."
ejecutar_etl

paso 7 "Contenido de demografia_anual..."
psql_c -c "
    SELECT d.codigo_ine, m.nombre, d.anio, d.poblacion,
           d.poblacion_mayor_65, d.poblacion_menor_15, d.tasa_envejecimiento
    FROM demografia_anual d JOIN municipios m USING (codigo_ine)
    ORDER BY d.codigo_ine, d.anio"
echo "  (las tres columnas de edad vacías = NULL: de momento no hay fuente de datos por edad)"

paso 8 "Ejecutando probar_p2_backend.py..."
# Ojo: probar_p2_backend.py hace su propio DROP y vuelve a crear municipios y demografia_anual
# (necesita empezar con la tabla vacía para probar la carga bajo demanda), y durante las pruebas borra además el 2015 de 28027.
# Así que machaca los datos de los pasos 4–7, pero no hay conflicto: él mismo deja las tablas preparadas.
# Lee POSTGRES_PORT y se niega a ejecutarse si el puerto no es 5433.
DATABASE_URL_SYNC="" POSTGRES_HOST=localhost POSTGRES_PORT="$PUERTO" "$PYTHON" "$PRUEBAS"

if [[ "$KEEP" == 1 ]]; then
    # Con --keep hay que dejar los datos como en el paso 7; si no, al entrar verías los restos de las pruebas
    echo
    echo "  --keep: repitiendo los pasos 4–6 para dejar la BD con el resultado del ETL..."
    crear_municipios
    crear_demografia
    ejecutar_etl
fi

TERMINADO=1
# El paso 9 (parar el contenedor o, con --keep, mostrar cómo conectarse) se hace en limpiar(), dentro del trap
