# =============================================================================
# Self-RAG Backend — Multi-stage Docker build
# =============================================================================
# Stage 1: install dependencies (cached unless requirements.txt changes)
FROM python:3.12-slim AS base

WORKDIR /app

# System deps for psycopg2 build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: copy application code
FROM base AS app

COPY backend/app ./app

# Why non-root: production best practice — limits blast radius if container is compromised
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Why --no-access-log: uvicorn access logs duplicate what Langfuse traces already capture
# Why no --reload: hot-reload watches the filesystem and wastes resources in production
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
