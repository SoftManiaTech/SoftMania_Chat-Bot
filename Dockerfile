FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /wheels

# Install build dependencies to compile wheels
RUN apt-get update \
     && apt-get install -y --no-install-recommends \
         build-essential \
         gfortran \
         git \
         cmake \
         pkg-config \
         libopenblas-dev \
         liblapack-dev \
         curl \
         python3-dev \
     && rm -rf /var/lib/apt/lists/*

# Copy requirements and build wheels for all packages (cached between builds)
COPY requirements.txt /wheels/requirements.txt
RUN pip install --upgrade pip setuptools wheel cython && \
    pip wheel --no-cache-dir -r /wheels/requirements.txt -w /wheels

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal runtime libs required by some wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libopenblas0 \
       liblapack3 \
    && rm -rf /var/lib/apt/lists/*

# Copy prebuilt wheels from builder and install from them (fast, deterministic)
COPY --from=builder /wheels /wheels
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --no-index --find-links=/wheels -r /app/requirements.txt

# Copy project
COPY . /app

EXPOSE 7860

# We use main.py as the entry point because it runs our critical pre_download_models()
# caching script before starting Uvicorn, which prevents the Space from freezing.
CMD ["python", "main.py"]
