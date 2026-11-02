"""Unit tests for MultiFrameVoter."""

import threading

import pytest

from app.alpr.multi_frame_voter import (
    MAX_WINDOW_SIZE,
    MIN_WINDOW_SIZE,
    MultiFrameVoter,
    VoteResult,
    VotingEntry,
)


class TestMultiFrameVoterInitialization:
    def test_default_window_size(self):
        voter = MultiFrameVoter()
        assert voter.window_size == 5
        assert len(voter) == 0

    def test_custom_window_size(self):
        voter = MultiFrameVoter(window_size=10)
        assert voter.window_size == 10

    @pytest.mark.parametrize("window_size", [MIN_WINDOW_SIZE, MAX_WINDOW_SIZE])
    def test_boundary_window_sizes(self, window_size):
        assert MultiFrameVoter(window_size).window_size == window_size

    @pytest.mark.parametrize("window_size", [MIN_WINDOW_SIZE - 1, MAX_WINDOW_SIZE + 1])
    def test_window_size_out_of_range_raises_value_error(self, window_size):
        with pytest.raises(ValueError):
            MultiFrameVoter(window_size)

    @pytest.mark.parametrize("window_size", [5.0, "5", None, True, False])
    def test_non_integer_window_size_raises_type_error(self, window_size):
        with pytest.raises(TypeError):
            MultiFrameVoter(window_size)

    def test_repr_contains_window_and_buffer_size(self):
        assert repr(MultiFrameVoter(5)) == ("MultiFrameVoter(window_size=5, buffer_size=0)")


class TestPushAndBuffer:
    def test_empty_voter_has_no_vote(self):
        voter = MultiFrameVoter()
        assert voter.vote() is None
        assert voter.is_stable() is False

    def test_push_single_detection(self):
        voter = MultiFrameVoter()
        voter.push("30A-12345", 0.9)
        result = voter.vote()

        assert result == VoteResult(
            plate="30A-12345",
            confidence=0.9,
            frequency=1,
            total_frames=1,
        )
        assert len(voter) == 1
        assert voter.is_stable() is False

    @pytest.mark.parametrize("plate", [None, "", "   "])
    def test_missing_or_empty_plate_is_ignored(self, plate):
        voter = MultiFrameVoter()
        voter.push(plate, 0.9)
        assert len(voter) == 0
        assert voter.vote() is None

    def test_plate_is_stripped_before_storing(self):
        voter = MultiFrameVoter()
        voter.push("  30A-12345  ", 0.9)
        assert voter.vote().plate == "30A-12345"

    def test_custom_timestamp_is_stored(self):
        voter = MultiFrameVoter()
        voter.push("30A-12345", 0.9, timestamp=123.5)

        with voter._lock:
            entry = voter._buffer[0]

        assert isinstance(entry, VotingEntry)
        assert entry.timestamp == 123.5

    def test_default_timestamp_is_monotonic_number(self):
        voter = MultiFrameVoter()
        voter.push("30A-12345", 0.9)

        with voter._lock:
            timestamp = voter._buffer[0].timestamp

        assert isinstance(timestamp, float)
        assert timestamp > 0


class TestVoting:
    def test_unanimous_vote(self):
        voter = MultiFrameVoter(5)
        for _ in range(5):
            voter.push("30A-12345", 0.9)

        result = voter.vote()
        assert result.plate == "30A-12345"
        assert result.confidence == 0.9
        assert result.frequency == 5
        assert result.total_frames == 5

    def test_majority_vote_three_out_of_five(self):
        voter = MultiFrameVoter(5)
        voter.push("30A-12345", 0.8)
        voter.push("29B-67890", 0.95)
        voter.push("30A-12345", 0.9)
        voter.push("29B-67890", 0.7)
        voter.push("30A-12345", 0.85)

        result = voter.vote()
        assert result.plate == "30A-12345"
        assert result.frequency == 3
        assert result.total_frames == 5
        assert result.confidence == 0.9

    def test_frequency_tie_is_broken_by_highest_confidence(self):
        voter = MultiFrameVoter(4)
        voter.push("30A-12345", 0.70)
        voter.push("30A-12345", 0.75)
        voter.push("29B-67890", 0.80)
        voter.push("29B-67890", 0.95)

        result = voter.vote()
        assert result.plate == "29B-67890"
        assert result.frequency == 2
        assert result.confidence == 0.95

    def test_exact_frequency_and_confidence_tie_is_deterministic(self):
        voter = MultiFrameVoter(2)
        voter.push("30A-12345", 0.9)
        voter.push("29B-67890", 0.9)

        # Both candidates are equally ranked; the first-seen plate wins.
        assert voter.vote().plate == "30A-12345"

    def test_three_different_plates(self):
        voter = MultiFrameVoter(5)
        voter.push("30A-12345", 0.9)
        voter.push("29B-67890", 0.8)
        voter.push("31C-11111", 0.7)

        result = voter.vote()
        assert result.frequency == 1
        assert result.total_frames == 3
        assert voter.is_stable() is False

    def test_vote_result_is_named_tuple(self):
        voter = MultiFrameVoter()
        voter.push("30A-12345", 0.9)
        result = voter.vote()

        assert isinstance(result, VoteResult)
        assert result._fields == ("plate", "confidence", "frequency", "total_frames")


