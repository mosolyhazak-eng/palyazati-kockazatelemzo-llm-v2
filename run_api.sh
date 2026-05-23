#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source ~/venv/bin/activate 2>/dev/null || true
uvicorn app.api:app --host 0.0.0.0 --port 8000
