# Auralis — single-container deployment (Railway / Render / Fly.io / anywhere)
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# Install dependencies first so this layer caches across code changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

# World-writable: HF Spaces (and other PaaS) run the container as a
# non-root user, and SQLite needs write access to its directory.
RUN mkdir -p /data && chmod 777 /data
ENV DATABASE_PATH=/data/auralis.db

EXPOSE 8000
# Shell form so $PORT from the platform (Render/Railway/Heroku) is honored
CMD uv run --no-sync uvicorn auralis.api.app:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir src
