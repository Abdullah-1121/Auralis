# Auralis — single-container deployment (Railway / Render / Fly.io / anywhere)
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# Install dependencies first so this layer caches across code changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

ENV DATABASE_PATH=/data/auralis.db
VOLUME /data

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "auralis.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
