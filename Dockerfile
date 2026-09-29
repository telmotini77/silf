FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema para WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no root
RUN useradd -m -d /app user

WORKDIR /app

# Copiar requirements o pyproject (usamos pip standard por simplicidad aquí, pyproject.toml también soportado)
COPY pyproject.toml /app/
RUN mkdir app && touch app/__init__.py && pip install --no-cache-dir .

COPY . /app/

RUN chown -R user:user /app
USER user

# Ejecutar migraciones y luego uvicorn
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
