"""Unit tests for SPEC-AI-06 Hard Sample Mining Loop and Confirmation."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.alpr.confirmation import save_hard_sample
from app.modules.alpr.models import Detection
from app.modules.users.models import User


def test_save_hard_sample_creates_metadata(tmp_path, monkeypatch):
    detection_id = uuid4()
    detection = Detection(
        id=detection_id,
        lane_id=uuid4(),
        raw_plate="29A12345",
        normalized_plate="29A12345",
        confidence=0.88,
        vehicle_type="CAR",
        vehicle_confidence=0.92,
        model_version="test-model",
        image_key="fake_key.jpg",
    )
    operator = User(id=uuid4(), username="operator_test")

    monkeypatch.chdir(tmp_path)
    save_hard_sample(
        detection=detection,
        confirmed_plate="29A99999",
        confirmed_vehicle_type="MOTORBIKE",
        operator=operator,
        reason="Misread plate number",
    )

    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    sample_dir = tmp_path / "var" / "hard_samples" / today_str / str(detection_id)
    assert sample_dir.is_dir()
    metadata_file = sample_dir / "metadata.json"
    assert metadata_file.is_file()
    content = metadata_file.read_text(encoding="utf-8")
    assert "29A99999" in content
    assert "29A12345" in content
    assert "Misread plate number" in content
