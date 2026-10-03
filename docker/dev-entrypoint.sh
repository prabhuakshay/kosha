#!/bin/sh
# Runs on every start rather than at build time: the lockfile and migrations
# live in the bind-mounted working tree, so a pulled branch needs no rebuild.
set -eu

uv sync --frozen
python manage.py migrate --noinput
python manage.py setup_code

exec "$@"
