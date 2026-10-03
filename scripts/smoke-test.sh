#!/usr/bin/env bash
# Black-box checks against a built production image, as it will run in
# production. Needs only Docker and curl on the host.
#
#   scripts/smoke-test.sh kosha:smoke
set -euo pipefail

image=${1:?usage: smoke-test.sh IMAGE}
run=kosha-smoke-$$
db=$run-db
app=$run-app

cleanup() {
  docker rm -f "$db" "$app" "$app-nodb" >/dev/null 2>&1 || true
  docker network rm "$run" >/dev/null 2>&1 || true
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

pass() {
  echo "ok: $*"
}

prod_env=(
  -e SECRET_KEY=smoke-only-not-a-real-secret-key-padding-to-fifty-characters
  -e ALLOWED_HOSTS=kosha.example.com
  -e DATABASE_URL=postgres://kosha:kosha@$db:5432/kosha
  -e SECURE_PROXY_SSL_HEADER=true
  -e SECURE_HSTS_INCLUDE_SUBDOMAINS=true
  -e SECURE_HSTS_PRELOAD=true
  -e S3_BUCKET_NAME=kosha-smoke
  -e S3_ENDPOINT_URL=https://smoke.r2.cloudflarestorage.com
  -e S3_ACCESS_KEY_ID=smoke
  -e S3_SECRET_ACCESS_KEY=smoke
)

in_image() {
  docker run --rm --network "$run" "${prod_env[@]}" "$image" "$@"
}

# Starts the app in a container named $1 with any extra docker run flags, and
# prints the status /healthz/ answers once it answers at all.
start_and_probe() {
  local name=$1 port
  shift
  docker run -d --name "$name" "${prod_env[@]}" "$@" -p 127.0.0.1::8000 "$image" >/dev/null
  port=$(docker port "$name" 8000/tcp | head -1 | cut -d: -f2)
  for _ in $(seq 60); do
    status=$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: anything.invalid' \
      "http://127.0.0.1:$port/healthz/" || true)
    if [ "$status" != "000" ]; then
      echo "$status"
      return
    fi
    sleep 1
  done
  echo "000"
}

docker network create "$run" >/dev/null
docker run -d --name "$db" --network "$run" \
  -e POSTGRES_USER=kosha -e POSTGRES_PASSWORD=kosha -e POSTGRES_DB=kosha \
  postgres:18-alpine >/dev/null

# --- Static assets --------------------------------------------------------

in_image sh -c 'test -s staticfiles/css/app.css' || fail "stylesheet missing or empty"
in_image grep -q 'min-h-dvh' staticfiles/css/app.css \
  || fail "stylesheet lacks a utility class the base template uses"
for js in htmx.min.js alpine.min.js lucide.min.js; do
  in_image test -s "staticfiles/js/$js" || fail "$js missing or empty"
done
in_image grep -q 'CSP Parser Error' staticfiles/js/alpine.min.js \
  || fail "alpine.min.js is not Alpine's CSP build"
for file in fonts/public-sans-latin-wght-normal.woff2 icons/icon-512.png core/app.js; do
  in_image test -s "staticfiles/$file" || fail "$file missing or empty"
done
pass "compiled, vendored and committed assets collected"

# --- Required configuration -----------------------------------------------

status=0
output=$(timeout 60 docker run --rm \
  -e SECRET_KEY=smoke -e ALLOWED_HOSTS=kosha.example.com \
  -e DATABASE_URL=postgres://kosha:kosha@$db:5432/kosha \
  "$image" 2>&1) || status=$?
[ "$status" -ne 0 ] && [ "$status" -ne 124 ] || fail "started without S3_* (exit $status)"
grep -q 'S3_BUCKET_NAME' <<<"$output" || fail "exited for another reason: $output"
pass "refuses to start without S3_* when DEBUG=false"

# --- Deployment checks ----------------------------------------------------

in_image python manage.py check --deploy --fail-level WARNING || fail "check --deploy"
pass "check --deploy"

# --- Health ---------------------------------------------------------------

for _ in $(seq 30); do
  docker exec "$db" pg_isready -U kosha >/dev/null 2>&1 && break
  sleep 1
done
in_image python manage.py migrate --noinput >/dev/null || fail "migrate"

status=$(start_and_probe "$app" --network "$run")
[ "$status" = "200" ] || { docker logs "$app"; fail "/healthz/ answered $status, want 200"; }
pass "/healthz/ answers 200 over plain HTTP with an arbitrary Host"

status=$(start_and_probe "$app-nodb" \
  -e DATABASE_URL=postgres://kosha:kosha@unreachable.invalid:5432/kosha)
[ "$status" = "503" ] || { docker logs "$app-nodb"; fail "/healthz/ answered $status, want 503"; }
pass "/healthz/ answers 503 when the database is unreachable"

# --- Static serving -------------------------------------------------------

hashed=$(docker exec "$app" python -c \
  "import json; print(json.load(open('staticfiles/staticfiles.json'))['paths']['css/app.css'])")
port=$(docker port "$app" 8000/tcp | head -1 | cut -d: -f2)
headers=$(curl -s -D - -o /dev/null -H 'Host: kosha.example.com' -H 'X-Forwarded-Proto: https' \
  "http://127.0.0.1:$port/static/$hashed")
echo "$headers" | head -1 | grep -q ' 200' || fail "hashed stylesheet not served: $headers"
echo "$headers" | grep -qi '^cache-control:.*max-age=315360000' \
  || fail "hashed stylesheet lacks far-future caching: $headers"
pass "hashed stylesheet served with far-future Cache-Control"

echo "all smoke checks passed"
