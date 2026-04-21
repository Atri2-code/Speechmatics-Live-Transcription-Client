"""
Session state and real-time analytics.

Tracks transcript words as they arrive and computes
running analytics: word count, WPM, speaker breakdown,
average confidence, and session duration.
"""

import time
from dataclasses import dataclass, field
from enum import Enum, auto

from .client import TranscriptWord


class SessionState(Enum):
    IDLE = auto()
    ACTIVE = auto()
    STOPPED = auto()


@dataclass
class SpeakerStats:
    word_count: int = 0
    total_confidence: float = 0.0

    @property
    def avg_confidence(self) -> float:
        if self.word_count == 0:
            return 0.0
        return round(self.total_confidence / self.word_count, 3)


@dataclass
class Session:
    """
    Holds all state for a single transcription session.
    Thread-safe for single-threaded async use.
    """
    language: str = "en"
    state: SessionState = SessionState.IDLE
    words: list[TranscriptWord] = field(default_factory=list)
    speakers: dict[str, SpeakerStats] = field(default_factory=dict)
    started_at: float | None = None
    stopped_at: float | None = None

    def start(self):
        self.state = SessionState.ACTIVE
        self.started_at = time.monotonic()
        self.words.clear()
        self.speakers.clear()

    def stop(self):
        self.state = SessionState.STOPPED
        self.stopped_at = time.monotonic()

    def add_word(self, word: TranscriptWord):
        if self.state != SessionState.ACTIVE:
            return
        self.words.append(word)
        if word.speaker not in self.speakers:
            self.speakers[word.speaker] = SpeakerStats()
        stats = self.speakers[word.speaker]
        stats.word_count += 1
        stats.total_confidence += word.confidence

    @property
    def duration_seconds(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.stopped_at or time.monotonic()
        return round(end - self.started_at, 2)

    @property
    def word_count(self) -> int:
        return len(self.words)

    @property
    def words_per_minute(self) -> float:
        minutes = self.duration_seconds / 60
        if minutes == 0:
            return 0.0
        return round(self.word_count / minutes, 1)

    @property
    def avg_confidence(self) -> float:
        if not self.words:
            return 0.0
        return round(sum(w.confidence for w in self.words) / len(self.words), 3)

    @property
    def transcript_text(self) -> str:
        return " ".join(w.word for w in self.words)

    def to_dict(self) -> dict:
        return {
            "state": self.state.name,
            "language": self.language,
            "duration_seconds": self.duration_seconds,
            "word_count": self.word_count,
            "words_per_minute": self.words_per_minute,
            "avg_confidence": self.avg_confidence,
            "speakers": {
                spk: {
                    "word_count": stats.word_count,
                    "avg_confidence": stats.avg_confidence,
                }
                for spk, stats in self.speakers.items()
            },
        }
