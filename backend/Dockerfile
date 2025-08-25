# Multi-stage Docker build for FastAPI backend
FROM python:3.12-slim as base

# Set environment variables for optimal performance
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install system dependencies with minimal packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libpq-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app user for security
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser

# Set working directory
WORKDIR /app

# Install Poetry with timeout and retry settings
RUN pip install --no-cache-dir --timeout=300 poetry==1.6.1

# Copy dependency files first for better Docker layer caching
COPY pyproject.toml poetry.lock ./

# Configure poetry for production and install dependencies with timeout
RUN poetry config virtualenvs.create false \
    && poetry config installer.max-workers 10 \
    && poetry config installer.modern-installation false \
    && poetry install --only=main --no-interaction --no-ansi --timeout=600 \
    && rm -rf $POETRY_CACHE_DIR

# Development stage
FROM base as development

# Install development dependencies
RUN poetry install --no-interaction --no-ansi

# Copy application code
COPY . .

# Change ownership to app user
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Development command with reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# Production stage - Optimized for App Runner
FROM base as production

# Copy application code excluding unnecessary files
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser gunicorn.conf.py ./

# Remove development files and caches for smaller image
RUN find /app -name "*.pyc" -delete \
    && find /app -name "__pycache__" -type d -exec rm -rf {} + \
    && find /app -name ".pytest_cache" -type d -exec rm -rf {} + \
    && find /app -name "*.pyo" -delete

# Switch to non-root user for security
USER appuser

# Health check optimized for App Runner
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Production command optimized for App Runner (single worker for better resource management)
CMD ["gunicorn", "app.main:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--timeout", "120", "--keepalive", "2", "--max-requests", "1000", "--max-requests-jitter", "100", "--preload", "--access-logfile", "-", "--error-logfile", "-"]