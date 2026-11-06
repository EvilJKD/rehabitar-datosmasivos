# =============================================================================
# Dockerfile para el Contenedor Efimero ETL Runner (LISTO PARA USAR)
# =============================================================================
FROM python:3.11-slim

LABEL maintainer="Equipo Re-Habitar - Master en Informatica"
LABEL description="Contenedor efimero que ejecuta secuencialmente los pipelines ETL P1 -> P2 -> P3 -> P4"

WORKDIR /app/etl

# Dependencias del sistema necesarias para psycopg2 y herramientas de red
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalacion de librerias Python del modulo ETL
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia de todos los submodulos ETL (p1_ngbe, p2_ine, p3_cam, p4_bdns) y datos raw
COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "run_all.py"]
