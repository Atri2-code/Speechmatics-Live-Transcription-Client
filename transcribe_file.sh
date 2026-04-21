#!/usr/bin/env bash
# transcribe_file.sh — transcribe an audio file and save the transcript
# Usage: ./scripts/transcribe_file.sh <audio_file> [language]
# Example: ./scripts/transcribe_file.sh meeting.wav en

set -euo pipefail

AUDIO_FILE="${1:-}"
LANGUAGE="${2:-en}"
OUTPUT_DIR="./transcripts"

if [[ -z "${AUDIO_FILE}" ]]; then
  echo "Usage: $0 <audio_file> [language]"
  exit 1
fi

if [[ ! -f "${AUDIO_FILE}" ]]; then
  echo "ERROR: File not found: ${AUDIO_FILE}"
  exit 1
fi

if [[ -z "${SPEECHMATICS_API_KEY:-}" ]]; then
  echo "ERROR: SPEECHMATICS_API_KEY is not set"
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

BASENAME=$(basename "${AUDIO_FILE%.*}")
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}/${BASENAME}_${TIMESTAMP}.txt"

echo "==> Transcribing: ${AUDIO_FILE}"
echo "    Language: ${LANGUAGE}"
echo "    Output:   ${OUTPUT_FILE}"

python -m src.python.client \
  --file "${AUDIO_FILE}" \
  --language "${LANGUAGE}" \
  --output "${OUTPUT_FILE}"

echo "==> Done — transcript saved to ${OUTPUT_FILE}"
wc -w "${OUTPUT_FILE}" | awk '{print "    Words:", $1}'
