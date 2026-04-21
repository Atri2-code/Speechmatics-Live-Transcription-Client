"""
Audio capture module.

Provides async generators for both live microphone capture
and chunked file-based audio streaming, normalised to 16kHz PCM float32.
"""

import asyncio
import logging
import struct
import wave
from pathlib import Path
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_FRAMES = SAMPLE_RATE // 10  # 100ms chunks


async def microphone_stream() -> AsyncGenerator[bytes, None]:
    """
    Capture audio from the default microphone in 100ms PCM chunks.
    Requires PyAudio. Falls back gracefully if no device is available.
    """
    try:
        import pyaudio
    except ImportError as exc:
        raise RuntimeError(
            "PyAudio not installed — run: pip install pyaudio"
        ) from exc

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paFloat32,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_FRAMES,
    )

    logger.info("Microphone capture started — sample_rate=%d chunk_frames=%d",
                SAMPLE_RATE, CHUNK_FRAMES)

    try:
        while True:
            chunk = await asyncio.to_thread(
                stream.read, CHUNK_FRAMES, exception_on_overflow=False
            )
            yield chunk
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        logger.info("Microphone capture stopped")


async def file_stream(path: str | Path) -> AsyncGenerator[bytes, None]:
    """
    Stream a WAV audio file in 100ms PCM float32 chunks.
    Non-WAV formats require ffmpeg pre-conversion.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    logger.info("Streaming audio file: %s", path)

    with wave.open(str(path), "rb") as wf:
        if wf.getnchannels() != CHANNELS:
            logger.warning(
                "File has %d channels — expected mono. "
                "Transcription may be degraded.",
                wf.getnchannels(),
            )

        total_frames = wf.getnframes()
        frames_read = 0

        while frames_read < total_frames:
            raw = wf.readframes(CHUNK_FRAMES)
            if not raw:
                break

            # Convert 16-bit PCM to float32 PCM for Speechmatics raw format
            n_samples = len(raw) // 2
            samples = struct.unpack(f"{n_samples}h", raw)
            float_samples = [s / 32768.0 for s in samples]
            chunk = struct.pack(f"{n_samples}f", *float_samples)

            yield chunk
            frames_read += CHUNK_FRAMES

            # Simulate real-time pacing so server is not overwhelmed
            await asyncio.sleep(CHUNK_FRAMES / SAMPLE_RATE)

    logger.info("File stream complete: %s", path)
