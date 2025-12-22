FROM python:3.14.2-slim

# ------------------------------------------------------------------
# Environment
# ------------------------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYSTRAY_HEADLESS=1 \
    USE_AVAILABLE_PORT=0 \
    SERVER_PORT=9000

# ------------------------------------------------------------------
# System dependencies
# ------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libopenjp2-7-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------
WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ /app

# ------------------------------------------------------------------
# Runtime
# ------------------------------------------------------------------
CMD ["python", "main.py"]

