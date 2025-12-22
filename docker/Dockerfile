FROM python:3.14.2-slim

WORKDIR /app
ENV PYSTRAY_HEADLESS=1
ENV USE_AVAILABLE_PORT=0
ENV SERVER_PORT=9000

RUN apt-get update && apt-get install -y \
    build-essential \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libopenjp2-7-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app

CMD ["python", "main.py"]
