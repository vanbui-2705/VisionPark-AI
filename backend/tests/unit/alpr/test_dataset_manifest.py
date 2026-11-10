import hashlib
import json
from pathlib import Path

from app.alpr.dataset_manifest import validate_dataset_manifest


def write_dataset(tmp_path: Path, *, leak: bool = False, bad_hash: bool = False) -> Path:
    scenarios = [
        ("smoke", "success"),
        ("validation", "no-plate"),
        ("demo", "low-confidence"),
        ("edge_cases", "blur"),
        ("edge_cases", "dark"),
        ("edge_cases", "oblique"),
        ("edge_cases", "small-or-partial"),
        ("edge_cases", "negative"),
    ]
    splits: dict[str, list[dict]] = {}
    for index, (split, scenario) in enumerate(scenarios):
        image = tmp_path / f"case-{index}.jpg"
        image.write_bytes(f"image-{index}".encode())
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        splits.setdefault(split, []).append(
            {
                "id": f"case-{index}",
                "vehicle_id": "shared" if leak and index < 2 else f"vehicle-{index}",
                "image": image.name,
                "expected_plate": None if scenario in {"no-plate", "negative"} else "29A12345",
                "scenario": scenario,
                "sha256": "0" * 64 if bad_hash and index == 0 else digest,
            }
        )
    dataset = tmp_path / "dataset.json"
    dataset.write_text(
        json.dumps(
            {
                "provenance": {
                    "source": "test fixture",
                    "usage_rights": "test-only",
                    "annotation_policy": "manual",
                    "dataset_version": "1",
                },
                "splits": splits,
            }
        ),
        encoding="utf-8",
    )
    return dataset


def test_release_manifest_is_valid_and_fingerprinted(tmp_path):
    result = validate_dataset_manifest(write_dataset(tmp_path), release=True)

    assert result["valid"] is True
    assert result["release_ready"] is True
    assert len(result["dataset_fingerprint"]) == 64
    assert result["counts"] == {"smoke": 1, "validation": 1, "demo": 1, "edge_cases": 5}


def test_release_manifest_rejects_group_leakage(tmp_path):
    result = validate_dataset_manifest(write_dataset(tmp_path, leak=True), release=True)

    assert result["valid"] is False
    assert any("leaks across splits" in error for error in result["errors"])


def test_release_manifest_rejects_hash_mismatch(tmp_path):
    result = validate_dataset_manifest(write_dataset(tmp_path, bad_hash=True), release=True)

    assert result["valid"] is False
    assert any("sha256 mismatch" in error for error in result["errors"])
