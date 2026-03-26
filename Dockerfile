# =============================================================================
# STAGE 1: Builder — compile / resolve all Python wheels
# =============================================================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /wheels

# Build-time C dependencies needed only for packages without binary wheels.
# Note: git, cmake, curl are intentionally excluded — not needed with --prefer-binary.
RUN apt-get update \
     && apt-get install -y --no-install-recommends \
         build-essential \
         gfortran \
         pkg-config \
         libopenblas-dev \
         liblapack-dev \
         python3-dev \
     && rm -rf /var/lib/apt/lists/*

# Copy requirements first — changes here invalidate the wheel cache layer only.
COPY requirements.txt /wheels/requirements.txt

# --prefer-binary: grabs pre-compiled wheels from PyPI before trying to compile
# from source. This is the single largest build-time saving for this project.
RUN pip install --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --prefer-binary -r /wheels/requirements.txt -w /wheels

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

# Only the shared libraries the pre-built numpy/scipy wheels link against at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libopenblas0 \
       liblapack3 \
    && rm -rf /var/lib/apt/lists/*

# Install from local wheels — fully offline, zero compilation.
# Upgrade step is intentionally omitted here; pip version from python:3.11-slim is fine
# for an offline install (--no-index + --find-links).
COPY --from=builder /wheels /wheels
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r /app/requirements.txt \
    && rm -rf /wheels

# Copy project source (respects .dockerignore — excludes venv/, .git/, data/, etc.)
COPY . /app

# Expose the port Hugging Face Spaces expects
EXPOSE 7860

# main.py:
#   1. Sets HF_HOME env var
#   2. Calls pre_download_models() → downloads tokenizer config files (~100 KB) on
#      FIRST boot only. Subsequent restarts skip it because HF checks the cache.
#      On HF Spaces the cache is persisted by the Space's storage layer between reboots.
#   3. Starts Uvicorn with reload=False (file-watcher is harmful in containers)
CMD ["python", "main.py"]
