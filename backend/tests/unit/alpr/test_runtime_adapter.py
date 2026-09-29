from io import BytesIO

import pytest
from PIL import Image

from app.alpr.errors import ALPRNotReadyError, ALPRProcessingError
from app.alpr.runtime_adapter import FakeALPRRuntime


def image_bytes() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (10, 10), color="red").save(stream, format="JPEG")
    return stream.getvalue()


def test_mock_scenarios_are_deterministic():
    success = FakeALPRRuntime("success").detect_and_read(image_bytes())
    low = FakeALPRRuntime("low-confidence").detect_and_read(image_bytes())
    no_plate = FakeALPRRuntime("no-plate").detect_and_read(image_bytes())

    assert success.plate_number == "29A-123.45"
    assert success.requires_confirmation is False
    assert low.confidence == 0.5
    assert low.requires_confirmation is True
    assert no_plate.plate_number is None
    assert no_plate.bbox is None
    assert no_plate.requires_confirmation is True


def test_mock_unavailable_and_processing_error():
    unavailable = FakeALPRRuntime("unavailable")
    assert unavailable.is_ready()[0] is False
    with pytest.raises(ALPRNotReadyError):
        unavailable.detect_and_read(image_bytes())

    with pytest.raises(ALPRProcessingError):
        FakeALPRRuntime("processing-error").detect_and_read(image_bytes())
