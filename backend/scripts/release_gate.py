"""Run the Phase 2 mock release gate without model weights or GPU."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from app.alpr.runtime_adapter import create_runtime


def run(command: list[str], cwd: Path) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    backend = Path(__file__).resolve().parents[1]

    for scenario in ("success", "low-confidence", "no-plate", "unavailable", "processing-error"):
        runtime = create_runtime("mock", mock_scenario=scenario)
        ready, _ = runtime.is_ready()
        expected_ready = scenario != "unavailable"
        if ready != expected_ready:
            raise SystemExit(f"Mock readiness mismatch for scenario={scenario}")

    missing = create_runtime("real", manifest_path=str(backend / "models" / "missing.json"))
    if missing.is_ready()[0]:
        raise SystemExit("Real provider unexpectedly became ready without its manifest")

    run(
        [
            sys.executable,
            "scripts/benchmark_alpr.py",
            "--provider",
            "mock",
            "--split",
            "smoke",
        ],
        backend,
    )
    if not args.skip_tests:
        run([sys.executable, "-m", "pytest", "tests", "-q"], backend)
        run([sys.executable, "-m", "ruff", "check", "."], backend)
    print("Phase 2 mock release gate: PASS")


if __name__ == "__main__":
    main()
