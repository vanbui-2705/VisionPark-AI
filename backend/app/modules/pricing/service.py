from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.audit_logs.service import log_action
from app.modules.buildings.models import Building

from .domain import FeeResult, PriceSnapshot, TicketKind, calculate_fee
from .models import CustomerClass, PricingRule, PricingVersion
from .schemas import PricingPreviewRequest, PricingVersionCreate


def has_effective_pricing(db: Session, building_id: UUID, at: datetime) -> bool:
    return db.scalar(
        select(PricingVersion.id)
        .where(PricingVersion.building_id == building_id, PricingVersion.active_from <= at)
        .order_by(PricingVersion.active_from.desc())
        .limit(1)
    ) is not None


def create_pricing_version(
    db: Session,
    *,
    building_id: UUID,
    actor_id: UUID,
    payload: PricingVersionCreate,
) -> PricingVersion:
    building = db.scalar(select(Building).where(Building.id == building_id).with_for_update())
    if building is None:
        raise AppError(status_code=404, code="BUILDING_NOT_FOUND", message="Building not found.")
    version_number = (
        db.scalar(
            select(func.max(PricingVersion.version_number)).where(
                PricingVersion.building_id == building_id
            )
        )
        or 0
    ) + 1
    classes = {
        item.id: item
        for item in db.scalars(
            select(CustomerClass).where(CustomerClass.building_id == building_id)
        )
    }
    for rule in payload.rules:
        if rule.customer_class_id not in classes:
            raise AppError(
                status_code=422,
                code="INVALID_CUSTOMER_CLASS",
                message="Customer class does not belong to this building.",
            )
    version = PricingVersion(
        id=uuid4(),
        building_id=building_id,
        version_number=version_number,
        active_from=payload.active_from,
        created_by_id=actor_id,
    )
    db.add(version)
    for rule in payload.rules:
        values = rule.model_dump(
            mode="json", exclude={"vehicle_type", "ticket_kind", "customer_class_id"}
        )
        values["discount_percent"] = classes[rule.customer_class_id].discount_percent
        db.add(
            PricingRule(
                id=uuid4(),
                version_id=version.id,
                vehicle_type=rule.vehicle_type,
                ticket_kind=rule.ticket_kind,
                customer_class_id=rule.customer_class_id,
                rule_data=values,
            )
        )
    log_action(
        db,
        actor_id,
        "CREATE_PRICING_VERSION",
        "PricingVersion",
        str(version.id),
        new_value={"building_id": str(building_id), "version_number": version_number},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            status_code=409,
            code="PRICING_VERSION_CONFLICT",
            message="A pricing version was created concurrently.",
        ) from exc
    db.refresh(version)
    return version


def select_price_snapshot(
    db: Session,
    *,
    building_id: UUID,
    vehicle_type: str,
    ticket_kind: TicketKind,
    customer_class_id: UUID,
    at: datetime,
) -> PriceSnapshot:
    if at.tzinfo is None:
        raise ValueError("Pricing time must include a timezone")
    version = db.scalar(
        select(PricingVersion)
        .where(PricingVersion.building_id == building_id, PricingVersion.active_from <= at)
        .order_by(PricingVersion.active_from.desc(), PricingVersion.version_number.desc())
        .limit(1)
    )
    if version is None:
        raise AppError(
            status_code=409, code="PRICE_UNAVAILABLE", message="No active price version."
        )
    customer_class = db.scalar(
        select(CustomerClass).where(
            CustomerClass.id == customer_class_id,
            CustomerClass.building_id == building_id,
            CustomerClass.active.is_(True),
        )
    )
    if customer_class is None:
        raise AppError(status_code=422, code="INVALID_CUSTOMER_CLASS", message="Invalid class.")
    rule = db.scalar(
        select(PricingRule).where(
            PricingRule.version_id == version.id,
            PricingRule.vehicle_type == vehicle_type,
            PricingRule.ticket_kind == ticket_kind,
            PricingRule.customer_class_id == customer_class_id,
        )
    )
    if rule is None:
        raise AppError(status_code=409, code="PRICE_UNAVAILABLE", message="No matching price rule.")
    return PriceSnapshot.model_validate(
        {
            **rule.rule_data,
            "version_id": version.id,
            "rule_id": rule.id,
            "vehicle_type": vehicle_type,
            "ticket_kind": ticket_kind,
            "customer_class": customer_class.code,
        }
    )


def preview_fee(db: Session, *, building_id: UUID, request: PricingPreviewRequest) -> FeeResult:
    snapshot = select_price_snapshot(
        db,
        building_id=building_id,
        vehicle_type=request.vehicle_type,
        ticket_kind=request.ticket_kind,
        customer_class_id=request.customer_class_id,
        at=request.check_in,
    )
    return calculate_fee(
        check_in=request.check_in,
        check_out=request.check_out,
        snapshot=snapshot,
        lost_ticket=request.lost_ticket,
        overtime=request.overtime,
        extra_free_minutes=request.extra_free_minutes,
    )
