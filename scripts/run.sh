#!/bin/bash
PROJECT_ROOT="$(realpath "$(dirname "$0")/..")"

cd "$PROJECT_ROOT"
exec uvicorn app.main:app \
    --host localhost \
    --port 8000 \
    --log-config "$PROJECT_ROOT/logging.yaml"