"""Verify rebuild/restart/recreate preserve every restored row and media byte."""

import json
import subprocess
from pathlib import Path

import httpx
from data_backup import inventory
from smoke_completion import BACKEND, COMPOSE, DB, compose, wait_ready

ROOT = Path(__file__).resolve().parents[2]


def main():
    with httpx.Client(base_url="http://localhost:8003", timeout=180) as api:
        wait_ready(api)
        before = inventory(DB, BACKEND)
        assert not {"visionpark_postgres_data", "visionpark_media_data"} & set(before["volumes"])
        checks = {}
        for operation in ["restart", "down_up", "rebuild_force_recreate"]:
            print("Verify all persisted data: " + operation, flush=True)
            if operation == "restart":
                compose("restart")
            elif operation == "down_up":
                compose("down")
                compose("up", "-d")
            else:
                subprocess.run(
                    ["docker", "compose", "build", "backend", "frontend"],
                    cwd=ROOT,
                    check=True,
                    stdout=subprocess.DEVNULL,
                )
                compose("up", "-d", "--force-recreate")
            wait_ready(api)
            assert inventory(DB, BACKEND) == before, operation + " changed rows/media"
            checks[operation] = "pass"
        report = {
            "environment": "isolated restore",
            "checks": checks,
            "inventory": before,
            "compose": COMPOSE[-1],
        }
        (ROOT / "docs/phase-2-evidence/completion-lifecycle-final.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(checks), flush=True)


if __name__ == "__main__":
    main()
