FROM python:3.14-slim AS base

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
          build-essential gcc git curl ca-certificates \
          libpq-dev postgresql-client python3-dev pkg-config \
          libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir uv


FROM base AS deps

COPY pyproject.toml ./
COPY shared/pyproject.toml shared/pyproject.toml
COPY app/s3_api/pyproject.toml app/s3_api/pyproject.toml
COPY app/bot/pyproject.toml app/bot/pyproject.toml

ARG SERVICE
RUN uv sync --no-editable --package ${SERVICE}


FROM base AS runtime

WORKDIR /app

COPY --from=deps /app/.venv /app/.venv
COPY . .

ENV PATH="/app/.venv/bin:$PATH"

RUN groupadd -r app && useradd -r -m -d /app -g app app \
    && chown -R app:app /app \
    && chmod -R 777 /app

USER app