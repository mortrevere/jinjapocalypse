ARG BASE_IMAGE=python:3.12-slim-bookworm
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /jinjapocalypse

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY *.py /

RUN useradd --system --uid 10001 --create-home --home-dir /home/jinjapocalypse jinjapocalypse \
    && chown -R jinjapocalypse:jinjapocalypse /jinjapocalypse

USER jinjapocalypse

ENTRYPOINT ["python", "/jinjapocalypse.py"]
