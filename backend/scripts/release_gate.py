"""Run the traceable Phase 2 real-provider release gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from app.alpr.dataset_manifest import validate_dataset_manifest
from app.alpr.runtime_adapter import create_runtime

REQUIRED_EVIDENCE = (
    "real_success_image",
    "real_success_video",
    "real_low_confidence_operator_correction",
    "real_no_plate_manual_fallback",
    "corrected_plate_audit",
    "duplicate",
    "retry_idempotency",
)
BENCHMARK_REPORTS = {
    "smoke": "release-benchmark-smoke.json",
    "validation": "release-benchmark-validation.json",
    "demo": "release-benchmark-demo.json",
    "edge_cases": "release-benchmark-edge-cases.json",
}
MIN_RELEASE_EXACT_MATCH = 0.8
MAX_RELEASE_P95_MS = 1000.0


def run(command: list[str], cwd: Path) -> None:
    print("$", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def main() -> None:
    backend = Path(__file__).resolve().parents[1]
    root = backend.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=backend / "datasets" / "phase2-release.json",
    )
    parser.add_argument(
        "--evidence-index",
        type=Path,
        default=root / "docs" / "phase-2-evidence" / "evidence-index.json",
    )
    parser.add_argument(
        "--functional-only",
        action="store_true",
        help=(
            "Validate the runnable operator workflow and safety evidence without "
            "requiring the recognition-quality exact-match floor."
        ),
    )
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    failures: list[str] = []

    validation = validate_dataset_manifest(args.dataset, release=True)
    if not validation["release_ready"]:
        failures.extend(validation["errors"])

    evidence = json.loads(args.evidence_index.read_text(encoding="utf-8"))
    for scenario in REQUIRED_EVIDENCE:
        status = evidence.get("scenarios", {}).get(scenario, {}).get("status")
        if status != "pass":
            failures.append(f"evidence {scenario!r} is {status or 'missing'}")
    if evidence.get("dataset", {}).get("fingerprint") != validation["dataset_fingerprint"]:
        failures.append("evidence index dataset fingerprint does not match the manifest")

    evidence_dir = args.evidence_index.parent
    benchmark_reports: dict[str, dict] = {}
    for split, filename in BENCHMARK_REPORTS.items():
        report_path = evidence_dir / filename
        if not report_path.is_file():
            failures.append(f"missing benchmark report: {filename}")
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        benchmark_reports[split] = report
        if report.get("dataset_fingerprint") != validation["dataset_fingerprint"]:
            failures.append(f"benchmark {split!r} fingerprint does not match the manifest")
        if report.get("errors") != 0 or report.get("station", {}).get("provider_error_rate") != 0:
            failures.append(f"benchmark {split!r} contains provider errors")
        p95 = report.get("latency_ms", {}).get("full_p95")
        if not isinstance(p95, int | float) or p95 > MAX_RELEASE_P95_MS:
            failures.append(f"benchmark {split!r} full p95 exceeds {MAX_RELEASE_P95_MS} ms")

    if not args.functional_only:
        for split in ("validation", "demo"):
            exact_match = benchmark_reports.get(split, {}).get("exact_match_rate")
            if not isinstance(exact_match, int | float) or exact_match < MIN_RELEASE_EXACT_MATCH:
                failures.append(
                    f"benchmark {split!r} exact match is {exact_match}; "
                    f"release floor is {MIN_RELEASE_EXACT_MATCH}"
                )
    edge_report = benchmark_reports.get("edge_cases", {})
    if edge_report.get("false_positive_rate") != 0:
        failures.append("edge-case benchmark has false positives")

    missing = create_runtime("real", manifest_path=str(backend / "models" / "missing.json"))
    if missing.is_ready()[0]:
        failures.append("real provider unexpectedly became ready without its manifest")

    if not args.skip_tests:
        run([sys.executable, "-m", "pytest", "tests", "-q"], backend)
        run([sys.executable, "-m", "ruff", "check", "."], backend)
        run(["npm", "test", "--", "--run"], root / "frontend")
        run(["npm", "run", "lint"], root / "frontend")
        run(["npm", "run", "build"], root / "frontend")

    gate_name = (
        "Phase 2 functional acceptance gate"
        if args.functional_only
        else "Phase 2 recognition-quality release gate"
    )
    if failures:
        print(f"{gate_name}: FAIL")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print(f"{gate_name}: PASS")


if __name__ == "__main__":
    main()
