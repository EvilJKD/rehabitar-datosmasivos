# =============================================================================
# Dockerfile para Backend FastAPI + Ingesta Hibrida + Frontend Web (LISTO PARA USAR)
# Nota: Se construye desde el contexto raiz (.) en docker-compose.yml
# =============================================================================
FROM python:3.11-slim

LABEL maintainer="Equipo Re-Habitar - Master en Informatica"
LABEL description="Servidor FastAPI con Ingesta Hibrida (Batch + Bajo Demanda), Motor WLC y Frontend"

WORKDIR /app/backend

# Dependencias del sistema para drivers PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalacion de dependencias de Backend y ETL (para ingesta hibrida bajo demanda)
COPY etl/requirements.txt /tmp/etl_requirements.txt
COPY backend/requirements.txt /tmp/backend_requirements.txt
RUN pip install --no-cache-dir -r /tmp/etl_requirements.txt -r /tmp/backend_requirements.txt

# Copia de modulos ETL (incluyendo data/raw para fallback bajo demanda), Backend y Frontend
COPY etl/ /app/etl/
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

ENV PYTHONPATH=/app/backend:/app/etl
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
