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
| App server      | [Gunicorn](https://gunicorn.org/) + [WhiteNoise](https://whitenoise.readthedocs.io/) |
| Packaging       | [uv](https://github.com/astral-sh/uv)                                 |
| Lint and format | [Ruff](https://github.com/astral-sh/ruff), every rule enabled         |
| Git hooks       | [prek](https://github.com/j178/prek)                                  |

## Getting started

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [PostgreSQL](https://www.postgresql.org/download/)
- [Mailpit](https://mailpit.axllent.org/docs/install/) to catch outgoing email

### Setup

```bash
git clone https://github.com/prabhuakshay/kosha.git
cd kosha
uv sync
uv run prek install
cp .env.example .env   # then set DEBUG=true, SECRET_KEY and DATABASE_URL
uv run manage.py migrate
uv run manage.py createsuperuser
uv run manage.py runserver
```

Every setting is configured through environment variables or `.env`. See [`.env.example`](.env.example) for the full list.

## Deployment

Defaults are production-safe: `DEBUG` is off, HTTPS is enforced and HSTS is on. At minimum set `SECRET_KEY`, `ALLOWED_HOSTS` and `DATABASE_URL`, then:

```bash
export UV_NO_DEV=1   # keep dev tools out of every uv sync and uv run
uv sync --locked
uv run manage.py check --deploy
uv run manage.py migrate
uv run manage.py collectstatic --noinput
uv run gunicorn config.wsgi --bind 0.0.0.0:8000
```

Static files are served by [WhiteNoise](https://whitenoise.readthedocs.io/). Behind a TLS-terminating reverse proxy, set `SECURE_PROXY_SSL_HEADER=true`.

## Development

```bash
uv run ruff check .        # lint
uv run ruff format .       # format
uv run prek run -a         # run every hook against the whole repo
```

### Conventions

- **Commits** follow [Conventional Commits](https://www.conventionalcommits.org/), enforced by a `commit-msg` hook.
- **No direct commits to `main`** — work on a branch and open a pull request.
- **Docstrings** are required on public modules, classes and functions (Google style), and must stay in sync with signatures.

## License

[MIT](LICENSE) © Akshay Prabhu
