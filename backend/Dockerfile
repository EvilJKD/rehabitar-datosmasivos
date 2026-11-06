# =============================================================================
# Dockerfile para Backend FastAPI + Frontend Web Estatico (LISTO PARA USAR)
# Nota: Se construye desde el contexto raiz (.) en docker-compose.yml
# =============================================================================
FROM python:3.11-slim

LABEL maintainer="Equipo Re-Habitar - Master en Informatica"
LABEL description="Servidor FastAPI + Motor WLC + Frontend Interactivo en puerto 8000"

WORKDIR /app/backend

# Instalacion de dependencias del backend (FastAPI, Uvicorn, SQLAlchemy, asyncpg, httpx)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia del codigo del backend y de los archivos estaticos del frontend
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
