# Nitya Dharma — production-safe Docker image
# Additive layer: does not replace existing VPS/Gunicorn deployment.
# Use python-decouple + .env at runtime; no secrets in image.

FROM python:3.11-slim

# Prevent Python from writing pyc and prevent buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Production logging directory (mounted as a Docker volume in compose)
RUN mkdir -p /logs

# Install system deps required for mysqlclient
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code (excluding paths in .dockerignore; .env is not copied)
COPY . .

# Non-root user for Celery worker only (compose sets user: celeryuser on celery_worker; web stays default root)
RUN useradd --system --no-create-home --shell /usr/sbin/nologin celeryuser

# Expose Gunicorn port
EXPOSE 8000

# Gunicorn is intentionally started from docker-compose via `command: ...`.
