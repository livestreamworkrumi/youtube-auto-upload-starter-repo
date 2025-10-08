# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data storage/downloads storage/transforms storage/thumbnails storage/proofs

# Set environment variables
ENV DEMO_MODE=true
ENV LOG_LEVEL=INFO
ENV DB_URL=sqlite:///./data/app.db

# Expose port
EXPOSE 8000

# Create a simple health check script
RUN echo '#!/usr/bin/env python3\n\
import sys\n\
try:\n\
    from app.config import get_settings\n\
    settings = get_settings()\n\
    print(f"Health check passed - Demo mode: {settings.demo_mode}")\n\
    sys.exit(0)\n\
except Exception as e:\n\
    print(f"Health check failed: {e}")\n\
    sys.exit(1)' > health_check.py && chmod +x health_check.py

# Default command
CMD ["python", "-m", "app.main"]
