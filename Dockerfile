# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/workspaces/youtube-auto-upload-starter-repo

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Build tools
    build-essential \
    # FFmpeg for video processing
    ffmpeg \
    # Image processing libraries
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    # SSL libraries
    libssl-dev \
    libffi-dev \
    # Git for version control
    git \
    # Curl for downloads
    curl \
    # Make for build system
    make \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash vscode \
    && usermod -aG sudo vscode \
    && echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set working directory
WORKDIR /workspaces/youtube-auto-upload-starter-repo

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p \
    storage/downloads \
    storage/transforms \
    storage/thumbnails \
    storage/proofs \
    storage/temp \
    data \
    && chown -R vscode:vscode /workspaces/youtube-auto-upload-starter-repo

# Switch to non-root user
USER vscode

# Set up environment
ENV PATH="/home/vscode/.local/bin:${PATH}"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "-m", "app.main"]
