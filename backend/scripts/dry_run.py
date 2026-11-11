"""Run independent system and ALPR quality gates; preserve both reports on failure."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5173")
    parser.add_argument("--output", type=Path, default=BACKEND / "var/reports")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    commands = {
        "SYSTEM_FUNCTIONAL": [
            "scripts/system_gate.py",
            "--image",
            str(args.image.resolve()),
            "--video",
            str(args.video.resolve()),
            "--backend-url",
            args.backend_url,
            "--frontend-url",
            args.frontend_url,
            "--report",
            str(output / "system-functional.json"),
        ],
        "ALPR_QUALITY": [
            "scripts/release_gate.py",
            "--dataset",
            str(args.dataset.resolve()),
            "--report",
            str(output / "alpr-quality.json"),
        ],
    }
    codes = {}
    for name, command in commands.items():
        try:
            codes[name] = subprocess.run(
                [sys.executable, *command], cwd=BACKEND, timeout=1800, check=False
            ).returncode
        except (OSError, subprocess.TimeoutExpired):
            codes[name] = 1
    (output / "dry-run.json").write_text(json.dumps(codes, indent=2), encoding="utf-8")
    print(json.dumps(codes))
    # Failure outranks HOLD, and missing evidence never exits successfully.
    return (
        1
        if any(code not in (0, 2) for code in codes.values())
        else (2 if 2 in codes.values() else 0)
    )


if __name__ == "__main__":
    raise SystemExit(main())
