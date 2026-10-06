from uuid import UUID

import pytest

from app.core.errors import AppError
from app.database.idempotency import fingerprint_payload, validate_idempotency_key


def test_fingerprint_is_stable_across_mapping_order():
    lane = UUID("00000000-0000-0000-0000-000000000001")
    assert fingerprint_payload({"lane": lane, "notes": "confirmed"}) == fingerprint_payload(
        {"notes": "confirmed", "lane": lane}
    )


def test_fingerprint_distinguishes_notes_and_actor():
    original = {"plate": "29A12345", "notes": "accepted", "actor": "operator-1"}
    assert fingerprint_payload(original) != fingerprint_payload({**original, "notes": "edited"})
    assert fingerprint_payload(original) != fingerprint_payload({**original, "actor": "operator-2"})


@pytest.mark.parametrize("key", [None, "", "   "])
def test_missing_key_is_a_controlled_validation_error(key):
    with pytest.raises(AppError) as error:
        validate_idempotency_key(key)
    assert error.value.status_code == 422
    assert error.value.code == "IDEMPOTENCY_KEY_REQUIRED"


def test_key_length_matches_database_capacity():
    assert validate_idempotency_key("k" * 255) == "k" * 255
    with pytest.raises(AppError) as error:
        validate_idempotency_key("k" * 256)
    assert error.value.status_code == 422
    assert error.value.code == "INVALID_IDEMPOTENCY_KEY"
