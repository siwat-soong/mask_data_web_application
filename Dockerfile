# Backend image: FastAPI + Tesseract OCR (Thai + English).
# Build:  docker build -t maskdata .
# Run:    docker run --rm -p 8000:8000 maskdata   then open http://127.0.0.1:8000/docs
# Test:   docker build --target test -t maskdata-test . && docker run --rm maskdata-test
FROM python:3.12-slim AS app

# The Tesseract program and its Thai data; pytesseract only calls this program.
# tesseract-ocr already pulls in the English data.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-tha \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install packages before copying the code, so code changes don't redo this slow step.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Hosting services usually pass the port in $PORT; 8000 when run locally.
# exec replaces the shell with uvicorn, so "docker stop" reaches uvicorn directly.
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]


# Test image: the app plus a Thai font, so the real Thai OCR test can draw its image.
FROM app AS test
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-tlwg-garuda-ttf \
    && rm -rf /var/lib/apt/lists/*
CMD ["python", "-m", "pytest", "backend/tests", "-v", "-rs", "-p", "no:cacheprovider"]


# The last stage is what a plain "docker build" produces: the app without the test font.
FROM app
