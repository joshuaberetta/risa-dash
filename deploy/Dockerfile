# One image for every role (web, worker) and every target (DO, self-hosted, offline box).
# GDAL for imagery and vector conversion, Chromium for printing.

FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
COPY symbology/ /app/symbology/
RUN npm run build

FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.4 AS base
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv venv --python /usr/bin/python3 /opt/venv && uv sync --frozen --no-dev --no-install-project
RUN apt-get update && apt-get install -y --no-install-recommends xz-utils \
 && playwright install --with-deps --only-shell chromium && rm -rf /var/lib/apt/lists/*
# Typst lays out the printed pages
ARG TYPST_VERSION=0.15.1
ARG TARGETARCH
RUN arch=$([ "$TARGETARCH" = "arm64" ] && echo aarch64 || echo x86_64) \
 && curl -fsSL "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-${arch}-unknown-linux-musl.tar.xz" \
    | tar -xJ -C /usr/local/bin --strip-components=1 "typst-${arch}-unknown-linux-musl/typst" \
 && typst --version
COPY deploy/start.sh /usr/local/bin/start

# Development: code is mounted
FROM base AS dev
RUN uv sync --frozen --no-install-project

FROM base AS app
COPY symbology/ /app/symbology/
COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist
RUN SECRET_KEY=build python manage.py collectstatic --noinput -v0
EXPOSE 8000
CMD ["start", "web"]
