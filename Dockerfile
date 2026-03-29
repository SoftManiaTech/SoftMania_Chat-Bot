# =============================================================================
# STAGE 1: Builder — compile / resolve all Python wheels
# =============================================================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /wheels

# Build arg — default to prod requirements, override for dev
ARG REQUIREMENTS=requirements.txt

# Copy requirements first — changes here invalidate the wheel cache layer only.
COPY requirements.txt requirements-dev.txt ./

# --prefer-binary: grabs pre-compiled wheels from PyPI before trying to compile
# from source. C-compilers (build-essential, gfortran, etc.) have been removed 
# since all packages in our requirements now have pre-built wheels.
RUN pip install --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --prefer-binary -r ${REQUIREMENTS} -w /wheels

# =============================================================================
# STAGE 2: Runtime — minimal production image
# =============================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# HF_HOME must be writable at container runtime.
# We use /app/.cache so it lives inside the volume mount defined in docker-compose.
ENV HF_HOME=/app/.cache/huggingface

WORKDIR /app

# Build arg for runtime parity
ARG REQUIREMENTS=requirements.txt

# Install from local wheels — fully offline, zero compilation.
COPY --from=builder /wheels /wheels
COPY requirements.txt requirements-dev.txt ./

RUN pip install --no-cache-dir --no-index --find-links=/wheels -r ${REQUIREMENTS} \
    && rm -rf /wheels

# Copy project source (respects .dockerignore — excludes venv/, .git/, data/, etc.)
COPY . /app

# Expose the port Hugging Face Spaces expects
EXPOSE 7860

# main.py:
#   1. Sets HF_HOME env var
#   2. Calls pre_download_models() if LOCAL_EMBEDDING_MODEL=true
#   3. Starts Uvicorn with reload controlled dynamically by APP_ENV
CMD ["python", "main.py"]
