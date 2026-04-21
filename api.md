# API reference

Base URL: `http://localhost:8000`

Interactive docs available at `/docs` (Swagger UI) and `/redoc` when the server is running.

---

## Session endpoints

### `POST /session/start`

Begin a new transcription session and connect to the Speechmatics RT API.

**Query parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `language` | string | `en` | BCP-47 language code |

**Response `200`**
```json
{ "status": "started", "language": "en" }
```

**Response `409`** — session already active.

---

### `POST /session/stop`

End the active session and disconnect from Speechmatics.

**Response `200`**
```json
{
  "status": "stopped",
  "analytics": {
    "state": "STOPPED",
    "language": "en",
    "duration_seconds": 47.2,
    "word_count": 183,
    "words_per_minute": 232.6,
    "avg_confidence": 0.934,
    "speakers": {
      "S1": { "word_count": 120, "avg_confidence": 0.951 },
      "S2": { "word_count": 63,  "avg_confidence": 0.902 }
    }
  }
}
```

**Response `409`** — no active session.

---

### `GET /session/status`

Return current session state and running analytics.

**Response `200`** — same schema as the analytics object above.

---

## Transcript endpoints

### `GET /transcript/stream`

Server-Sent Events stream. Connect once per session; words are pushed as they arrive from Speechmatics.

**Event types**

| Type | Description |
|---|---|
| `connected` | Emitted immediately on connection |
| `word` | A transcribed word with metadata |
| `keepalive` | Emitted every 15s when idle — prevents proxy timeouts |

**Word event payload**
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

**JavaScript example**
```javascript
const source = new EventSource("http://localhost:8000/transcript/stream");
source.onmessage = (e) => {
  const event = JSON.parse(e.data);
  if (event.type === "word") console.log(event.word);
};
```

---

### `GET /transcript/export`

Export the full transcript for the current or most recent session.

**Query parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `fmt` | `json` \| `text` | `json` | Output format |

**Response `200` (fmt=text)**
```json
{ "transcript": "the quick brown fox jumps over the lazy dog" }
```

**Response `200` (fmt=json)**
```json
{
  "transcript": [
    {
      "word": "the",
      "confidence": 0.99,
      "speaker": "S1",
      "start_time": 0.12,
      "end_time": 0.28
    }
  ],
  "analytics": { ... }
}
```
