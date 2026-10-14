from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_RELEASE_SPLITS = {"smoke", "validation", "demo", "edge_cases"}
REQUIRED_RELEASE_SCENARIOS = {
    "success",
    "no-plate",
    "low-confidence",
    "blur",
    "dark",
    "oblique",
    "small-or-partial",
    "negative",
}
REQUIRED_PROVENANCE_FIELDS = {
    "source",
    "usage_rights",
    "annotation_policy",
    "dataset_version",
}
REQUIRED_CASE_FIELDS = {"id", "vehicle_id", "image", "expected_plate", "scenario"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_dataset_manifest(dataset: Path, *, release: bool = False) -> dict[str, Any]:
    payload = json.loads(dataset.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []
    splits = payload.get("splits")
    if not isinstance(splits, dict) or not splits:
        return {
            "valid": False,
            "release_ready": False,
            "errors": ["splits must be a non-empty object"],
            "warnings": [],
            "dataset_fingerprint": None,
            "counts": {},
        }

    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("provenance must be an object with source and usage metadata")
    else:
        missing_provenance = sorted(REQUIRED_PROVENANCE_FIELDS - provenance.keys())
        if missing_provenance:
            errors.append("provenance missing fields: " + ", ".join(missing_provenance))

    missing_splits = sorted(REQUIRED_RELEASE_SPLITS - splits.keys())
    if missing_splits:
        message = "missing release splits: " + ", ".join(missing_splits)
        (errors if release else warnings).append(message)

    seen_ids: set[str] = set()
    group_splits: dict[str, set[str]] = {}
    scenarios: set[str] = set()
    file_hashes: dict[str, str] = {}
    counts: dict[str, int] = {}

    for split, cases in splits.items():
        if not isinstance(cases, list) or not cases:
            errors.append(f"split {split!r} must be a non-empty list")
            continue
        counts[split] = len(cases)
        for index, case in enumerate(cases):
            location = f"{split}[{index}]"
            if not isinstance(case, dict):
                errors.append(f"{location} must be an object")
                continue
            missing_fields = sorted(REQUIRED_CASE_FIELDS - case.keys())
            if missing_fields:
                errors.append(f"{location} missing fields: {', '.join(missing_fields)}")
                continue

            case_id = str(case["id"])
            if case_id in seen_ids:
                errors.append(f"duplicate case id: {case_id}")
            seen_ids.add(case_id)

            scenario_value = case["scenario"]
            case_scenarios = (
                {str(item) for item in scenario_value}
                if isinstance(scenario_value, list)
                else {str(scenario_value)}
            )
            scenarios.update(case_scenarios)

            group = str(case.get("video_id") or case["vehicle_id"])
            group_splits.setdefault(group, set()).add(split)

            image = Path(str(case["image"]))
            image_path = image if image.is_absolute() else dataset.parent / image
            if not image_path.is_file():
                errors.append(f"{location} image does not exist: {image_path}")
                continue
            actual_hash = _sha256(image_path)
            file_hashes[case_id] = actual_hash
            expected_hash = case.get("sha256")
            if expected_hash and str(expected_hash).lower() != actual_hash:
                errors.append(f"{location} sha256 mismatch")

    for group, assigned_splits in sorted(group_splits.items()):
        if len(assigned_splits) > 1:
            errors.append(
                f"vehicle/video group {group!r} leaks across splits: "
                + ", ".join(sorted(assigned_splits))
            )

    missing_scenarios = sorted(REQUIRED_RELEASE_SCENARIOS - scenarios)
    if missing_scenarios:
        message = "missing release scenarios: " + ", ".join(missing_scenarios)
        (errors if release else warnings).append(message)

    canonical_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    fingerprint_input = canonical_payload + json.dumps(
        file_hashes, sort_keys=True
    ).encode("utf-8")
    fingerprint = hashlib.sha256(fingerprint_input).hexdigest()
    return {
        "valid": not errors,
        "release_ready": not errors and not missing_splits and not missing_scenarios,
        "errors": errors,
        "warnings": warnings,
        "dataset_fingerprint": fingerprint,
        "counts": counts,
        "scenarios": sorted(scenarios),
        "file_hashes": file_hashes,
    }
