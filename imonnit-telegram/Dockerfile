FROM python:3.12-slim

# Instalar dependencias para WeasyPrint y psycopg2
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    fonts-dejavu-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip
COPY pyproject.toml .
RUN pip install -e .

COPY alembic.ini .
COPY migrations/ migrations/
COPY scripts/ scripts/
COPY app/ app/

RUN useradd -m appuser
USER appuser

# Esperar a la BD, correr migraciones y levantar Uvicorn
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
