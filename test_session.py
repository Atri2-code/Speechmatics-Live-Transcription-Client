"""Unit tests for Session analytics — no I/O, pure logic."""

import time
import pytest

from src.python.client import TranscriptWord
from src.python.session import Session, SessionState


def _word(text="hello", confidence=0.95, speaker="S1"):
    return TranscriptWord(
        word=text, confidence=confidence, speaker=speaker,
        start_time=0.0, end_time=0.5
    )


def test_session_starts_idle():
    s = Session()
    assert s.state == SessionState.IDLE
    assert s.word_count == 0


def test_session_start_clears_state():
    s = Session()
    s.start()
    s.add_word(_word("hello"))
    s.start()  # restart
    assert s.word_count == 0


def test_add_word_increments_count():
    s = Session()
    s.start()
    s.add_word(_word("hello"))
    s.add_word(_word("world"))
    assert s.word_count == 2


def test_add_word_ignored_when_not_active():
    s = Session()
    s.add_word(_word("ignored"))
    assert s.word_count == 0


def test_avg_confidence():
    s = Session()
    s.start()
    s.add_word(_word(confidence=1.0))
    s.add_word(_word(confidence=0.8))
    assert s.avg_confidence == pytest.approx(0.9, abs=0.001)


def test_transcript_text():
    s = Session()
    s.start()
    s.add_word(_word("the"))
    s.add_word(_word("quick"))
    s.add_word(_word("brown"))
    assert s.transcript_text == "the quick brown"


def test_speaker_stats_tracked():
    s = Session()
    s.start()
    s.add_word(_word("hello", speaker="S1"))
    s.add_word(_word("hi", speaker="S2"))
    s.add_word(_word("there", speaker="S1"))
    assert s.speakers["S1"].word_count == 2
    assert s.speakers["S2"].word_count == 1


def test_speaker_avg_confidence():
    s = Session()
    s.start()
    s.add_word(_word(confidence=0.9, speaker="S1"))
    s.add_word(_word(confidence=0.7, speaker="S1"))
    assert s.speakers["S1"].avg_confidence == pytest.approx(0.8, abs=0.001)


def test_to_dict_contains_required_keys():
    s = Session()
    s.start()
    d = s.to_dict()
    assert "state" in d
    assert "word_count" in d
    assert "words_per_minute" in d
    assert "avg_confidence" in d
    assert "speakers" in d
    assert "duration_seconds" in d


def test_wpm_zero_before_any_words():
    s = Session()
    s.start()
    assert s.words_per_minute == 0.0


def test_session_duration_increases():
    s = Session()
    s.start()
    time.sleep(0.05)
    assert s.duration_seconds >= 0.04


def test_stop_freezes_duration():
    s = Session()
    s.start()
    time.sleep(0.05)
    s.stop()
    d1 = s.duration_seconds
    time.sleep(0.05)
    d2 = s.duration_seconds
    assert d1 == d2
