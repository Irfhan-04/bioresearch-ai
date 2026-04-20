# BioResearch AI — Backend Dockerfile
# Target: Render.com Web Service

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python scripts/generate_training_data.py && python ml/train_scorer.py

ENV CHROMADB_PATH=/app/chromadb_store
RUN mkdir -p /app/chromadb_store

EXPOSE 8000

#CMD ["gunicorn", "app.main:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--workers", "1", "--bind", "0.0.0.0:8000", "--timeout", "0", "--keep-alive", "5", "--graceful-timeout", "30"]

# Alternative start command for debugging (no worker timeout):
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
