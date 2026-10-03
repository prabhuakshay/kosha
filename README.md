<div align="center">

# Kosha

**A self-hosted personal finance app built with Django.**

_Kosha (कोश) — Sanskrit for treasury._

[![Python](https://img.shields.io/badge/python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![prek](https://img.shields.io/badge/prek-enabled-orange)](https://github.com/j178/prek)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-FE5196?logo=conventionalcommits&logoColor=white)](https://www.conventionalcommits.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

</div>

---

> [!NOTE]
> Kosha is in early development. Nothing here is usable yet.

## Why Kosha

Your financial data is personal. Kosha keeps it on infrastructure you control, with no third-party aggregators, ads, or data resale.

## Planned features

- **Accounts** — bank, credit card, cash and investment accounts in one place
- **Transactions** — record, import and categorise income and spending
- **Budgets** — set monthly limits per category and track progress
- **Reports** — net worth, cash flow and spending trends over time

## Tech stack

| Layer           | Tool                                                                  |
| --------------- | --------------------------------------------------------------------- |
| Language        | [Python 3.14](https://www.python.org/)                                |
| Web framework   | [Django](https://www.djangoproject.com/)                              |
| Database        | [PostgreSQL](https://www.postgresql.org/)                              |
| Frontend        | [Tailwind CSS](https://tailwindcss.com/), [htmx](https://htmx.org/), [Alpine.js](https://alpinejs.dev/) (CSP build), [Lucide](https://lucide.dev/) |
| App server      | [Gunicorn](https://gunicorn.org/) + [WhiteNoise](https://whitenoise.readthedocs.io/) |
| Media storage   | [Cloudflare R2](https://developers.cloudflare.com/r2/) via [django-storages](https://django-storages.readthedocs.io/) |
| Deployment      | Docker image on [GHCR](https://github.com/prabhuakshay/kosha/pkgs/container/kosha) (amd64, arm64) |
| Packaging       | [uv](https://github.com/astral-sh/uv)                                 |
| Lint and format | [Ruff](https://github.com/astral-sh/ruff), every rule enabled         |
| Tests           | [pytest](https://pytest.org/) + [pytest-django](https://pytest-django.readthedocs.io/) |
| Git hooks       | [prek](https://github.com/j178/prek)                                  |

## Getting started

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Node.js](https://nodejs.org/) to build the stylesheet and vendor the scripts
- [PostgreSQL](https://www.postgresql.org/download/)
- [Mailpit](https://mailpit.axllent.org/docs/install/) to catch outgoing email

### Setup

```bash
git clone https://github.com/prabhuakshay/kosha.git
cd kosha
uv sync
uv run prek install
npm install
cp .env.example .env   # then set DEBUG=true, SECRET_KEY and DATABASE_URL
uv run manage.py migrate
uv run manage.py setup_code   # the code that Claims your install
npm run watch          # in a second terminal: rebuilds the stylesheet on change
uv run manage.py runserver
```

Every setting is configured through environment variables or `.env`. See [`.env.example`](.env.example) for the full list. With `DEBUG=true` and no `S3_BUCKET_NAME`, uploads go to the local `media/` directory. To work against a real R2 bucket instead, run `scripts/setup-r2.sh` and choose development.

### With Docker

Instead of installing uv and Node, run the development stack (Compose v2.30 or newer):

```bash
cp .env.example .env   # DEBUG=true, SECRET_KEY, DATABASE_URL
docker compose up
```

It runs an autoreloading Django server on http://localhost:8000 and a Tailwind watcher, both over your working tree and as your own uid (set `DOCKER_UID`/`DOCKER_GID` in `.env` if yours is not 1000). Dependencies are synced and migrations applied on every start. There is no database service: a Postgres on your machine is reached as `host.docker.internal`, not `localhost`. For `breakpoint()`, run `docker compose attach django`.

## Deployment

Kosha ships as a container image, `ghcr.io/prabhuakshay/kosha`, for amd64 and arm64. Every release `vX.Y.Z` is tagged `X.Y.Z` and, unless it is a prerelease, `X.Y` and `latest`. You need Docker with Compose v2.30 or newer, a PostgreSQL database, a private [Cloudflare R2](https://developers.cloudflare.com/r2/) bucket for uploaded files, and a reverse proxy that terminates TLS.

```bash
curl -O https://raw.githubusercontent.com/prabhuakshay/kosha/main/compose.prod.yaml
curl -o .env https://raw.githubusercontent.com/prabhuakshay/kosha/main/.env.example
curl -O https://raw.githubusercontent.com/prabhuakshay/kosha/main/scripts/setup-r2.sh
bash setup-r2.sh       # walks you through the R2 bucket and token, fills in S3_*
# edit .env: SECRET_KEY, ALLOWED_HOSTS, DATABASE_URL, CSRF_TRUSTED_ORIGINS
# (or WEBAUTHN_ORIGINS), SECURE_PROXY_SSL_HEADER=true, and KOSHA_VERSION to
# pin a release
docker compose -f compose.prod.yaml up -d
docker compose -f compose.prod.yaml logs django | grep "Setup code"
```

- **Claim:** open Kosha and enter the Setup code from the log to become its Owner, its only sign-in. `docker compose -f compose.prod.yaml exec django python manage.py setup_code` prints it again. Then add a Passkey or set up an Authenticator app, and save your ten Recovery codes. Passkeys are bound to `WEBAUTHN_RP_ID` (by default the host of the first of `WEBAUTHN_ORIGINS`, or of the HTTPS `CSRF_TRUSTED_ORIGINS`), so settle it before Claiming. Once claimed, there is no Setup code. See [ADR 0002](docs/adr/0002-one-owner-per-install.md).
- **Migrations** run once in a `migrate` container before the app starts; if they fail, the app does not start.
- **The app** listens on `127.0.0.1:8000` only (`DOCKER_HOST_PORT`). Point your proxy at it and have the proxy set `X-Forwarded-Proto`.
- **Database:** a Postgres on the same host is reached as `host.docker.internal`.
- **Uploaded files** are stored in R2 and served only through short-lived signed URLs; Kosha refuses to start without the `S3_*` settings. See [ADR 0001](docs/adr/0001-media-in-a-private-r2-bucket.md).
- **Upgrading:** change `KOSHA_VERSION` in `.env` and run `docker compose -f compose.prod.yaml up -d`.
- **Health:** `/healthz/` answers 200 when Django can reach its database and 503 when it cannot.
- **Hardening:** the container runs as an unprivileged user on a read-only filesystem with every capability dropped, rotated logs and CPU and memory limits. Gunicorn and the limits are tuned through `.env`; see the Gunicorn and Docker sections of [`.env.example`](.env.example).

Static files are compiled and collected into the image and served by [WhiteNoise](https://whitenoise.readthedocs.io/) with far-future caching.

## Development

```bash
uv run ruff check .        # lint
uv run ruff format .       # format
uv run pytest              # test, against the database in DATABASE_URL
uv run prek run -a         # run every hook against the whole repo
docker build --target prod -t kosha:smoke . && scripts/smoke-test.sh kosha:smoke
```

### Conventions

- **Commits** follow [Conventional Commits](https://www.conventionalcommits.org/), enforced by a `commit-msg` hook.
- **No direct commits to `main`** — work on a branch and open a pull request.
- **Docstrings** are required on public modules, classes and functions (Google style), and must stay in sync with signatures.

## License

[MIT](LICENSE) © Akshay Prabhu
