#!/bin/sh
# Build the production image and run scripts/e2e.py against it with the internet cut
# off (deploy/compose.e2e.yaml). Prints the web and worker logs on failure. Used by CI.
#   scripts/e2e.sh            # build, test, tear down
#   NO_BUILD=1 scripts/e2e.sh # reuse $RISA_IMAGE (default risa-dash:latest)
set -eu
cd "$(dirname "$0")/.."
export POSTGRES_PASSWORD=e2e
dc="docker compose -p risa-e2e -f deploy/compose.yaml -f deploy/compose.e2e.yaml"

[ -n "${NO_BUILD:-}" ] || $dc build web
trap '$dc down -v --remove-orphans >/dev/null 2>&1' EXIT
if ! $dc run --rm e2e; then
  $dc logs --no-color web worker | tail -200
  exit 1
fi
