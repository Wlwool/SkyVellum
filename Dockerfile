FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.7.14 /uv /uvx /bin/

RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*
ENV TZ=Europe/Moscow

WORKDIR /app

ENV PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .

RUN mkdir -p /app/database /app/logs

CMD ["sh", "-c", "alembic upgrade head && exec python main.py"]
