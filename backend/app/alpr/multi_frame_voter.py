"""Multi-frame voting for ALPR plate recognition results."""

from __future__ import annotations

import math
import threading
import time
from collections import Counter, deque
from typing import NamedTuple

MIN_WINDOW_SIZE = 2
MAX_WINDOW_SIZE = 30


class VotingEntry(NamedTuple):
    """One plate recognition result from a frame."""

    plate: str
    confidence: float
    timestamp: float


class VoteResult(NamedTuple):
    """Aggregated result from the current voting window."""

    plate: str
    confidence: float
    frequency: int
    total_frames: int


class MultiFrameVoter:
    """Aggregate plate detections over a sliding window of frames.

    The most frequently detected plate wins. If multiple plates have the
    same frequency, the plate with the highest individual confidence wins.
    The returned confidence is the highest confidence among detections of
    the winning plate.
    """

    def __init__(self, window_size: int = 5) -> None:
        if isinstance(window_size, bool) or not isinstance(window_size, int):
            raise TypeError("window_size must be an integer")
        if not MIN_WINDOW_SIZE <= window_size <= MAX_WINDOW_SIZE:
            raise ValueError(
                f"window_size must be between {MIN_WINDOW_SIZE} "
                f"and {MAX_WINDOW_SIZE}"
            )

        self.window_size = window_size
        self._buffer: deque[VotingEntry] = deque(maxlen=window_size)
        self._lock = threading.Lock()

    def push(
        self,
        plate: str | None,
        confidence: float,
        timestamp: float | None = None,
    ) -> None:
        """Add a detection to the sliding window.

        Empty or missing plate values are ignored. Confidence must be a
        finite number in the inclusive range [0, 1]. If timestamp is omitted,
        a monotonic timestamp is generated.
        """
        if plate is None or (isinstance(plate, str) and not plate.strip()):
            return
        if not isinstance(plate, str):
            raise TypeError("plate must be a string or None")

        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError) as exc:
            raise TypeError("confidence must be a number") from exc

        if not math.isfinite(confidence_value):
            raise ValueError("confidence must be finite")
        if not 0.0 <= confidence_value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        if timestamp is None:
            timestamp_value = time.monotonic()
        else:
            try:
                timestamp_value = float(timestamp)
            except (TypeError, ValueError) as exc:
                raise TypeError("timestamp must be a number") from exc
            if not math.isfinite(timestamp_value):
                raise ValueError("timestamp must be finite")

        entry = VotingEntry(
            plate=plate.strip(),
            confidence=confidence_value,
            timestamp=timestamp_value,
        )
        with self._lock:
            self._buffer.append(entry)

    def vote(self) -> VoteResult | None:
        """Return the winning plate for the current window, if any."""
        with self._lock:
            if not self._buffer:
                return None

            counts = Counter(entry.plate for entry in self._buffer)
            highest_frequency = max(counts.values())
            candidates = [
                plate
                for plate, frequency in counts.items()
                if frequency == highest_frequency
            ]

            # In a frequency tie, compare the highest confidence for each
            # candidate. max() preserves the first candidate on an exact tie.
            winning_plate = max(
                candidates,
                key=lambda candidate: max(
                    entry.confidence
                    for entry in self._buffer
                    if entry.plate == candidate
                ),
            )
            winning_entries = [
                entry for entry in self._buffer
                if entry.plate == winning_plate
            ]

            return VoteResult(
                plate=winning_plate,
                confidence=max(entry.confidence for entry in winning_entries),
                frequency=len(winning_entries),
                total_frames=len(self._buffer),
            )

    def reset(self) -> None:
        """Clear all detections from the current window."""
        with self._lock:
            self._buffer.clear()

    def is_stable(self) -> bool:
        """Return whether the winning plate reaches the required threshold.

        The threshold follows the project specification:
        ceil(window_size / 2). For an even-sized window this is half the
        window, not a strict mathematical majority.
        """
        with self._lock:
            if not self._buffer:
                return False

            counts = Counter(entry.plate for entry in self._buffer)
            threshold = math.ceil(self.window_size / 2)
            return max(counts.values()) >= threshold

    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)

    def __repr__(self) -> str:
        with self._lock:
            return (
                f"{self.__class__.__name__}("
                f"window_size={self.window_size}, "
                f"buffer_size={len(self._buffer)})"
            )
