"""
Speechmatics real-time WebSocket streaming client.

Connects to the Speechmatics RT API, streams audio chunks,
and yields TranscriptWord events as they arrive.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import AsyncGenerator

import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

logger = logging.getLogger(__name__)

SPEECHMATICS_RT_URL = "wss://eu2.rt.speechmatics.com/v2"
API_KEY = os.environ.get("SPEECHMATICS_API_KEY", "")
CHUNK_DURATION_MS = int(os.environ.get("CHUNK_DURATION_MS", "100"))


@dataclass
class TranscriptWord:
    word: str
    confidence: float
    speaker: str
    start_time: float
    end_time: float

    def to_sse(self) -> str:
        payload = json.dumps({
            "type": "word",
            "word": self.word,
            "confidence": round(self.confidence, 3),
            "speaker": self.speaker,
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3),
        })
        return f"data: {payload}\n\n"


class SpeechmaticsClient:
    """
    Manages the WebSocket connection lifecycle with the Speechmatics RT API.

    Usage:
        async with SpeechmaticsClient(language="en") as client:
            async for word in client.stream(audio_generator):
                print(word)
    """

    def __init__(self, language: str = "en", api_key: str | None = None):
        self.language = language
        self.api_key = api_key or API_KEY
        self._ws = None

    async def __aenter__(self):
        await self._connect()
        return self

    async def __aexit__(self, *args):
        await self._disconnect()

    async def _connect(self):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{SPEECHMATICS_RT_URL}/{self.language}"
        logger.info("Connecting to Speechmatics RT: %s", url)
        self._ws = await websockets.connect(url, additional_headers=headers)
        await self._send_start_recognition()
        logger.info("Connected — recognition started")

    async def _send_start_recognition(self):
        config = {
            "message": "StartRecognition",
            "audio_format": {
                "type": "raw",
                "encoding": "pcm_f32le",
                "sample_rate": 16000,
            },
            "transcription_config": {
                "language": self.language,
                "enable_partials": False,
                "diarization": "speaker",
                "max_delay": float(os.environ.get("MAX_DELAY_MS", "700")) / 1000,
            },
        }
        await self._ws.send(json.dumps(config))

    async def _disconnect(self):
        if self._ws:
            try:
                await self._ws.send(json.dumps({"message": "EndOfStream", "last_seq_no": 0}))
            except WebSocketException:
                pass
            finally:
                await self._ws.close()
                logger.info("Disconnected from Speechmatics RT")

    async def stream(
        self, audio_chunks: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[TranscriptWord, None]:
        """
        Send audio chunks and yield TranscriptWord events as they arrive.
        Runs send and receive concurrently.
        """
        send_task = asyncio.create_task(self._send_audio(audio_chunks))
        try:
            async for word in self._receive_transcripts():
                yield word
        except ConnectionClosedError as exc:
            logger.warning("WebSocket closed: %s", exc)
        finally:
            send_task.cancel()

    async def _send_audio(self, audio_chunks: AsyncGenerator[bytes, None]):
        seq = 0
        async for chunk in audio_chunks:
            if self._ws is None:
                break
            await self._ws.send(chunk)
            seq += 1
            logger.debug("Sent audio chunk #%d (%d bytes)", seq, len(chunk))

    async def _receive_transcripts(self) -> AsyncGenerator[TranscriptWord, None]:
        async for raw in self._ws:
            message = json.loads(raw)
            msg_type = message.get("message")

            if msg_type == "AddTranscript":
                for result in message.get("results", []):
                    for alt in result.get("alternatives", []):
                        yield TranscriptWord(
                            word=alt.get("content", ""),
                            confidence=alt.get("confidence", 0.0),
                            speaker=result.get("channel", "S1"),
                            start_time=result.get("start_time", 0.0),
                            end_time=result.get("end_time", 0.0),
                        )

            elif msg_type == "EndOfTranscript":
                logger.info("Speechmatics signalled end of transcript")
                return

            elif msg_type == "Error":
                logger.error("Speechmatics error: %s", message.get("reason"))
                raise RuntimeError(f"Speechmatics API error: {message.get('reason')}")
