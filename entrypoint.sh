#!/bin/sh
set -e

ROLE="${ROLE:-web}"
PORT="${PORT:-8008}"

if [ "$ROLE" = "web" ]; then
  echo "Running migrations..."
  python3 manage.py migrate --noinput
  echo "Collecting static files..."
  python3 manage.py collectstatic --noinput
  echo "Starting Uvicorn..."
  exec uvicorn core.asgi:application \
    --host 0.0.0.0 \
    --port "$PORT" \
    --ws websockets \
    --timeout-keep-alive "${UVICORN_TIMEOUT:-120}" \
    --proxy-headers
elif [ "$ROLE" = "worker" ]; then
  echo "Starting Celery worker..."
  exec celery -A core worker -l info
elif [ "$ROLE" = "beat" ]; then
  echo "Starting Celery beat..."
  exec celery -A core beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
else
  echo "Unknown ROLE: $ROLE"
  exit 1
fi
