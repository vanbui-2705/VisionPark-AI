import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.core.errors import AppError
from app.modules.checkin.models import TransactionStatus
from app.modules.checkin.schemas import CheckInRequest
from app.modules.checkin.service import CheckInService
from app.modules.lanes.models import LaneDirection


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def service(mock_repo, mock_session):
    return CheckInService(repository=mock_repo, session=mock_session)


@pytest.fixture
def operator():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.display_name = "Test Operator"
    return user


@pytest.fixture
def lane_in():
    lane = MagicMock()
    lane.is_active = True
    lane.direction = LaneDirection.IN
    lane.name = "Test Lane IN"
    return lane


def test_check_in_success(service, mock_repo, mock_session, operator, lane_in):
    # Setup
    lane_id = uuid.uuid4()
    mock_repo.get_by_idempotency_key.return_value = None
    mock_repo.get_lane.return_value = lane_in
    mock_repo.get_active_by_plate.return_value = None

    transaction_mock = MagicMock()
    transaction_mock.id = uuid.uuid4()
    transaction_mock.lane = lane_in
    transaction_mock.lane_id = lane_id
    transaction_mock.lane_name_snapshot = lane_in.name
    transaction_mock.operator_name_snapshot = operator.display_name
    transaction_mock.license_plate = "29A12345"
    transaction_mock.normalized_plate = "29A12345"
    transaction_mock.original_ai_plate = None
    transaction_mock.status = TransactionStatus.PARKED
    transaction_mock.detection_id = None
    transaction_mock.image_url = None
    transaction_mock.confidence = None
    transaction_mock.check_in_time = datetime.now()
    transaction_mock.check_in_operator_id = operator.id
    transaction_mock.lane_snapshot_name = "Mock Lane"
    transaction_mock.lane_snapshot_direction = "IN"
    transaction_mock.check_in_operator = MagicMock()
    transaction_mock.check_in_operator.display_name = "Test Operator"
    transaction_mock.operator_snapshot_name = "Test Operator"
    transaction_mock.source = "MANUAL_ENTRY"
    transaction_mock.is_manual_override = True
    transaction_mock.notes = None
    transaction_mock.created_at = datetime.now()
    mock_repo.save_transaction.return_value = transaction_mock

    request = CheckInRequest(lane_id=lane_id, license_plate="29A-123.45", idempotency_key="key1")

    # Execute
    response = service.process_check_in(request, operator=operator, idempotency_key="key1")

    # Assert
    assert response.message == "Check-in transaction created."
    mock_repo.save_transaction.assert_called_once()
    saved_data = mock_repo.save_transaction.call_args[0][0]
    assert saved_data["normalized_plate"] == "29A12345"


def test_check_in_lane_inactive(service, mock_repo, operator):
    # Setup
    lane_id = uuid.uuid4()
    mock_repo.get_by_idempotency_key.return_value = None
    lane_inactive = MagicMock()
    lane_inactive.is_active = False
    mock_repo.get_lane.return_value = lane_inactive

    request = CheckInRequest(lane_id=lane_id, license_plate="30H-12345", idempotency_key="key2")

    # Execute & Assert
    with pytest.raises(AppError) as exc_info:
        service.process_check_in(request, operator=operator, idempotency_key="key2")
    assert exc_info.value.code == "LANE_INACTIVE"


def test_check_in_invalid_lane_direction(service, mock_repo, operator):
    # Setup
    lane_id = uuid.uuid4()
    mock_repo.get_by_idempotency_key.return_value = None
    lane_out = MagicMock()
    lane_out.is_active = True
    lane_out.direction = LaneDirection.OUT
    mock_repo.get_lane.return_value = lane_out

    request = CheckInRequest(lane_id=lane_id, license_plate="30H-12345", idempotency_key="key3")

    # Execute & Assert
    with pytest.raises(AppError) as exc_info:
        service.process_check_in(request, operator=operator, idempotency_key="key3")
    assert exc_info.value.code == "INVALID_LANE_TYPE"


def test_check_in_duplicate_plate(service, mock_repo, operator, lane_in):
    # Setup
    lane_id = uuid.uuid4()
    mock_repo.get_by_idempotency_key.return_value = None
    mock_repo.get_lane.return_value = lane_in

    existing_txn = MagicMock()
    existing_txn.id = uuid.uuid4()
    mock_repo.get_active_by_plate.return_value = existing_txn

    request = CheckInRequest(lane_id=lane_id, license_plate="30H-12345", idempotency_key="key4")

    # Execute & Assert
    with pytest.raises(AppError) as exc_info:
        service.process_check_in(request, operator=operator, idempotency_key="key4")
    assert exc_info.value.code == "PLATE_ALREADY_PARKED"


def test_check_in_idempotency_replay(service, mock_repo, operator, lane_in):
    # Setup
    lane_id = uuid.uuid4()
    mock_repo.get_lane.return_value = lane_in
    idempotency_key = "test-key-123"

    existing_txn = MagicMock()
    existing_txn.id = uuid.uuid4()
    existing_txn.request_fingerprint = "dummy_fingerprint"
    existing_txn.check_in_operator_id = operator.id
    existing_txn.notes = None
    existing_txn.original_ai_plate = None
    mock_repo.get_by_idempotency_key.return_value = existing_txn

    request = CheckInRequest(
        lane_id=lane_id, license_plate="29A-12345", idempotency_key=idempotency_key
    )

    with pytest.raises(AppError) as exc_info:
        service.process_check_in(request, operator=operator, idempotency_key=idempotency_key)
    assert exc_info.value.code == "IDEMPOTENCY_KEY_REUSED"
