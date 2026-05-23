#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source ~/venv/bin/activate 2>/dev/null || true
export OLLAMA_HOST=${OLLAMA_HOST:-127.0.0.1:11434}
export OLLAMA_MODEL=${OLLAMA_MODEL:-mistral}
export OLLAMA_TIMEOUT=${OLLAMA_TIMEOUT:-600}
export PDF_LIMIT=${PDF_LIMIT:-3}
python -m app.ingest
sqlite3 grants.db "SELECT id, file_name, call_code, title FROM grants;" || true
