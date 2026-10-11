#!/usr/bin/env bash
set -euo pipefail
# Backend SOLO en loopback: jamás escuchar en 0.0.0.0.
# GUNICORN_CMD_ARGS="" anula el default de Render (--bind 0.0.0.0:10000).
GUNICORN_CMD_ARGS="" gunicorn --bind 127.0.0.1:8000 --workers 1 --threads 4 \
  --timeout 180 'app:create_app()' &
pid_backend=$!
gunicorn --bind "0.0.0.0:${PORT:-10000}" --workers 1 --threads 4 \
  --timeout 180 'gateway.main:create_app()' &
pid_gateway=$!
trap 'kill -TERM $pid_backend $pid_gateway 2>/dev/null' TERM INT
# Si muere cualquiera de los dos, salimos con error -> Render reinicia todo.
wait -n
kill -TERM $pid_backend $pid_gateway 2>/dev/null || true
exit 1
