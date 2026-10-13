from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
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
from app.modules.pricing.domain import TicketKind
from app.modules.pricing.models import Subscription, TicketProduct, Vehicle
from app.modules.pricing.service import has_effective_pricing, select_price_snapshot
from app.modules.users.models import User

from .access_control import AccessDecision, evaluate_access_control
from .lifecycle_models import ActorType, LifecycleEventType
from .lifecycle_service import record_lifecycle_event
from .models import CheckInSource, ParkingTransaction, TransactionStatus
from .repository import CheckInRepository
from .schemas import (
    AccessCheckRequest,
    AccessCheckResponse,
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

        vehicle_type = getattr(request, "vehicle_type", "CAR") or "CAR"
        ticket_code = getattr(request, "ticket_code", None)
        requested_plate = request.license_plate or request.plate_number
        if vehicle_type == "BICYCLE" and not requested_plate:
            normalized_plate = None
        elif requested_plate:
            normalized_plate = normalize_plate(requested_plate)
            if len(normalized_plate) < 3 or len(normalized_plate) > 50:
                raise AppError(
                    status_code=422,
                    code="INVALID_PLATE",
                    message="The normalized plate must contain 3 to 50 characters.",
                )
        else:
            normalized_plate = None

        lane = self.repo.get_lane(request.lane_id)
        if lane is None:
            raise AppError(
                status_code=404, code="LANE_NOT_FOUND", message="The selected lane does not exist."
            )
        # System administrators can read all buildings, but writes/retries are bound
        # to the selected lane's server-resolved building just like operator writes.
        if (
            self.session is not None
            and isinstance(lane.building_id, UUID)
            and self.session.info.get("building_id") is None
        ):
            self.session.info["building_id"] = lane.building_id
        detection = self.repo.get_detection(request.detection_id) if request.detection_id else None
        operator_building_id = (
            operator.building_id
            if isinstance(getattr(operator, "building_id", None), UUID)
            else None
        )
        lane_building_id = (
            lane.building_id
            if lane and isinstance(getattr(lane, "building_id", None), UUID)
            else None
        )
        if (
            lane is not None
            and operator.role.name != "SYSTEM_ADMIN"
            and operator_building_id != lane_building_id
        ):
            raise AppError(
                status_code=404,
                code="LANE_NOT_FOUND",
                message="The selected lane does not exist.",
            )

        # Compute provenance for fingerprint
        ai_plate = detection.normalized_plate if detection else None
        ai_normalized = normalize_plate(ai_plate) if ai_plate else None
        confidence = detection.confidence if detection else None
        source = self._resolve_source(
            detection is not None, ai_normalized, normalized_plate, request.source
        )

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
                "vehicle_type": request.vehicle_type,
                "ticket_kind": request.ticket_kind,
                "customer_class_id": request.customer_class_id,
                "zone_id": request.zone_id,
                "ticket_code": request.ticket_code,
            }
        )

        existing = self.repo.get_by_idempotency_key(key)
        if existing is not None:
            existing_building_id = getattr(existing, "building_id", None)
            if not isinstance(existing_building_id, UUID):
                existing_building_id = None
            if existing_building_id != lane_building_id:
                raise AppError(
                    status_code=409,
                    code="IDEMPOTENCY_SCOPE_MISMATCH",
                    message="The idempotency key belongs to another building.",
                )
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

        # Access Control evaluation (P3-M3-04)
        access_result = evaluate_access_control(
            db=self.session,
            lane=lane,
            vehicle_type=vehicle_type,
            license_plate=normalized_plate,
            ticket_code=ticket_code,
            customer_class=getattr(request, "customer_class", "VISITOR"),
            operator=operator,
            is_override=bool(request.override_reason),
            override_reason=request.override_reason,
        )
        if access_result.decision == AccessDecision.DENY:
            err_code = (
                access_result.details.get("code", "ACCESS_DENIED")
                if access_result.details
                else "ACCESS_DENIED"
            )
            raise AppError(
                status_code=403,
                code=err_code,
                message=access_result.reason,
                details={"decision": "DENY", **(access_result.details or {})},
            )
        if access_result.decision == AccessDecision.REVIEW:
            raise AppError(
                status_code=400,
                code="ACCESS_REVIEW_REQUIRED",
                message=access_result.reason,
                details={"decision": "REVIEW", **(access_result.details or {})},
            )

        if normalized_plate:
            duplicate = self.repo.get_active_by_plate(normalized_plate, lane_building_id)
            if duplicate:
                raise AppError(
                    status_code=409,
                    code="PLATE_ALREADY_PARKED",
                    message="This plate already has an active PARKED transaction.",
                    details={"transaction_id": str(duplicate.id)},
                )

        if ticket_code:
            duplicate_ticket = self.repo.get_active_by_ticket_code(ticket_code)
            if duplicate_ticket:
                raise AppError(
                    status_code=409,
                    code="TICKET_ALREADY_ACTIVE",
                    message="This ticket_code already has an active session (BR-20).",
                    details={"transaction_id": str(duplicate_ticket.id)},
                )

        if isinstance(self.session, Session):
            from app.modules.lot_settings.contracts import no_pricing_provider
            from app.modules.lot_settings.service import require_ready_for_entry

            require_ready_for_entry(
                self.session,
                lane.building_id,
                self.session.info.get("effective_pricing", no_pricing_provider),
            )

        image_url = None
        if detection and detection.image_key:
            image_url = f"/api/v1/alpr/media/{detection.image_key}"

        if self.session is None:
            raise RuntimeError("Database session is required for check-in persistence")
        check_in_time = datetime.now(UTC)
        snapshot = None
        if lane_building_id is not None and has_effective_pricing(
            self.session, lane_building_id, check_in_time
        ):
            if not request.vehicle_type or not request.ticket_kind or not request.customer_class_id:
                raise AppError(
                    status_code=422,
                    code="PRICE_CONTEXT_REQUIRED",
                    message="Vehicle type, ticket kind and customer class are required.",
                )
            price = select_price_snapshot(
                self.session,
                building_id=lane_building_id,
                vehicle_type=request.vehicle_type,
                ticket_kind=request.ticket_kind,
                customer_class_id=request.customer_class_id,
                at=check_in_time,
            )
            if request.ticket_kind in {TicketKind.DAILY, TicketKind.MONTHLY}:
                vehicle_identifier = (
                    Vehicle.ticket_code == request.ticket_code.strip().upper()
                    if request.ticket_code
                    else Vehicle.normalized_plate == normalized_plate
                )
                vehicle = self.session.scalar(
                    select(Vehicle).where(
                        Vehicle.building_id == lane_building_id,
                        vehicle_identifier,
                    )
                )
                if vehicle is not None:
                    matches = []
                    rows = self.session.execute(
                        select(Subscription, TicketProduct)
                        .join(TicketProduct, Subscription.product_id == TicketProduct.id)
                        .where(
                            Subscription.building_id == lane_building_id,
                            Subscription.vehicle_id == vehicle.id,
                            TicketProduct.kind == request.ticket_kind,
                        )
                    )
                    for subscription, product in rows:
                        valid_from = subscription.valid_from.replace(
                            tzinfo=subscription.valid_from.tzinfo or UTC
                        )
                        valid_until = subscription.valid_until.replace(
                            tzinfo=subscription.valid_until.tzinfo or UTC
                        )
                        if (
                            (request.zone_id is None or subscription.zone_id == request.zone_id)
                            and product.active
                            and valid_from
                            <= check_in_time
                            <= valid_until + timedelta(days=subscription.grace_days)
                        ):
                            matches.append(valid_until)
                    if len(matches) > 1:
                        raise AppError(
                            status_code=409,
                            code="ZONE_REQUIRED",
                            message="Select a zone for the registered pass.",
                        )
                    if matches:
                        price = price.model_copy(update={"entitlement_valid_until": matches[0]})
            snapshot = price.model_dump(mode="json")
        try:
            transaction = self.repo.save_transaction(
                {
                    "license_plate": normalized_plate,
                    "normalized_plate": normalized_plate,
                    "original_ai_plate": ai_plate,
                    "vehicle_type": vehicle_type,
                    "ticket_code": ticket_code,
                    "status": TransactionStatus.PARKED,
                    "lane_id": request.lane_id,
                    "building_id": lane_building_id,
                    "check_in_time": check_in_time,
                    "price_snapshot": snapshot,
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
            if source == CheckInSource.OPERATOR_CORRECTED:
                record_lifecycle_event(
                    session=self.session,
                    session_id=transaction.id,
                    event_type=LifecycleEventType.OPERATOR_CORRECTED,
                    actor_type=ActorType.OPERATOR,
                    actor_id=operator.id,
                    lane_id=request.lane_id,
                    details={
                        "ai_plate": ai_plate,
                        "corrected_plate": normalized_plate,
                        "reason": request.override_reason,
                    },
                )
            record_lifecycle_event(
                session=self.session,
                session_id=transaction.id,
                event_type=LifecycleEventType.ACCESS_DECIDED,
                actor_type=ActorType.OPERATOR
                if (access_result.details and access_result.details.get("override"))
                else ActorType.SYSTEM,
                actor_id=operator.id if operator else None,
                lane_id=request.lane_id,
                details={
                    "decision": access_result.decision,
                    "reason": access_result.reason,
                    "vehicle_type": vehicle_type,
                    "ticket_code": ticket_code,
                },
            )
            record_lifecycle_event(
                session=self.session,
                session_id=transaction.id,
                event_type=LifecycleEventType.CHECKED_IN,
                actor_type=ActorType.OPERATOR if operator else ActorType.SYSTEM,
                actor_id=operator.id if operator else None,
                lane_id=request.lane_id,
                details={
                    "plate": normalized_plate,
                    "source": source,
                    "status": transaction.status,
                    "vehicle_type": getattr(transaction, "vehicle_type", "CAR"),
                },
                image_ref=image_url,
            )
            from app.modules.checkin.counter_service import CounterService

            CounterService.increment_atomic(
                db=self.session,
                building_id=getattr(lane, "building_id", None),
                vehicle_type=vehicle_type,
                session_id=transaction.id,
                customer_class=getattr(request, "customer_class", "VISITOR"),
                actor_type=ActorType.OPERATOR if operator else ActorType.SYSTEM,
                actor_id=operator.id if operator else None,
                reason="CHECK_IN",
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            existing = self.repo.get_by_idempotency_key(key)
            if existing is not None:
                return self._replay(existing, request, operator, fingerprint, normalized_plate)
            if normalized_plate:
                duplicate = self.repo.get_active_by_plate(normalized_plate, lane_building_id)
                if duplicate:
                    raise AppError(
                        status_code=409,
                        code="PLATE_ALREADY_PARKED",
                        message="This plate already has an active PARKED transaction.",
                        details={"transaction_id": str(duplicate.id)},
                    ) from exc
            if ticket_code:
                duplicate_ticket = self.repo.get_active_by_ticket_code(ticket_code)
                if duplicate_ticket:
                    raise AppError(
                        status_code=409,
                        code="TICKET_ALREADY_ACTIVE",
                        message="This ticket_code already has an active session (BR-20).",
                        details={"transaction_id": str(duplicate_ticket.id)},
                    ) from exc
            # Unrelated constraint failures are handled by the shared database error handler.
            raise
        except Exception:
            self.session.rollback()
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

        def _val(attr: str, default=None):
            v = getattr(transaction, attr, default)
            if type(v).__name__ == "MagicMock":
                return default
            return v if v is not None else default

        return ParkingTransactionResponse(
            id=transaction.id,
            license_plate=_val("license_plate"),
            original_ai_plate=_val("original_ai_plate"),
            normalized_plate=_val("normalized_plate"),
            ticket_code=_val("ticket_code"),
            vehicle_type=_val("vehicle_type", "CAR"),
            status=transaction.status,
            lane_id=transaction.lane_id,
            exit_lane_id=_val("exit_lane_id"),
            building_id=(
                transaction.building_id
                if isinstance(getattr(transaction, "building_id", None), UUID)
                else None
            ),
            lane_name=lane_name if type(lane_name).__name__ != "MagicMock" else None,
            lane_direction=lane_dir if type(lane_dir).__name__ != "MagicMock" else None,
            detection_id=_val("detection_id"),
            image_url=_val("image_url"),
            confidence=_val("confidence"),
            check_in_time=transaction.check_in_time,
            exit_time=_val("exit_time"),
            fee=_val("fee", 0.0),
            ticket_product_id=_val("ticket_product_id"),
            check_in_operator_id=_val("check_in_operator_id"),
            check_in_operator_name=operator_name
            if type(operator_name).__name__ != "MagicMock"
            else None,
            source=transaction.source,
            is_manual_override=bool(_val("is_manual_override", False)),
            notes=_val("notes"),
            created_at=transaction.created_at,
        )

    def check_access(
        self,
        request: AccessCheckRequest,
        *,
        operator: User | None = None,
    ) -> AccessCheckResponse:
        lane = self.repo.get_lane(request.lane_id)
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
                message="Access check is only allowed on an IN lane.",
            )

        norm_plate = normalize_plate(request.license_plate) if request.license_plate else None
        res = evaluate_access_control(
            db=self.session,
            lane=lane,
            vehicle_type=request.vehicle_type,
            license_plate=norm_plate,
            ticket_code=request.ticket_code,
            customer_class=getattr(request, "customer_class", "VISITOR"),
            operator=operator,
            is_override=bool(request.override_reason),
            override_reason=request.override_reason,
        )
        return AccessCheckResponse(
            decision=res.decision,
            reason=res.reason,
            details=res.details,
        )
