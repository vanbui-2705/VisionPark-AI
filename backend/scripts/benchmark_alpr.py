"""Run a reproducible ALPR benchmark without downloading model assets.

Uses externally provisioned model assets and labelled images.
No application mock provider is available.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.alpr.errors import ALPRNotReadyError, ALPRProcessingError
from app.alpr.runtime_adapter import create_runtime
from app.core.config import get_settings


def synthetic_frame() -> bytes:
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.rectangle(frame, (80, 90), (240, 150), (220, 220, 220), -1)
    cv2.putText(frame, "29A12345", (88, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 2)
    encoded, buffer = cv2.imencode(".jpg", frame)
    if not encoded:
        raise RuntimeError("Could not create synthetic benchmark frame")
    return buffer.tobytes()


def normalized(value: str | None) -> str | None:
    return "".join(char for char in (value or "").upper() if char.isalnum()) or None


def character_accuracy(expected: str | None, actual: str | None) -> float:
    expected = normalized(expected) or ""
    actual = normalized(actual) or ""
    if not expected:
        return 1.0 if not actual else 0.0
    previous = list(range(len(actual) + 1))
    for row, left in enumerate(expected, 1):
        current = [row]
        for column, right in enumerate(actual, 1):
            current.append(
                min(current[-1] + 1, previous[column] + 1, previous[column - 1] + (left != right))
            )
        previous = current
    return max(0.0, 1.0 - previous[-1] / len(expected))


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
    return round(ordered[index], 3)


def load_cases(dataset: Path, split: str) -> list[dict[str, Any]]:
    payload = json.loads(dataset.read_text(encoding="utf-8"))
    cases = payload.get("splits", {}).get(split)
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"Dataset split is empty or missing: {split}")
    return cases


def image_bytes(case: dict[str, Any], dataset: Path) -> bytes:
    image_path = case.get("image")
    if image_path:
        return (dataset.parent / image_path).read_bytes()
    return synthetic_frame()


def run_case(runtime: Any, case: dict[str, Any], dataset: Path) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = runtime.detect_and_read(image_bytes(case, dataset))
        error = None
    except (ALPRNotReadyError, ALPRProcessingError, TimeoutError) as exc:
        result = None
        error = type(exc).__name__
    full_latency = (time.perf_counter() - started) * 1000
    actual = normalized((result.normalized_plate or result.plate_number) if result else None)
    expected = normalized(case.get("expected_plate"))
    return {
        "id": case.get("id", "unknown"),
        "vehicle_id": case.get("vehicle_id", case.get("id", "unknown")),
        "scenario": case.get("scenario", "unknown"),
        "expected_plate": expected,
        "actual_plate": actual,
        "exact_match": bool(expected and actual and expected == actual),
        "character_accuracy": round(character_accuracy(expected, actual), 4),
        "no_result": actual is None,
        "false_positive": expected is None and actual is not None,
        "error": error,
        "full_latency_ms": round(full_latency, 3),
        "detector_latency_ms": getattr(result, "detector_latency_ms", None),
        "ocr_latency_ms": getattr(result, "ocr_latency_ms", None),
        "processing_time_ms": getattr(result, "processing_time_ms", None),
        "requires_confirmation": getattr(result, "requires_confirmation", True),
        "quality_flags": getattr(result, "quality_flags", []),
    }


def station_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["vehicle_id"], []).append(row)
    stable_times: list[float] = []
    flips = 0
    transitions = 0
    ocr_calls = 0
    for vehicle_rows in grouped.values():
        candidates = [row["actual_plate"] for row in vehicle_rows if row["actual_plate"]]
        ocr_calls += sum(row["ocr_latency_ms"] is not None for row in vehicle_rows)
        transitions += max(0, len(candidates) - 1)
        flips += sum(left != right for left, right in zip(candidates, candidates[1:], strict=False))
        for index in range(1, len(candidates)):
            if candidates[index] == candidates[index - 1]:
                stable_times.append(
                    sum(row["full_latency_ms"] for row in vehicle_rows[: index + 1])
                )
                break
    total = len(rows)
    return {
        "time_to_stable_ms": percentile(stable_times, 0.5),
        "ocr_calls_per_vehicle": round(ocr_calls / max(len(grouped), 1), 3),
        "candidate_flip_rate": round(flips / max(transitions, 1), 4),
        "provider_error_rate": round(
            sum(row["error"] is not None for row in rows) / max(total, 1), 4
        ),
    }


def build_report(rows: list[dict[str, Any]], provider: str, split: str) -> dict[str, Any]:
    latencies = [row["full_latency_ms"] for row in rows]
    detector = [
        row["detector_latency_ms"] for row in rows if row["detector_latency_ms"] is not None
    ]
    ocr = [row["ocr_latency_ms"] for row in rows if row["ocr_latency_ms"] is not None]
    expected = [row for row in rows if row["expected_plate"]]
    return {
        "provider": provider,
        "split": split,
        "sample_count": len(rows),
        "exact_match_rate": round(
            sum(row["exact_match"] for row in expected) / max(len(expected), 1), 4
        ),
        "character_accuracy": round(
            statistics.mean(row["character_accuracy"] for row in (expected or rows)), 4
        ),
        "no_result_rate": round(sum(row["no_result"] for row in rows) / max(len(rows), 1), 4),
        "false_positive_rate": round(
            sum(row["false_positive"] for row in rows) / max(len(rows), 1), 4
        ),
        "latency_ms": {
            "full_p50": percentile(latencies, 0.5),
            "full_p95": percentile(latencies, 0.95),
            "detector_p50": percentile(detector, 0.5),
            "ocr_p50": percentile(ocr, 0.5),
        },
        "station": station_metrics(rows),
        "errors": sum(row["error"] is not None for row in rows),
        "rows": rows,
    }


def warmup_report(runtime: Any, case: dict[str, Any], dataset: Path) -> dict[str, float | None]:
    timings: list[float] = []
    payload = image_bytes(case, dataset)
    for _ in range(3):
        started = time.perf_counter()
        try:
            runtime.detect_and_read(payload)
        except (ALPRNotReadyError, ALPRProcessingError, TimeoutError):
            return {"cold_ms": None, "warm_p50_ms": None}
        timings.append((time.perf_counter() - started) * 1000)
    return {"cold_ms": round(timings[0], 3), "warm_p50_ms": percentile(timings[1:], 0.5)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="real", choices=("real",))
    parser.add_argument("--split", default="smoke")
    parser.add_argument(
        "--dataset", type=Path, default=Path("tests/fixtures/phase2-benchmark.json")
    )
    parser.add_argument("--json-out", type=Path, default=Path("var/benchmarks/alpr-report.json"))
    parser.add_argument("--csv-out", type=Path, default=Path("var/benchmarks/alpr-results.csv"))
    args = parser.parse_args()
    cases = load_cases(args.dataset, args.split)
    if args.provider == "real":
        for case in cases:
            if not case.get("image"):
                parser.error(
                    "Real benchmarks require an image path for every sample; "
                    "mock fixtures are not recognition evidence."
                )
            if not (args.dataset.parent / case["image"]).is_file():
                parser.error(f"Real benchmark image is missing: {case['image']}")
    rows: list[dict[str, Any]] = []
    settings = get_settings()
    warm_runtime = create_runtime(
        args.provider,
        ocr_enabled=True,
        manifest_path=settings.alpr_manifest_path,
        device=settings.alpr_device,
        detector_confidence=settings.alpr_detector_confidence,
        confirmation_threshold=settings.alpr_confidence_threshold,
        ocr_margin=settings.alpr_ocr_margin,
    )
    warmup = warmup_report(warm_runtime, cases[0], args.dataset)
    for case in cases:
        runtime = warm_runtime
        rows.append(run_case(runtime, case, args.dataset))
    report = build_report(rows, args.provider, args.split)
    report["dataset"] = str(args.dataset)
    report["input_kind"] = "provisioned-images"
    report["warmup"] = warmup
    report["model_version"] = warm_runtime.version
    report["hardware"] = {
        "machine": platform.machine(),
        "platform": platform.platform(),
        "device": settings.alpr_device,
    }
    report["versions"] = {
        package: version(package) for package in ["ultralytics", "paddleocr", "paddlepaddle"]
    }
    report["provenance"] = json.loads(args.dataset.read_text(encoding="utf-8")).get("provenance")
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.csv_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with args.csv_out.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()
