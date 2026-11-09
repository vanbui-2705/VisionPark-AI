import hashlib
import json
from pathlib import Path

from app.alpr.interface import ALPRRuntime
from app.alpr.schema import ALPRResult
from scripts.release_gate import BenchmarkRunner, GateStatus, run_quality_gate


class RecordingRuntime(ALPRRuntime):
    def __init__(self, results: dict[bytes, str | None], *, ready: bool = True) -> None:
        self.results = results
        self.ready = ready
        self.received: list[bytes] = []

    @property
    def model_version(self) -> str:
        return "test-real-provider-v1"

    def is_ready(self) -> tuple[bool, str]:
        return self.ready, "ready" if self.ready else "model unavailable"

    def detect_and_read(self, image_bytes: bytes, settings=None) -> ALPRResult:
        self.received.append(image_bytes)
        plate = self.results[image_bytes]
        return ALPRResult(
            plate_number=plate,
            normalized_plate=plate,
            confidence=0.95 if plate else 0.0,
            processing_time_ms=25,
            requires_confirmation=False,
            model_version=self.model_version,
            provider="real-test-double",
        )


def _write_release_dataset(tmp_path: Path) -> tuple[Path, dict[bytes, str | None]]:
    scenarios = [
        ("smoke", "success"),
        ("validation", "no-plate"),
        ("validation", "low-confidence"),
        ("demo", "blur"),
        ("demo", "dark"),
        ("edge_cases", "oblique"),
        ("edge_cases", "small-or-partial"),
        ("edge_cases", "negative"),
    ]
    splits: dict[str, list[dict]] = {
        "smoke": [],
        "validation": [],
        "demo": [],
        "edge_cases": [],
    }
    results: dict[bytes, str | None] = {}
    for index, (split, scenario) in enumerate(scenarios):
        body = f"real-media-{index}".encode()
        media = tmp_path / f"case-{index}.jpg"
        media.write_bytes(body)
        expected = None if scenario in {"no-plate", "negative"} else "29A12345"
        results[body] = expected
        splits[split].append(
            {
                "id": f"case-{index}",
                "vehicle_id": f"vehicle-{index}",
                "image": media.name,
                "expected_plate": expected,
                "scenario": scenario,
                "sha256": hashlib.sha256(body).hexdigest(),
            }
        )

    dataset = tmp_path / "release.json"
    dataset.write_text(
        json.dumps(
            {
                "provenance": {
                    "source": "test fixtures",
                    "usage_rights": "test-only",
                    "annotation_policy": "independent labels",
                    "dataset_version": "1",
                },
                "splits": splits,
            }
        ),
        encoding="utf-8",
    )
    return dataset, results


def test_runner_reads_media_bytes_instead_of_generating_from_ground_truth(tmp_path):
    media = tmp_path / "capture.jpg"
    media.write_bytes(b"original-image-bytes-without-the-plate-label")
    runtime = RecordingRuntime({media.read_bytes(): "30F12345"})
    runner = BenchmarkRunner(runtime, tmp_path / "dataset.json")

    row = runner.run_case(
        {
            "id": "real-case",
            "image": media.name,
            "expected_plate": "30F12345",
            "scenario": "success",
        },
        "validation",
    )

    assert runtime.received == [b"original-image-bytes-without-the-plate-label"]
    assert row["exact_match"] is True
    assert row["input_kind"] == "IMAGE_UPLOAD"


def test_quality_gate_passes_only_after_real_media_inference(tmp_path):
    dataset, results = _write_release_dataset(tmp_path)
    runtime = RecordingRuntime(results)

    status, report = run_quality_gate(dataset, runtime=runtime)

    assert status == GateStatus.PASS
    assert report["status"] == GateStatus.PASS
    assert report["metrics"]["exact_match_rate"] == 1.0
    assert len(runtime.received) == 7  # smoke is validated but not scored by default


def test_quality_gate_holds_when_release_media_is_missing(tmp_path):
    dataset, results = _write_release_dataset(tmp_path)
    first_media = next(tmp_path.glob("case-*.jpg"))
    first_media.unlink()
    runtime = RecordingRuntime(results)

    status, report = run_quality_gate(dataset, runtime=runtime)

    assert status == GateStatus.HOLD
    assert report["status"] == GateStatus.HOLD
    assert any("does not exist" in reason for reason in report["reasons"])
    assert runtime.received == []


def test_quality_gate_holds_when_real_provider_is_not_ready(tmp_path):
    dataset, results = _write_release_dataset(tmp_path)
    runtime = RecordingRuntime(results, ready=False)

    status, report = run_quality_gate(dataset, runtime=runtime)

    assert status == GateStatus.HOLD
    assert report["runtime"]["ready"] is False
    assert report["reasons"] == ["model unavailable"]


def test_quality_gate_fails_when_inference_does_not_meet_threshold(tmp_path):
    dataset, results = _write_release_dataset(tmp_path)
    wrong_results = {body: "00Z00000" for body in results}
    runtime = RecordingRuntime(wrong_results)

    status, report = run_quality_gate(dataset, runtime=runtime)

    assert status == GateStatus.FAIL
    assert report["status"] == GateStatus.FAIL
    assert report["metrics"]["exact_match_rate"] < 0.8
