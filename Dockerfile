# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Set environment variables for Python in containers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8001

# Create non-root user
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser

WORKDIR /app

# Install dependencies first for better caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app

# Ensure proper file permissions
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose ports for FastAPI (8001) and Streamlit (8501)
EXPOSE 8001 8501

# Default health check against process HTTP liveness endpoint
HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

# Default command launches FastAPI service
CMD ["python", "-m", "uvicorn", "mock_api.app:app", "--host", "0.0.0.0", "--port", "8001"]
