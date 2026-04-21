#!/usr/bin/env bash
# dev.sh — start the local development server
# Usage: ./scripts/dev.sh

set -euo pipefail

if [[ -z "${SPEECHMATICS_API_KEY:-}" ]]; then
  echo "ERROR: SPEECHMATICS_API_KEY is not set"
  echo "       Get a free key at https://portal.speechmatics.com"
  exit 1
fi

echo "==> Starting Speechmatics Live Transcription server"
echo "    Dashboard: http://localhost:8000/dashboard"
echo "    API docs:  http://localhost:8000/docs"
echo ""

python -m src.python.server
