from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.alpr.utils import normalize_plate
from app.core.errors import AppError
from app.database.idempotency import (
    fingerprint_payload,
    require_matching_fingerprint,
    validate_idempotency_key,
)
from app.modules.audit_logs.service import log_action
from app.modules.lanes.models import LaneDirection
from app.modules.users.models import User

from .models import CheckInSource, ParkingTransaction, TransactionStatus
from .repository import CheckInRepository
from .schemas import (
    CheckInRequest,
    CheckInResponse,
    PaginatedParkingTransactions,
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
        confirm_detection: bool = False,
    ) -> CheckInResponse:
        key = validate_idempotency_key(
            idempotency_key if idempotency_key is not None else request.idempotency_key
        )
        if request.idempotency_key is not None and request.idempotency_key != key:
            raise AppError(
                status_code=422,
                code="IDEMPOTENCY_KEY_MISMATCH",
                message="Header and body idempotency keys must match.",
            )

        normalized_plate = normalize_plate(request.requested_plate)
        if len(normalized_plate) < 3 or len(normalized_plate) > 50:
            raise AppError(
                status_code=422,
                code="INVALID_PLATE",
                message="The normalized plate must contain 3 to 50 characters.",
            )
        lane = self.repo.get_lane(request.lane_id)
        detection = self.repo.get_detection(request.detection_id) if request.detection_id else None

        # Compute provenance for fingerprint
        ai_plate = detection.normalized_plate if detection else None
        ai_normalized = normalize_plate(ai_plate) if ai_plate else None
        confidence = detection.confidence if detection else None
        source = self._resolve_source(detection is not None, ai_normalized, normalized_plate, request.source)

        fingerprint = fingerprint_payload(
            {
                "operation": "parking.check-in.v2",
                "operator_id": operator.id,
                "lane_id": request.lane_id,
                "normalized_plate": normalized_plate,
                "detection_id": request.detection_id,
                "source": request.source,
                "original_ai_plate": request.original_ai_plate,
                "confidence": request.confidence,
                "notes": request.override_reason,
            }
        )

        existing = self.repo.get_by_idempotency_key(key)
        if existing is not None:
            return self._replay(existing, request, operator, fingerprint, normalized_plate)

        # Now perform validations
        if lane is None:
            raise AppError(
                status_code=404, code="LANE_NOT_FOUND", message="The selected lane does not exist."
            )
        if not lane.is_active:
            raise AppError(
                status_code=400, code="LANE_INACTIVE", message="The selected lane is inactive."
            )
        if lane.direction != LaneDirection.IN:
            raise AppError(
                status_code=400,
                code="INVALID_LANE_TYPE",
                message="Check-in is only allowed on an IN lane.",
            )

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


        duplicate = self.repo.get_active_by_plate(normalized_plate)
        if duplicate:
            raise AppError(
                status_code=409,
                code="PLATE_ALREADY_PARKED",
                message="This plate already has an active PARKED transaction.",
                details={"transaction_id": str(duplicate.id)},
            )


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
                    "lane_snapshot_name": lane.name,
                    "lane_snapshot_direction": lane.direction,
                    "detection_id": request.detection_id,
                    "image_url": image_url,
                    "confidence": confidence,
                    "check_in_operator_id": operator.id,
                    "operator_snapshot_name": operator.display_name,
                    "source": source,
                    "lane_name_snapshot": lane.name,
                    "operator_name_snapshot": operator.display_name,
                    "is_manual_override": source != CheckInSource.AI_ACCEPTED,
                    "notes": request.override_reason,
                    "idempotency_key": key,
                    "request_fingerprint": fingerprint,
                }
            )
            if confirm_detection and detection:
                old_plate = detection.confirmed_plate
                detection.is_confirmed = True
                detection.requires_confirmation = False
                detection.confirmed_plate = normalized_plate
                detection.confirmed_by_id = operator.id
                detection.confirmed_at = datetime.now(UTC)
                log_action(
                    db=self.session,
                    user_id=operator.id,
                    action="CONFIRM_PLATE",
                    entity_type="Detection",
                    entity_id=str(detection.id),
                    old_value={"plate": old_plate or detection.raw_plate},
                    new_value={"plate": normalized_plate, "source": source},
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
            if existing is not None:
                return self._replay(existing, request, operator, fingerprint, normalized_plate)
            duplicate = self.repo.get_active_by_plate(normalized_plate)
            if duplicate:
                raise AppError(
                    status_code=409,
                    code="PLATE_ALREADY_PARKED",
                    message="This plate already has an active PARKED transaction.",
                    details={"transaction_id": str(duplicate.id)},
                ) from exc
            # Unrelated constraint failures are handled by the shared database error handler.
            raise
        self.session.refresh(transaction)
        return CheckInResponse(
            transaction=self.to_response(transaction),
            message="Check-in transaction created.",
        )

    def _replay(
        self, existing, request, operator, fingerprint, normalized_plate
    ) -> CheckInResponse:
        # Preserve retries for transactions written by the initial Phase 2 implementation.
        # Fallback to the requested original_ai_plate for legacy fingerprints
        legacy_ai_plate = request.original_ai_plate or existing.original_ai_plate
        legacy_ai_normalized = normalize_plate(legacy_ai_plate) if legacy_ai_plate else None

        # We need to emulate the old _resolve_source for legacy fingerprint
        requested_source = request.source
        if requested_source == CheckInSource.STATION_AUTO:
            requested_source = CheckInSource.AI_ACCEPTED
        if requested_source == CheckInSource.OPERATOR_MANUAL:
            requested_source = CheckInSource.MANUAL_ENTRY
        if not requested_source:
            if not request.detection_id or not legacy_ai_normalized:
                requested_source = CheckInSource.MANUAL_ENTRY
            else:
                requested_source = (
                    CheckInSource.AI_ACCEPTED
                    if legacy_ai_normalized == normalized_plate
                    else CheckInSource.OPERATOR_CORRECTED
                )

        legacy = fingerprint_payload(
            {
                "lane_id": request.lane_id,
                "normalized_plate": normalized_plate,
                "detection_id": request.detection_id,
                "source": requested_source,
                "ai_plate": legacy_ai_normalized,
                "confidence": request.confidence,
            }
        )

        legacy_matches = (
            existing.request_fingerprint == legacy
            and existing.check_in_operator_id == operator.id
            and existing.notes == request.override_reason
            and (
                request.original_ai_plate is None
                or request.original_ai_plate == existing.original_ai_plate
            )
        )

        # New fingerprint legacy support: the Phase 2 original fingerprint before this change
        intermediate_fingerprint = fingerprint_payload(
            {
                "operation": "parking.check-in.v2",
                "operator_id": operator.id,
                "lane_id": request.lane_id,
                "normalized_plate": normalized_plate,
                "detection_id": request.detection_id,
                "source": request.source,
                "original_ai_plate": request.original_ai_plate,
                "confidence": request.confidence,
                "notes": request.override_reason,
            }
        )

        if not legacy_matches and existing.request_fingerprint != intermediate_fingerprint:
            require_matching_fingerprint(existing.request_fingerprint, fingerprint)

        return CheckInResponse(
            transaction=self.to_response(existing),
            message="The existing check-in transaction was returned.",
        )

    def get_transaction(self, transaction_id: UUID) -> ParkingTransactionResponse:
        transaction = self.repo.get_by_id(transaction_id)
        if transaction is None:
            raise AppError(status_code=404, code="NOT_FOUND", message="Transaction not found.")
        return self.to_response(transaction)

    def list_transactions(
        self, limit: int = 100, offset: int = 0, **filters
    ) -> PaginatedParkingTransactions:
        transactions, total = self.repo.list_transactions(limit=limit, offset=offset, **filters)
        return PaginatedParkingTransactions(
            data=[self.to_response(item) for item in transactions],
            total=total,
            page=offset // limit if limit > 0 else 0,
            limit=limit,
        )

    @staticmethod
    def _resolve_source(
        has_detection: bool,
        ai_plate: str | None,
        final_plate: str,
        requested: str | None = None,
    ) -> str:
        if requested == CheckInSource.STATION_AUTO:
            requested = CheckInSource.AI_ACCEPTED
        if requested == CheckInSource.OPERATOR_MANUAL:
            requested = CheckInSource.MANUAL_ENTRY
            
        if not has_detection or not ai_plate or requested == CheckInSource.MANUAL_ENTRY:
            return CheckInSource.MANUAL_ENTRY
            
        if requested == CheckInSource.OPERATOR_CORRECTED or not ai_plate:
            return CheckInSource.OPERATOR_CORRECTED
            
        return (
            CheckInSource.AI_ACCEPTED
            if ai_plate == final_plate
            else CheckInSource.OPERATOR_CORRECTED
        )

    @staticmethod
    def to_response(transaction: ParkingTransaction) -> ParkingTransactionResponse:
        lane_name = transaction.lane_snapshot_name
        if not lane_name and transaction.lane:
            lane_name = transaction.lane.name

        lane_dir = transaction.lane_snapshot_direction
        if not lane_dir and transaction.lane:
            lane_dir = transaction.lane.direction

        operator_name = transaction.operator_snapshot_name
        if not operator_name and transaction.check_in_operator:
            operator_name = transaction.check_in_operator.display_name

        return ParkingTransactionResponse(
            id=transaction.id,
            license_plate=transaction.license_plate,
            original_ai_plate=transaction.original_ai_plate,
            normalized_plate=transaction.normalized_plate,
            status=transaction.status,
            lane_id=transaction.lane_id,
            lane_name=lane_name,
            lane_direction=lane_dir,
            detection_id=transaction.detection_id,
            image_url=transaction.image_url,
            confidence=transaction.confidence,
            check_in_time=transaction.check_in_time,
            check_in_operator_id=transaction.check_in_operator_id,
            check_in_operator_name=operator_name,
            source=transaction.source,
            is_manual_override=transaction.is_manual_override,
            notes=transaction.notes,
            created_at=transaction.created_at,
        )
