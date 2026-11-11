"""Functional gate exit/report contract; no ALPR quality claims."""

from scripts.system_gate import ExitCode, GateStatus, aggregate_status


def test_gate_aggregate_never_passes_partial_failure():
    assert aggregate_status([{"status": "PASS"}, {"status": "FAIL"}]) == GateStatus.FAIL
    assert aggregate_status([{"status": "PASS"}, {"status": "HOLD"}]) == GateStatus.HOLD
    assert aggregate_status([{"status": "PASS"}]) == GateStatus.PASS
    assert ExitCode.FAIL != 0 and ExitCode.HOLD != 0
