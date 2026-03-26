FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /wheels

# Minimal build deps — git/cmake/curl removed (not needed when using --prefer-binary)
RUN apt-get update \
     && apt-get install -y --no-install-recommends \
         build-essential \
         gfortran \
         pkg-config \
         libopenblas-dev \
         liblapack-dev \
         python3-dev \
     && rm -rf /var/lib/apt/lists/*

# Copy requirements and build wheels.
# --prefer-binary: pulls pre-compiled wheels from PyPI first, only compiles as fallback.
# This is the single biggest build-time win (avoids compiling scipy/numba/cryptography/etc.)
COPY requirements.txt /wheels/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --prefer-binary -r /wheels/requirements.txt -w /wheels

# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Bake the HF home path into the image so main.py and the pre-download step agree
ENV HF_HOME=/app/.cache/huggingface

WORKDIR /app

# Minimal runtime shared libraries required by numpy/scipy wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libopenblas0 \
       liblapack3 \
    && rm -rf /var/lib/apt/lists/*

# Install directly from pre-built wheels — fully offline, no compilation
COPY --from=builder /wheels /wheels
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r /app/requirements.txt

# Bake the tokenizer config files (~100 KB) into the image at BUILD time.
# On HuggingFace Spaces the .cache dir is ephemeral, so without this the
# tokenizer is re-downloaded on every cold start, adding 30–60 s to startup.
RUN python -c "\
from huggingface_hub import snapshot_download; \
snapshot_download(\
    repo_id='intfloat/e5-mistral-7b-instruct', \
    allow_patterns=['*.json', '*.model', 'tokenizer*'], \
    local_dir='/app/.cache/huggingface'\
)"

# Copy project (relies on .dockerignore to exclude venv/, .git/, data/, logs/)
COPY . /app

EXPOSE 7860

# main.py runs pre_download_models() (skipped if cache exists) then starts Uvicorn
CMD ["python", "main.py"]
