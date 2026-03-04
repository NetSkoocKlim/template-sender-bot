FROM public.ecr.aws/docker/library/python:3.14-slim


WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
          build-essential gcc git curl ca-certificates \
          libpq-dev postgresql-client python3-dev pkg-config \
          libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*


RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* requirements.txt* /app/

COPY . /app

RUN groupadd -r app && useradd -r -m -d /app -g app app \
    && chown -R app:app /app \
    && chmod -R 777 /app

USER app


RUN set -eux; \
    if [ -f "./pyproject.toml" ] || [ -f "./uv.lock" ]; then \
        rm -rf .venv || true; \
        uv venv --clear --python "$(which python)"; \
        uv sync; \
    elif [ -f "./requirements.txt" ]; then \
        uv pip install --system -r requirements.txt; \
    else \
        echo "No dependency file found (pyproject.toml/uv.lock or requirements.txt)"; \
    fi

ENV PATH="${PATH}:/app/.venv/bin"

CMD ["uv", "run", "python", "-m", "bot"]