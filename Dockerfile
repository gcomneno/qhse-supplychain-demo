FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (minime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
COPY app /app/app
COPY worker.py /app/worker.py

EXPOSE 8000

# Command viene impostato da docker-compose per ogni servizio
