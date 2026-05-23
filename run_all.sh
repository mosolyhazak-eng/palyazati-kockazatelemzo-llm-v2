#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export PDF_LIMIT=${PDF_LIMIT:-3}
export OLLAMA_TIMEOUT=${OLLAMA_TIMEOUT:-600}
python -m app.ingest
python -m app.monitoring
printf '\nIndítás külön terminálokban:\n'
printf '  ./run_api.sh\n'
printf '  ./run_streamlit.sh\n'
