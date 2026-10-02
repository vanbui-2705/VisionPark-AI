import hashlib
import json
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.alpr.utils import normalize_plate
from app.core.errors import AppError
from app.modules.audit_logs.service import log_action
from app.modules.lanes.models import LaneDirection
from app.modules.users.models import User

from .models import CheckInSource, ParkingTransaction, TransactionStatus
from .repository import CheckInRepository
from .schemas import (
    CheckInRequest,
    CheckInResponse,
    ParkingTransactionResponse,
)


class CheckInService:
    def __init__(self, repository: CheckInRepository, session: Session | None = None):
        self.repo = repository
        self.session = session

    def process_check_in(
        self,
        request: CheckInRequest,
        *,
        operator: User,
        idempotency_key: str | None = None,
    ) -> CheckInResponse:
        key = idempotency_key or request.idempotency_key
        if not key:
            raise AppError(
                status_code=422,
                code="IDEMPOTENCY_KEY_REQUIRED",
                message="Idempotency-Key header is required.",
            )

        lane = self.repo.get_lane(request.lane_id)
        if lane is None:
            raise AppError(
                status_code=404,
                code="LANE_NOT_FOUND",
                message="The selected lane does not exist.",
            )
        if not lane.is_active:
            raise AppError(
                status_code=400,
                code="LANE_INACTIVE",
                message="The selected lane is inactive.",
            )
        if lane.direction != LaneDirection.IN:
            raise AppError(
                status_code=400,
                code="INVALID_LANE_TYPE",
                message="Check-in is only allowed on an IN lane.",
            )

        normalized_plate = normalize_plate(request.requested_plate)
        if len(normalized_plate) < 3:
            raise AppError(
                status_code=422,
                code="INVALID_PLATE",
                message="The normalized plate is too short.",
            )

        detection = self.repo.get_detection(request.detection_id) if request.detection_id else None
        if request.detection_id and detection is None:
            raise AppError(
                status_code=404,
                code="DETECTION_NOT_FOUND",
                message="The referenced detection does not exist.",
            )
        if detection and detection.lane_id != request.lane_id:
            raise AppError(
                status_code=409,
                code="DETECTION_LANE_MISMATCH",
                message="The detection belongs to a different lane.",
            )

        ai_plate = request.original_ai_plate or (detection.normalized_plate if detection else None)
        ai_normalized = normalize_plate(ai_plate) if ai_plate else None
        source = self._resolve_source(
            request.source, detection is not None, ai_normalized, normalized_plate
        )
        fingerprint = self._fingerprint(
            lane_id=request.lane_id,
            normalized_plate=normalized_plate,
            detection_id=request.detection_id,
            source=source,
            ai_plate=ai_normalized,
            confidence=request.confidence,
        )

        existing = self.repo.get_by_idempotency_key(key)
        if existing:
            if existing.request_fingerprint != fingerprint:
                raise AppError(
                    status_code=409,
                    code="IDEMPOTENCY_KEY_REUSED",
                    message="Idempotency-Key was already used with a different payload.",
                )
            return CheckInResponse(
                transaction=self.to_response(existing),
                message="The existing check-in transaction was returned.",
            )

        duplicate = self.repo.get_active_by_plate(normalized_plate)
        if duplicate:
            raise AppError(
                status_code=409,
                code="PLATE_ALREADY_PARKED",
                message="This plate already has an active PARKED transaction.",
                details={"transaction_id": str(duplicate.id)},
            )

        confidence = request.confidence
        if confidence is None and detection:
            confidence = detection.confidence
        image_url = None
        if detection and detection.image_key:
            image_url = f"/api/v1/alpr/media/{detection.image_key}"
        if self.session is None:
            raise RuntimeError("Database session is required for check-in persistence")
        try:
            transaction = self.repo.save_transaction(
                {
                    "license_plate": normalized_plate,
                    "normalized_plate": normalized_plate,
                    "original_ai_plate": ai_plate,
                    "status": TransactionStatus.PARKED,
                    "lane_id": request.lane_id,
                    "detection_id": request.detection_id,
                    "image_url": image_url,
                    "confidence": confidence,
                    "check_in_operator_id": operator.id,
                    "source": source,
                    "is_manual_override": source != CheckInSource.AI_ACCEPTED,
                    "notes": request.override_reason,
                    "idempotency_key": key,
                    "request_fingerprint": fingerprint,
                }
            )
            log_action(
                db=self.session,
                user_id=operator.id,
                action="CREATE_CHECKIN",
                entity_type="ParkingTransaction",
                entity_id=str(transaction.id),
                new_value={
                    "lane_id": str(request.lane_id),
                    "ai_plate": ai_plate,
                    "final_plate": normalized_plate,
                    "source": source,
                    "actor_id": str(operator.id),
                    "detection_id": str(request.detection_id) if request.detection_id else None,
                },
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            existing = self.repo.get_by_idempotency_key(key)
            if existing and existing.request_fingerprint == fingerprint:
                return CheckInResponse(
                    transaction=self.to_response(existing),
                    message="The existing check-in transaction was returned.",
                )
            duplicate = self.repo.get_active_by_plate(normalized_plate)
            if duplicate:
                raise AppError(
                    status_code=409,
                    code="PLATE_ALREADY_PARKED",
                    message="This plate already has an active PARKED transaction.",
                    details={"transaction_id": str(duplicate.id)},
                ) from exc
            raise AppError(
                status_code=409,
                code="IDEMPOTENCY_KEY_REUSED",
                message="Idempotency-Key was already used with a different payload.",
            ) from exc
        self.session.refresh(transaction)
        return CheckInResponse(
            transaction=self.to_response(transaction),
            message="Check-in transaction created.",
        )

    def get_transaction(self, transaction_id: UUID) -> ParkingTransactionResponse:
        transaction = self.repo.get_by_id(transaction_id)
        if transaction is None:
            raise AppError(status_code=404, code="NOT_FOUND", message="Transaction not found.")
        return self.to_response(transaction)

    def list_transactions(self, **filters) -> list[ParkingTransactionResponse]:
        return [self.to_response(item) for item in self.repo.list_transactions(**filters)]

    @staticmethod
    def _resolve_source(
        requested: CheckInSource | None,
        has_detection: bool,
        ai_plate: str | None,
        final_plate: str,
    ) -> str:
        if requested == CheckInSource.STATION_AUTO:
            requested = CheckInSource.AI_ACCEPTED
        if requested == CheckInSource.OPERATOR_MANUAL:
            requested = CheckInSource.MANUAL_ENTRY
        if requested:
            return requested
        if not has_detection or not ai_plate:
            return CheckInSource.MANUAL_ENTRY
        return (
            CheckInSource.AI_ACCEPTED
            if ai_plate == final_plate
            else CheckInSource.OPERATOR_CORRECTED
        )

    @staticmethod
    def _fingerprint(**values: object) -> str:
        payload = json.dumps(values, default=str, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def to_response(transaction: ParkingTransaction) -> ParkingTransactionResponse:
        return ParkingTransactionResponse(
            id=transaction.id,
            license_plate=transaction.license_plate,
            original_ai_plate=transaction.original_ai_plate,
            normalized_plate=transaction.normalized_plate,
            status=transaction.status,
            lane_id=transaction.lane_id,
            lane_name=transaction.lane.name if transaction.lane else None,
            detection_id=transaction.detection_id,
            image_url=transaction.image_url,
            confidence=transaction.confidence,
            check_in_time=transaction.check_in_time,
            check_in_operator_id=transaction.check_in_operator_id,
            check_in_operator_name=(
                transaction.check_in_operator.display_name
                if transaction.check_in_operator
                else None
            ),
            source=transaction.source,
            is_manual_override=transaction.is_manual_override,
            notes=transaction.notes,
            created_at=transaction.created_at,
        )
