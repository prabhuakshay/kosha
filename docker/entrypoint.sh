#!/bin/sh
# Production entrypoint. Until the install is claimed, the server's log carries
# the Setup code that Claims it. Only the server prints it: the image also runs
# one-off commands, such as migrate, against a database that may not be ready.
set -eu

if [ "${1:-}" = "gunicorn" ]; then
  # Never fatal, so the server still starts, and /healthz/ still reports, when
  # the database is down.
  python manage.py setup_code || true
fi

exec "$@"
