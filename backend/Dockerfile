# ARKiin v2.0 - Backend Cloud Run Container
# Python 3.11 slim for minimal image size
FROM python:3.11-slim

# Metadata
LABEL maintainer="contact@arkiin.com"
LABEL version="2.0.0"
LABEL description="ARKiin v2.0 FastAPI Backend - Cloud Run"

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    GOOGLE_CLOUD_PROJECT=arkiin

# Install system dependencies for OpenCV and PDF
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1001 arkiin && chown -R arkiin:arkiin /app
USER arkiin

# Expose Cloud Run port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
