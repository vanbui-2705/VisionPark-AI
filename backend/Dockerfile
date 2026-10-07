FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system visionpark \
    && adduser --system --ingroup visionpark --home /app visionpark

COPY pyproject.toml ./
RUN mkdir app && touch app/__init__.py

ARG INSTALL_REAL_ALPR=false
ARG INSTALL_OCR=false
ARG INSTALL_TORCH_CPU=false
RUN python -m pip install --upgrade pip \
    && if [ "$INSTALL_REAL_ALPR" = "true" ] || [ "$INSTALL_OCR" = "true" ]; then apt-get update && apt-get install -y --no-install-recommends libgl1 libgomp1 && rm -rf /var/lib/apt/lists/*; fi \
    && if [ "$INSTALL_TORCH_CPU" = "true" ]; then python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu; fi \
    && if [ "$INSTALL_REAL_ALPR" = "true" ]; then python -m pip install ".[real]"; else python -m pip install .; fi \
    && if [ "$INSTALL_OCR" = "true" ]; then python -m pip install ".[ocr]"; fi \
    && mkdir -p /app/var/media \
    && chown -R visionpark:visionpark /app

RUN if [ "$INSTALL_REAL_ALPR" = "true" ] || [ "$INSTALL_OCR" = "true" ]; then \
    apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*; fi

COPY app ./app
COPY models ./models
COPY alembic.ini ./
COPY alembic ./alembic

FROM base AS ci

ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then python -m pip install ".[dev,onnx]"; fi

COPY tests ./tests

USER visionpark

CMD ["sh", "-c", "python -m pytest && python -m ruff check app tests && python -m ruff format --check app tests"]

FROM base AS runtime

USER visionpark

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
