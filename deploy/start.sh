#!/bin/sh
# Roles: web (API + frontend + admin), worker (jobs), migrate
set -e
cd /app/backend
case "${1:-web}" in
  web)
    python manage.py migrate --noinput
    exec gunicorn config.wsgi -b "0.0.0.0:${PORT:-8000}" -w "${WEB_CONCURRENCY:-3}" --timeout 120 \
      --access-logfile - --forwarded-allow-ips='*'
    ;;
  worker)
    exec python manage.py procrastinate worker --concurrency "${WORKER_CONCURRENCY:-2}"
    ;;
  migrate)
    exec python manage.py migrate --noinput
    ;;
  *)
    exec "$@"
    ;;
esac
