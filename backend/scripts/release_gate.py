"""Run the ALPR quality gate against real media and the real provider.

This gate never generates input from ground truth.  Functional workflow checks
belong to ``system_gate.py``; this script only evaluates recognition quality.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any

import cv2

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SPLITS = ["smoke", "validation", "demo", "edge_cases"]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.alpr.dataset_manifest import validate_dataset_manifest  # noqa: E402
from app.alpr.interface import ALPRRuntime  # noqa: E402
from app.alpr.runtime_adapter import create_runtime  # noqa: E402
from app.alpr.utils import normalize_plate  # noqa: E402


class GateStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    HOLD = "HOLD"


class ExitCode(IntEnum):
    PASS = 0
    FAIL = 1
    HOLD = 2


def character_accuracy(expected: str | None, actual: str | None) -> float:
    exp = (normalize_plate(expected, auto_correct=False) if expected else "").upper()
    act = (normalize_plate(actual, auto_correct=False) if actual else "").upper()
    if not exp:
        return 1.0 if not act else 0.0
    previous = list(range(len(act) + 1))
    for row, left in enumerate(exp, 1):
        current = [row]
        for col, right in enumerate(act, 1):
            current.append(
                min(current[-1] + 1, previous[col] + 1, previous[col - 1] + (left != right))
            )
        previous = current
    return max(0.0, 1.0 - previous[-1] / len(exp))


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
    return round(ordered[index], 3)


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=BACKEND_DIR, text=True, timeout=5
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _media_path(dataset: Path, case: dict[str, Any]) -> Path:
    raw_path = case.get("media") or case.get("image")
    if not raw_path:
        raise ValueError(f"Case {case.get('id')!r} has no media/image path")
    path = Path(str(raw_path))
    return path if path.is_absolute() else (dataset.parent / path).resolve()


def _read_inference_bytes(dataset: Path, case: dict[str, Any]) -> tuple[bytes, str]:
    """Read an image or extract one requested frame from a video file."""

    path = _media_path(dataset, case)
    if not path.is_file():
        raise FileNotFoundError(path)

    if path.suffix.lower() not in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        return path.read_bytes(), "IMAGE_UPLOAD"

    capture = cv2.VideoCapture(str(path))
    try:
        requested_ms = int(case.get("video_time_ms", 0))
        if requested_ms > 0:
            capture.set(cv2.CAP_PROP_POS_MSEC, requested_ms)
        success, frame = capture.read()
        if not success or frame is None:
            raise ValueError(f"Could not decode a frame from {path}")
        encoded, buffer = cv2.imencode(".jpg", frame)
        if not encoded:
            raise ValueError(f"Could not encode a frame from {path}")
        return buffer.tobytes(), "VIDEO_FRAME"
    finally:
        capture.release()


class BenchmarkRunner:
    """Run an ALPR runtime on bytes read exclusively from dataset media."""

    def __init__(self, runtime: ALPRRuntime, dataset: Path) -> None:
        self.runtime = runtime
        self.dataset = dataset

    def run_case(self, case: dict[str, Any], split: str) -> dict[str, Any]:
        image_bytes, input_kind = _read_inference_bytes(self.dataset, case)
        started = time.perf_counter()
        result = self.runtime.detect_and_read(image_bytes)
        measured_latency_ms = (time.perf_counter() - started) * 1000

        expected = case.get("expected_plate")
        actual = result.normalized_plate or result.plate_number
        normalized_expected = normalize_plate(expected) if expected else None
        normalized_actual = normalize_plate(actual) if actual else None
        exact = normalized_expected == normalized_actual
        detector_found = result.bbox is not None

        return {
            "id": case.get("id"),
            "split": split,
            "scenario": case.get("scenario"),
            "media": str(_media_path(self.dataset, case)),
            "input_kind": input_kind,
            "expected": normalized_expected,
            "actual": normalized_actual,
            "exact_match": exact,
            "detector_found": detector_found,
            "detector_required": bool(case.get("detector_required", expected is not None)),
            "negative_false_positive": expected is None and normalized_actual is not None,
            "char_accuracy": round(character_accuracy(normalized_expected, normalized_actual), 4),
            "latency_ms": round(float(result.processing_time_ms or measured_latency_ms), 3),
            "confidence": result.confidence,
            "bbox": list(result.bbox.as_tuple) if result.bbox else None,
            "detector_latency_ms": result.detector_latency_ms,
            "ocr_latency_ms": result.ocr_latency_ms,
            "provider": result.provider,
            "model_version": result.model_version,
        }


def evaluate_dataset(
    runtime: ALPRRuntime,
    dataset: Path,
    payload: dict[str, Any],
    splits: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    runner = BenchmarkRunner(runtime, dataset)
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    available_splits = payload.get("splits", {})
    for split in splits:
        for case in available_splits.get(split, []):
            try:
                rows.append(runner.run_case(case, split))
            except Exception as exc:  # report every failed media/inference case
                errors.append(f"{split}/{case.get('id')}: {type(exc).__name__}: {exc}")
    return rows, errors


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    positive = [row for row in rows if row["expected"]]
    negative = [row for row in rows if not row["expected"]]
    detector_scored = [row for row in positive if row["detector_required"]]
    detected_positive = [row for row in detector_scored if row["detector_found"]]
    latencies = [float(row["latency_ms"]) for row in rows]
    return {
        "sample_count": len(rows),
        "positive_count": len(positive),
        "negative_count": len(negative),
        "exact_match_rate": round(
            sum(1 for row in rows if row["exact_match"]) / max(len(rows), 1), 4
        ),
        "positive_exact_match_rate": round(
            sum(1 for row in positive if row["exact_match"]) / max(len(positive), 1), 4
        ),
        "detector_scored_count": len(detector_scored),
        "detector_recall": round(
            sum(1 for row in detector_scored if row["detector_found"])
            / max(len(detector_scored), 1),
            4,
        ),
        "ocr_exact_given_detection": round(
            sum(1 for row in detected_positive if row["exact_match"])
            / max(len(detected_positive), 1),
            4,
        ),
        "negative_false_positive_count": sum(
            1 for row in negative if row["negative_false_positive"]
        ),
        "negative_false_positive_rate": round(
            sum(1 for row in negative if row["negative_false_positive"]) / max(len(negative), 1),
            4,
        ),
        "negative_accuracy": round(
            sum(1 for row in negative if row["exact_match"]) / max(len(negative), 1), 4
        ),
        "positive_character_accuracy": round(
            statistics.mean(row["char_accuracy"] for row in positive) if positive else 0.0,
            4,
        ),
        "latency_ms": {
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
        },
    }


def _base_report(dataset: Path) -> dict[str, Any]:
    return {
        "gate": "ALPR_QUALITY",
        "timestamp": datetime.now(UTC).isoformat(),
        "commit": _git_commit(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "dataset": str(dataset.resolve()),
    }


def run_quality_gate(
    dataset: Path,
    *,
    runtime: ALPRRuntime | None = None,
    splits: list[str] | None = None,
    min_exact_match: float = 0.80,
    min_positive_exact_match: float = 0.80,
    min_detector_recall: float = 0.94,
    min_ocr_exact_given_detection: float = 0.80,
    max_negative_false_positive_rate: float = 0.0,
    max_p95_latency_ms: float = 1000.0,
) -> tuple[GateStatus, dict[str, Any]]:
    """Return a truthful quality status and a machine-readable report."""

    report = _base_report(dataset)
    if not dataset.is_file():
        report.update(status=GateStatus.HOLD, reasons=["Dataset manifest does not exist"])
        return GateStatus.HOLD, report

    validation = validate_dataset_manifest(dataset, release=True)
    report["dataset_validation"] = validation
    if not validation["release_ready"]:
        report.update(
            status=GateStatus.HOLD,
            reasons=[*validation.get("errors", []), *validation.get("warnings", [])],
        )
        return GateStatus.HOLD, report

    runtime = runtime or create_runtime("real", ocr_enabled=True)
    ready, ready_message = runtime.is_ready()
    report["runtime"] = {
        "provider": "real",
        "model_version": runtime.model_version,
        "ready": ready,
        "message": ready_message,
    }
    if not ready:
        report.update(status=GateStatus.HOLD, reasons=[ready_message])
        return GateStatus.HOLD, report

    payload = json.loads(dataset.read_text(encoding="utf-8"))
    selected_splits = splits or DEFAULT_SPLITS
    rows, errors = evaluate_dataset(runtime, dataset, payload, selected_splits)
    metrics = _metrics(rows)
    report.update(
        splits=selected_splits,
        rows=rows,
        inference_errors=errors,
        metrics=metrics,
        thresholds={
            "min_exact_match": min_exact_match,
            "min_positive_exact_match": min_positive_exact_match,
            "min_detector_recall": min_detector_recall,
            "min_ocr_exact_given_detection": min_ocr_exact_given_detection,
            "max_negative_false_positive_rate": max_negative_false_positive_rate,
            "max_p95_latency_ms": max_p95_latency_ms,
        },
    )

    reasons = []
    if not rows:
        reasons.append("No benchmark cases were evaluated")
    if errors:
        reasons.append(f"{len(errors)} media/inference case(s) failed")
    if metrics["exact_match_rate"] < min_exact_match:
        reasons.append(
            f"Exact match {metrics['exact_match_rate']:.4f} is below {min_exact_match:.4f}"
        )
    if metrics["positive_exact_match_rate"] < min_positive_exact_match:
        reasons.append(
            "Positive exact match "
            f"{metrics['positive_exact_match_rate']:.4f} is below "
            f"{min_positive_exact_match:.4f}"
        )
    if metrics["detector_recall"] < min_detector_recall:
        reasons.append(
            f"Detector recall {metrics['detector_recall']:.4f} is below {min_detector_recall:.4f}"
        )
    if metrics["ocr_exact_given_detection"] < min_ocr_exact_given_detection:
        reasons.append(
            "OCR exact given detection "
            f"{metrics['ocr_exact_given_detection']:.4f} is below "
            f"{min_ocr_exact_given_detection:.4f}"
        )
    if metrics["negative_false_positive_rate"] > max_negative_false_positive_rate:
        reasons.append(
            "Negative false positive rate "
            f"{metrics['negative_false_positive_rate']:.4f} exceeds "
            f"{max_negative_false_positive_rate:.4f}"
        )
    if metrics["latency_ms"]["p95"] > max_p95_latency_ms:
        reasons.append(
            f"P95 latency {metrics['latency_ms']['p95']:.3f}ms exceeds {max_p95_latency_ms:.3f}ms"
        )

    status = GateStatus.FAIL if reasons else GateStatus.PASS
    report.update(status=status, reasons=reasons)
    return status, report


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="VisionPark real-media ALPR quality gate")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=BACKEND_DIR / "datasets" / "phase2-release.json",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=BACKEND_DIR / "var" / "benchmarks" / "alpr-quality-gate-report.json",
    )
    parser.add_argument("--splits", nargs="+", default=DEFAULT_SPLITS)
    parser.add_argument("--min-exact-match", type=float, default=0.80)
    parser.add_argument("--min-positive-exact-match", type=float, default=0.80)
    parser.add_argument("--min-detector-recall", type=float, default=0.94)
    parser.add_argument("--min-ocr-exact-given-detection", type=float, default=0.80)
    parser.add_argument("--max-negative-false-positive-rate", type=float, default=0.0)
    parser.add_argument("--max-p95-latency-ms", type=float, default=1000.0)
    args = parser.parse_args()

    status, report = run_quality_gate(
        args.dataset,
        splits=args.splits,
        min_exact_match=args.min_exact_match,
        min_positive_exact_match=args.min_positive_exact_match,
        min_detector_recall=args.min_detector_recall,
        min_ocr_exact_given_detection=args.min_ocr_exact_given_detection,
        max_negative_false_positive_rate=args.max_negative_false_positive_rate,
        max_p95_latency_ms=args.max_p95_latency_ms,
    )
    _write_report(args.report, report)
    print(json.dumps({"status": status, "report": str(args.report)}, ensure_ascii=False))
    return ExitCode[status.name]


if __name__ == "__main__":
    raise SystemExit(main())