class TestSlidingWindow:
    def test_oldest_detection_is_evicted_when_window_is_full(self):
        voter = MultiFrameVoter(3)
        voter.push("OLD-111", 0.99)
        voter.push("NEW-222", 0.8)
        voter.push("NEW-222", 0.85)
        voter.push("NEW-222", 0.9)

        result = voter.vote()
        assert len(voter) == 3
        assert result.plate == "NEW-222"
        assert result.frequency == 3
        assert result.total_frames == 3

    def test_buffer_never_exceeds_window_size(self):
        voter = MultiFrameVoter(3)
        for index in range(10):
            voter.push(f"PLATE-{index}", 0.8)

        assert len(voter) == 3
        assert voter.vote().total_frames == 3

    def test_reset_clears_buffer_and_vote(self):
        voter = MultiFrameVoter(3)
        for _ in range(3):
            voter.push("30A-12345", 0.9)

        voter.reset()

        assert len(voter) == 0
        assert voter.vote() is None
        assert voter.is_stable() is False

    def test_can_push_after_reset(self):
        voter = MultiFrameVoter(3)
        voter.push("30A-12345", 0.9)
        voter.reset()
        voter.push("29B-67890", 0.8)

        assert voter.vote().plate == "29B-67890"
        assert len(voter) == 1


class TestStability:
    def test_three_out_of_five_is_stable(self):
        voter = MultiFrameVoter(5)
        voter.push("30A-12345", 0.9)
        voter.push("29B-67890", 0.8)
        voter.push("30A-12345", 0.85)
        voter.push("29B-67890", 0.7)
        voter.push("30A-12345", 0.88)

        assert voter.is_stable() is True

    def test_two_out_of_five_is_not_stable(self):
        voter = MultiFrameVoter(5)
        voter.push("30A-12345", 0.9)
        voter.push("30A-12345", 0.85)
        voter.push("29B-67890", 0.8)
        voter.push("29B-67890", 0.75)
        voter.push("31C-11111", 0.7)

        assert voter.is_stable() is False

    def test_even_window_uses_ceil_half_threshold_from_spec(self):
        voter = MultiFrameVoter(4)
        voter.push("30A-12345", 0.9)
        voter.push("30A-12345", 0.85)

        # ceil(4 / 2) == 2, according to the task specification.
        assert voter.is_stable() is True

    def test_single_frame_is_not_stable(self):
        voter = MultiFrameVoter(5)
        voter.push("30A-12345", 0.9)
        assert voter.is_stable() is False


class TestInputValidation:
    @pytest.mark.parametrize("confidence", [-0.01, 1.01])
    def test_confidence_out_of_range_raises_value_error(self, confidence):
        voter = MultiFrameVoter()
        with pytest.raises(ValueError):
            voter.push("30A-12345", confidence)

    @pytest.mark.parametrize("confidence", [float("nan"), float("inf"), -float("inf")])
    def test_non_finite_confidence_raises_value_error(self, confidence):
        voter = MultiFrameVoter()
        with pytest.raises(ValueError):
            voter.push("30A-12345", confidence)

    @pytest.mark.parametrize("confidence", ["not-a-number", None])
    def test_non_numeric_confidence_raises_type_error(self, confidence):
        voter = MultiFrameVoter()
        with pytest.raises(TypeError):
            voter.push("30A-12345", confidence)

    def test_non_string_plate_raises_type_error(self):
        voter = MultiFrameVoter()
        with pytest.raises(TypeError):
            voter.push(12345, 0.9)

    def test_non_finite_timestamp_raises_value_error(self):
        voter = MultiFrameVoter()
        with pytest.raises(ValueError):
            voter.push("30A-12345", 0.9, timestamp=float("nan"))


class TestThreadSafety:
    def test_concurrent_pushes_do_not_exceed_window_size(self):
        voter = MultiFrameVoter(30)
        thread_count = 8
        pushes_per_thread = 100

        def worker(thread_id):
            for index in range(pushes_per_thread):
                voter.push(f"PLATE-{thread_id}-{index}", 0.8)

        threads = [
            threading.Thread(target=worker, args=(thread_id,)) for thread_id in range(thread_count)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(voter) == 30
        assert voter.vote().total_frames == 30

    def test_concurrent_push_and_vote(self):
        voter = MultiFrameVoter(10)
        errors = []

        def push_worker():
            try:
                for index in range(200):
                    voter.push(f"PLATE-{index % 3}", 0.8)
            except Exception as exc:  # pragma: no cover - defensive thread check
                errors.append(exc)

        def vote_worker():
            try:
                for _ in range(200):
                    result = voter.vote()
                    if result is not None:
                        assert 1 <= result.frequency <= result.total_frames
                        assert result.total_frames <= voter.window_size
            except Exception as exc:  # pragma: no cover - defensive thread check
                errors.append(exc)

        threads = [
            threading.Thread(target=push_worker),
            threading.Thread(target=vote_worker),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == []
        assert len(voter) <= voter.window_size
