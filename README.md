# speechmatics-live-transcription-client

![CI](https://github.com/Atri2-code/speechmatics-live-transcription-client/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.11-3776AB)
![JavaScript](https://img.shields.io/badge/JavaScript-ES2022-F7DF1E)
![WebSocket](https://img.shields.io/badge/protocol-WebSocket-informational)
![License](https://img.shields.io/badge/license-MIT-green)

A real-time speech transcription client integrating with the [Speechmatics API](https://docs.speechmatics.com). Streams audio from microphone or file input over a WebSocket connection, receives live transcription events, and surfaces them in a browser-based dashboard with word-level confidence scoring, speaker diarisation, and session analytics.

Built to demonstrate real-time streaming systems, third-party SaaS API integration, and full-stack product delivery across Python and JavaScript.

---

## What it does

```
Microphone / Audio file
        │
        ▼
┌───────────────────┐      WebSocket       ┌──────────────────────┐
│  Python streaming  │ ──── audio chunks ──▶│  Speechmatics RT API │
│     client         │ ◀─── transcripts ─── │  (real-time ASR)     │
└────────┬──────────┘                       └──────────────────────┘
         │ Server-Sent Events
         ▼
┌───────────────────┐
│  FastAPI backend   │  REST + SSE
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  JS live dashboard │  Word stream · confidence · speaker labels
└───────────────────┘
```

---

## Features

- Real-time audio streaming to Speechmatics over WebSocket
- Live word-by-word transcript delivery via Server-Sent Events (SSE)
- Word-level confidence scoring with colour-coded highlighting
- Speaker diarisation — identifies and labels multiple speakers
- Session analytics: word count, WER estimate, words-per-minute
- Audio file transcription mode (WAV, MP3, FLAC)
- Clean JavaScript dashboard — no framework dependencies
- Pytest suite with mocked WebSocket and Speechmatics fixtures

---

## Repository structure

```
speechmatics-live-transcription-client/
├── .github/
│   └── workflows/
│       ├── ci.yml                  # lint, test, type-check on PR
│       └── release.yml             # tag-triggered PyPI/NPM publish
├── src/
│   ├── python/
│   │   ├── client.py               # WebSocket streaming client
│   │   ├── audio_capture.py        # microphone + file audio capture
│   │   ├── session.py              # session state, analytics
│   │   └── server.py               # FastAPI backend + SSE endpoint
│   └── js/
│       ├── dashboard.js            # live transcript dashboard
│       └── audio_recorder.js       # browser MediaRecorder wrapper
├── dashboard/
│   └── index.html                  # single-page dashboard UI
├── tests/
│   ├── test_client.py              # WebSocket client unit tests
│   ├── test_session.py             # session analytics tests
│   └── test_server.py              # FastAPI endpoint tests
├── scripts/
│   ├── transcribe_file.sh          # batch file transcription helper
│   └── dev.sh                      # local dev startup script
├── docs/
│   └── api.md                      # REST + SSE API reference
├── requirements.txt
└── README.md
```

---

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ (optional, for JS tooling) |
| Speechmatics API key | [Get one free](https://portal.speechmatics.com) |

---

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your API key

```bash
export SPEECHMATICS_API_KEY=your_api_key_here
```

### 3. Start the backend server

```bash
python -m src.python.server
# Server running at http://localhost:8000
```

### 4. Open the dashboard

Open `dashboard/index.html` in your browser — it connects automatically to `localhost:8000` and begins streaming transcripts as you speak.

### 5. Transcribe a file

```bash
python -m src.python.client --file audio/sample.wav --language en
```

---

## REST + SSE API

| Endpoint | Method | Description |
|---|---|---|
| `/session/start` | POST | Begin a new transcription session |
| `/session/stop` | POST | End the active session |
| `/session/status` | GET | Return session state and analytics |
| `/transcript/stream` | GET (SSE) | Server-Sent Events stream of live words |
| `/transcript/export` | GET | Export full transcript as JSON or plain text |

### SSE event format

```json
{
  "type": "word",
  "word": "hello",
  "confidence": 0.97,
  "speaker": "S1",
  "start_time": 1.42,
  "end_time": 1.81
}
```

---

## Running the test suite

```bash
pytest tests/ -v --tb=short
pytest tests/ --cov=src --cov-report=term-missing
```

Tests cover WebSocket connection lifecycle, session analytics calculations, SSE event formatting, and FastAPI endpoint responses — all with mocked Speechmatics fixtures (no live API calls required).

---

## Dashboard

The JavaScript dashboard (`dashboard/index.html`) connects to the SSE stream and renders:

- Live word stream with confidence colour-coding (green ≥ 0.9, amber ≥ 0.7, red < 0.7)
- Speaker labels per utterance
- Running word count and words-per-minute
- Session duration timer
- One-click transcript export to clipboard or `.txt`

No build step required — vanilla JavaScript, runs directly in the browser.

---

## Audio modes

**Microphone (live):** The dashboard uses the browser `MediaRecorder` API to capture audio and POST chunks to the backend, which forwards them over the Speechmatics WebSocket.

**File (batch):** Pass `--file` to the CLI client. Supports WAV, MP3, FLAC, and OGG. Audio is chunked into 100ms frames before streaming to preserve real-time behaviour.

---

## Configuration

| Variable | Description | Default |
|---|---|---|
| `SPEECHMATICS_API_KEY` | Your Speechmatics API key | required |
| `SPEECHMATICS_LANGUAGE` | BCP-47 language code | `en` |
| `CHUNK_DURATION_MS` | Audio chunk size in milliseconds | `100` |
| `MAX_DELAY_MS` | Max transcript delivery delay | `700` |
| `PORT` | FastAPI server port | `8000` |

---

## Extending this project

The session analytics module (`session.py`) is designed to be extended. Possible additions:

- Punctuation restoration post-processing
- Keyword extraction and entity recognition
- Translation via a secondary API (e.g. DeepL)
- Storage to PostgreSQL for multi-session review

---

## License

MIT
