# Multi-stage Docker build for FastAPI backend
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser

# Set working directory
WORKDIR /app

# Install Poetry
RUN pip install poetry==1.6.1

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure poetry and install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-interaction --no-ansi

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


# Production stage
FROM base as production

# Copy only application code (no dev dependencies)
COPY . .

# Remove development files
RUN rm -f pyproject.toml poetry.lock \
    && find /app -name "*.pyc" -delete \
    && find /app -name "__pycache__" -type d -exec rm -rf {} + \
    && find /app -name ".pytest_cache" -type d -exec rm -rf {} +

# Change ownership to app user
RUN chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Production command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]