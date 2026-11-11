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
