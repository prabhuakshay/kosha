# syntax=docker/dockerfile:1
#
# Development stages (`tailwind`, `dev`) hold a toolchain and no source: the
# working tree is bind-mounted and everything runs as the developer's uid.
# The production stage (`prod`) bakes in source, dependencies and compiled
# assets, built by `assets` and `builder`, which never ship.
#
#   docker compose build                          the dev stack
#   docker compose -f compose.prod.yaml build     the prod image

ARG PYTHON_VERSION=3.14
ARG NODE_VERSION=25
ARG UV_VERSION=0.12

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv


# --- tailwind: the stylesheet watcher (dev) ---------------------------------

FROM node:${NODE_VERSION}-slim AS tailwind

ARG DOCKER_UID=1000
ARG DOCKER_GID=1000

WORKDIR /app

# Docker seeds the anonymous volume masking node_modules from the image,
# ownership included, so it must exist here owned by the developer.
RUN mkdir -p /app/node_modules && chown -R ${DOCKER_UID}:${DOCKER_GID} /app

CMD ["sh", "-c", "npm install --no-audit --no-fund && npm run watch"]


# --- dev: the autoreloading server ------------------------------------------

FROM python:${PYTHON_VERSION}-slim AS dev

COPY --from=uv /uv /uvx /usr/local/bin/

# The virtualenv lives outside the bind-mounted tree so it never collides with
# the host's .venv. Copy mode because the cache volume is another filesystem.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_CACHE_DIR=/cache/uv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/opt/venv/bin:$PATH"

ARG DOCKER_UID=1000
ARG DOCKER_GID=1000

# The /app entries are where compose mounts anonymous volumes, which Docker
# seeds from the image, ownership included.
RUN mkdir -p /opt/venv /cache/uv /app/.venv /app/node_modules /app/staticfiles /app/.ruff_cache \
    && chown -R ${DOCKER_UID}:${DOCKER_GID} /opt/venv /cache/uv /app

WORKDIR /app

COPY docker/dev-entrypoint.sh /usr/local/bin/dev-entrypoint

ENTRYPOINT ["dev-entrypoint"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


# --- assets: compiled stylesheet and vendored scripts (build only) ----------

FROM node:${NODE_VERSION}-slim AS assets

WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

# Tailwind silently emits nothing for classes in sources it cannot see, so
# every directory that can name a class must be copied in.
COPY assets/ assets/
COPY templates/ templates/
COPY apps/ apps/
# Fonts and icons are committed; the build adds the stylesheet and scripts.
COPY static/ static/

RUN npm run build


# --- builder: the virtualenv (build only) -----------------------------------

FROM python:${PYTHON_VERSION}-slim AS builder

COPY --from=uv /uv /uvx /usr/local/bin/

# Bytecode is compiled now because the production filesystem is read-only.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_CACHE_DIR=/cache/uv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/cache/uv \
    uv sync --frozen --no-dev --no-install-project


# --- prod: what serves -------------------------------------------------------

FROM python:${PYTHON_VERSION}-slim AS prod

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/opt/venv/bin:$PATH"

ARG APP_UID=10001
ARG APP_GID=10001

RUN groupadd --system --gid ${APP_GID} app \
    && useradd --system --uid ${APP_UID} --gid app --no-create-home --home-dir /app app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Owned by root so a compromised worker cannot rewrite what it runs.
COPY manage.py ./
COPY config/ config/
COPY apps/ apps/
COPY templates/ templates/
COPY --from=assets /app/static/ static/
COPY docker/gunicorn.conf.py docker/
COPY docker/entrypoint.sh /usr/local/bin/entrypoint

# Settings refuse to load without these. The values exist only for this
# command; the database URL is parsed and never connected to.
RUN SECRET_KEY=collectstatic \
    DATABASE_URL=postgres://collectstatic@localhost/collectstatic \
    S3_BUCKET_NAME=collectstatic \
    S3_ENDPOINT_URL=https://collectstatic.invalid \
    S3_ACCESS_KEY_ID=collectstatic \
    S3_SECRET_ACCESS_KEY=collectstatic \
    python manage.py collectstatic --noinput \
    && python -m compileall -q config apps manage.py

USER app

EXPOSE 8000

ENTRYPOINT ["entrypoint"]
CMD ["gunicorn", "--config", "docker/gunicorn.conf.py", "config.wsgi:application"]
