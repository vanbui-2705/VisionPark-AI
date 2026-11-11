from scripts.system_gate import GateStatus, aggregate_status


def test_system_gate_passes_only_when_every_check_passes():
    checks = [
        {"name": "database", "status": GateStatus.PASS},
        {"name": "real_alpr", "status": GateStatus.PASS},
    ]

    assert aggregate_status(checks) == GateStatus.PASS


def test_system_gate_holds_when_evidence_or_runtime_is_missing():
    checks = [
        {"name": "database", "status": GateStatus.PASS},
        {"name": "acceptance_media", "status": GateStatus.HOLD},
    ]

    assert aggregate_status(checks) == GateStatus.HOLD


def test_system_gate_failure_takes_precedence_over_hold():
    checks = [
        {"name": "runtime", "status": GateStatus.HOLD},
        {"name": "cash_ledger", "status": GateStatus.FAIL},
    ]

    assert aggregate_status(checks) == GateStatus.FAIL


def test_no_checks_is_not_a_pass():
    assert aggregate_status([]) == GateStatus.HOLD


def test_corrupt_image_is_rejected(tmp_path):
    import pytest

    from scripts.system_gate import GateFailure, _media_bytes

    image = tmp_path / "bad.jpg"
    image.write_bytes(b"not an image")
    with pytest.raises(GateFailure, match="cannot be decoded"):
        _media_bytes(image)


def test_cli_always_writes_report_and_exits_nonzero_on_error(tmp_path, monkeypatch):
    import json

    from scripts import system_gate

    path = tmp_path / "result.json"
    monkeypatch.setattr("sys.argv", ["system_gate", "--report", str(path)])
    monkeypatch.setenv("GATE_PASSWORD", "must-not-appear")

    def broken(**kwargs):
        raise ValueError("must-not-appear")

    monkeypatch.setattr(system_gate, "run_system_gate", broken)
    assert system_gate.main() == 1
    report = json.loads(path.read_text())
    assert report["status"] == "FAIL"
    assert report["alpr_accuracy"] == "NOT_EVALUATED"
    assert "commit" in report and "environment" in report
    assert "must-not-appear" not in path.read_text()


def test_unreachable_runtime_and_missing_media_hold(tmp_path, monkeypatch):
    import httpx

    from scripts import system_gate

    real_client = httpx.Client

    def offline(request):
        raise httpx.ConnectError("unavailable", request=request)

    monkeypatch.setattr(
        system_gate.httpx,
        "Client",
        lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(offline)),
    )
    monkeypatch.setattr(
        system_gate.httpx, "get", lambda *a, **kw: offline(httpx.Request("GET", "http://test/"))
    )
    monkeypatch.setenv("GATE_COMMIT", "test-commit")
    status, report = system_gate.run_system_gate(
        backend_url="http://test",
        frontend_url="http://test",
        image_path=None,
        video_path=None,
        video_time_ms=0,
    )
    assert status == GateStatus.HOLD
    assert report["commit"] == "test-commit"
    assert report["alpr_accuracy"] == "NOT_EVALUATED"


def test_functional_failure_keeps_manual_check_and_never_claims_accuracy(tmp_path, monkeypatch):
    import httpx

    from scripts import system_gate

    image, video = tmp_path / "car.jpg", tmp_path / "drive.mp4"
    image.write_bytes(b"fixture")
    video.write_bytes(b"fixture")
    for name in ["USERNAME", "PASSWORD", "CUSTOMER_CLASS_ID", "PLATE", "ENVIRONMENT", "COMMIT"]:
        monkeypatch.setenv("GATE_" + name, "fixture")
    monkeypatch.setenv("GATE_IN_LANE_ID", "in")
    monkeypatch.setenv("GATE_OUT_LANE_ID", "out")
    monkeypatch.setattr(
        system_gate,
        "_media_bytes",
        lambda path, **kw: (
            b"fixture",
            "IMAGE_UPLOAD" if path == image else "VIDEO_FRAME",
            "image/jpeg",
        ),
    )

    def transport(request):
        path = request.url.path
        payload = {"status": "alive"}
        if path == "/health/ready":
            payload = {
                "database": {"status": "ready", "provider": "postgresql"},
                "alpr": {"status": "ready", "provider": "real", "ocr_enabled": True},
            }
        elif path.endswith("/login"):
            payload = {"access_token": "secret-token"}
        elif path.endswith("/lanes/active"):
            payload = [
                {"id": "in", "direction": "IN", "building_id": "building"},
                {"id": "out", "direction": "OUT", "building_id": "building"},
            ]
        elif path.endswith("/alpr/detections"):
            # Explicit inference failure: manual business path must still execute.
            return httpx.Response(503, json={"detail": "unavailable"})
        return httpx.Response(200, json=payload)

    real_client = httpx.Client
    monkeypatch.setattr(
        system_gate.httpx,
        "Client",
        lambda **kw: real_client(**kw, transport=httpx.MockTransport(transport)),
    )
    monkeypatch.setattr(
        system_gate.httpx,
        "get",
        lambda url, **kw: (
            httpx.Response(200, json={"status": "alive"})
            if url.endswith("/health/live")
            else httpx.Response(200, text='<div id="root"></div>')
        ),
    )
    calls = []

    def manual(client, **kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(system_gate, "business_workflow", manual)
    status, report = system_gate.run_system_gate(
        backend_url="http://test",
        frontend_url="http://test",
        image_path=image,
        video_path=video,
        video_time_ms=0,
    )
    assert status == GateStatus.FAIL
    assert len(calls) == 1 and calls[0].get("detection_id") is None
    assert report["checks"][-1]["status"] == GateStatus.PASS
    assert report["alpr_accuracy"] == "NOT_EVALUATED"
    assert "secret-token" not in str(report)


def test_dry_run_calls_both_gates_even_after_failure(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace

    from scripts import dry_run

    monkeypatch.setattr(
        "sys.argv",
        [
            "dry_run",
            "--image",
            "car.jpg",
            "--video",
            "drive.mp4",
            "--dataset",
            "dataset.json",
            "--output",
            str(tmp_path),
        ],
    )
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=1 if len(calls) == 1 else 2)

    monkeypatch.setattr(dry_run.subprocess, "run", run)
    assert dry_run.main() == 1
    assert len(calls) == 2
    assert json.loads((tmp_path / "dry-run.json").read_text()) == {
        "SYSTEM_FUNCTIONAL": 1,
        "ALPR_QUALITY": 2,
    }
