# Lightweight API Dockerfile - No GDAL needed
# API only handles requests and submits jobs to AWS Batch

FROM python:3.10-slim

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y \
    libgeos-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    HOST=0.0.0.0 \
    PORT=8000

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements and create a minimal version for API
WORKDIR /app
COPY requirements.txt .

# Create API-only requirements (exclude heavy geospatial processing libraries)
RUN grep -vE "^(GDAL|rasterio|rioxarray|fiona|xarray|dask)" requirements.txt > requirements-api.txt && \
    pip install --no-cache-dir -r requirements-api.txt && \
    rm requirements-api.txt requirements.txt

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data /app/temp && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser main.py .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI with multiple workers
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
