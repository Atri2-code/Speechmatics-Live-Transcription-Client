"""
FastAPI backend — REST endpoints and SSE transcript stream.

Bridges the Speechmatics WebSocket client with the browser dashboard
via Server-Sent Events (SSE), enabling live word-by-word delivery.
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .client import SpeechmaticsClient
from .session import Session, SessionState

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

session = Session()
word_queue: asyncio.Queue = asyncio.Queue()
streaming_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Speechmatics live transcription server starting")
    yield
    logger.info("Server shutting down")
    if streaming_task:
        streaming_task.cancel()


app = FastAPI(
    title="Speechmatics Live Transcription",
    description="Real-time speech transcription via Speechmatics RT API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")


@app.post("/session/start")
async def start_session(language: str = "en"):
    global streaming_task
    if session.state == SessionState.ACTIVE:
        raise HTTPException(status_code=409, detail="Session already active")

    session.language = language
    session.start()
    streaming_task = asyncio.create_task(_run_streaming(language))
    logger.info("Session started — language: %s", language)
    return {"status": "started", "language": language}


@app.post("/session/stop")
async def stop_session():
    global streaming_task
    if session.state != SessionState.ACTIVE:
        raise HTTPException(status_code=409, detail="No active session")

    session.stop()
    if streaming_task:
        streaming_task.cancel()
        streaming_task = None

    logger.info("Session stopped — %d words transcribed", session.word_count)
    return {"status": "stopped", "analytics": session.to_dict()}


@app.get("/session/status")
async def session_status():
    return session.to_dict()


@app.get("/transcript/stream")
async def transcript_stream():
    """Server-Sent Events stream of live transcript words."""
    async def event_generator():
        yield "data: {\"type\": \"connected\"}\n\n"
        while True:
            try:
                word = await asyncio.wait_for(word_queue.get(), timeout=15.0)
                yield word.to_sse()
            except asyncio.TimeoutError:
                yield "data: {\"type\": \"keepalive\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/transcript/export")
async def export_transcript(fmt: str = "json"):
    if fmt == "text":
        return {"transcript": session.transcript_text}
    return {
        "transcript": [
            {
                "word": w.word,
                "confidence": w.confidence,
                "speaker": w.speaker,
                "start_time": w.start_time,
                "end_time": w.end_time,
            }
            for w in session.words
        ],
        "analytics": session.to_dict(),
    }


async def _run_streaming(language: str):
    """Background task — connects to Speechmatics and pumps words into the queue."""
    from .audio_capture import microphone_stream

    try:
        async with SpeechmaticsClient(language=language) as client:
            async for word in client.stream(microphone_stream()):
                session.add_word(word)
                await word_queue.put(word)
    except asyncio.CancelledError:
        logger.info("Streaming task cancelled")
    except Exception as exc:
        logger.error("Streaming error: %s", exc)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
