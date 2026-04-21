"""Unit tests for SpeechmaticsClient — WebSocket mocked, no live API calls."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.python.client import SpeechmaticsClient, TranscriptWord


def _make_word_message(word="hello", confidence=0.95, speaker="S1"):
    return json.dumps({
        "message": "AddTranscript",
        "results": [{
            "alternatives": [{"content": word, "confidence": confidence}],
            "channel": speaker,
            "start_time": 1.0,
            "end_time": 1.5,
        }]
    })


@pytest.fixture()
def mock_ws():
    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_client_sends_start_recognition(mock_ws):
    with patch("websockets.connect", return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_ws), __aexit__=AsyncMock())):
        client = SpeechmaticsClient(language="en", api_key="test-key")
        client._ws = mock_ws
        await client._send_start_recognition()

    call_args = mock_ws.send.call_args[0][0]
    config = json.loads(call_args)
    assert config["message"] == "StartRecognition"
    assert config["transcription_config"]["language"] == "en"
    assert config["transcription_config"]["diarization"] == "speaker"


@pytest.mark.asyncio
async def test_receive_transcripts_yields_words(mock_ws):
    messages = [
        _make_word_message("hello", 0.98, "S1"),
        _make_word_message("world", 0.87, "S1"),
        json.dumps({"message": "EndOfTranscript"}),
    ]
    mock_ws.__aiter__ = MagicMock(return_value=iter(messages))

    client = SpeechmaticsClient(language="en", api_key="test-key")
    client._ws = mock_ws

    words = []
    async for word in client._receive_transcripts():
        words.append(word)

    assert len(words) == 2
    assert words[0].word == "hello"
    assert words[0].confidence == 0.98
    assert words[1].word == "world"


@pytest.mark.asyncio
async def test_receive_transcripts_raises_on_error(mock_ws):
    messages = [json.dumps({"message": "Error", "reason": "Invalid API key"})]
    mock_ws.__aiter__ = MagicMock(return_value=iter(messages))

    client = SpeechmaticsClient(language="en", api_key="bad-key")
    client._ws = mock_ws

    with pytest.raises(RuntimeError, match="Invalid API key"):
        async for _ in client._receive_transcripts():
            pass


def test_transcript_word_to_sse():
    word = TranscriptWord(
        word="test", confidence=0.91, speaker="S1", start_time=1.0, end_time=1.4
    )
    sse = word.to_sse()
    assert sse.startswith("data: ")
    assert sse.endswith("\n\n")
    payload = json.loads(sse.replace("data: ", "").strip())
    assert payload["word"] == "test"
    assert payload["type"] == "word"
    assert payload["confidence"] == 0.91


def test_transcript_word_confidence_rounded():
    word = TranscriptWord(
        word="hi", confidence=0.912345678, speaker="S1", start_time=0.0, end_time=0.3
    )
    payload = json.loads(word.to_sse().replace("data: ", "").strip())
    assert len(str(payload["confidence"]).split(".")[-1]) <= 3
