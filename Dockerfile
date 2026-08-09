ARG BASE_IMAGE=python:3.12-slim-bookworm
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_PROJECT_ENVIRONMENT=/opt/jinjapocalypse

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.11.29

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-dev --no-install-project \
    && rm -rf /tmp/uv-cache

COPY *.py ./

RUN mkdir -p /jinjapocalypse \
    && useradd --system --uid 10001 --create-home --home-dir /home/jinjapocalypse jinjapocalypse \
    && chown -R jinjapocalypse:jinjapocalypse /jinjapocalypse

WORKDIR /jinjapocalypse

USER jinjapocalypse

ENTRYPOINT ["uv", "run", "--locked", "--no-dev", "--project", "/app", "python", "/app/jinjapocalypse.py"]
