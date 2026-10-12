from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.database.session import get_db
from app.modules.audit_logs.service import log_action
from app.modules.auth.dependencies import CurrentUser, require_roles
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

from .domain import FeeResult, PriceSnapshot, TicketKind
from .models import CustomerClass, PricingRule, PricingVersion, TicketProduct
from .schemas import (
    CustomerClassCreate,
    PricingPreviewRequest,
    PricingVersionCreate,
    TicketProductCreate,
)
from .service import create_pricing_version, preview_fee, select_price_snapshot

router = APIRouter(prefix="/pricing", tags=["pricing"])
Db = Annotated[Session, Depends(get_db)]
BuildingAdmin = Annotated[User, Depends(require_roles(RoleName.BUILDING_ADMIN))]


class CustomerClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    discount_percent: int
    active: bool


class TicketProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    kind: TicketKind
    vehicle_type: str
    customer_class_id: UUID | None
    requires_vehicle: bool
    sale_limit: int | None
    active: bool


class CustomerClassUpdate(BaseModel):
    name: str | None = None
    discount_percent: int | None = None
    active: bool | None = None


class TicketProductUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None
    sale_limit: int | None = None


class PricingVersionResponse(BaseModel):
    id: UUID
    version_number: int
    active_from: str
    rules: list[PriceSnapshot]


def _building_id(actor: User) -> UUID:
    if actor.building_id is None:
        raise AppError(
            status_code=403, code="BUILDING_REQUIRED", message="A building assignment is required."
        )
    return actor.building_id


@router.get("/customer-classes", response_model=list[CustomerClassResponse])
def list_customer_classes(
    db: Db, actor: CurrentUser, building_id: UUID | None = None
) -> list[CustomerClass]:
    if actor.role.name == RoleName.SYSTEM_ADMIN and building_id is not None:
        scoped_building_id = building_id
    else:
        scoped_building_id = _building_id(actor)
    return list(
        db.scalars(
            select(CustomerClass)
            .where(CustomerClass.building_id == scoped_building_id)
            .order_by(CustomerClass.code)
        )
    )


@router.post("/customer-classes", response_model=CustomerClassResponse, status_code=201)
def create_customer_class(payload: CustomerClassCreate, db: Db, actor: BuildingAdmin):
    item = CustomerClass(
        building_id=_building_id(actor),
        code=payload.code.upper(),
        name=payload.name.strip(),
        discount_percent=payload.discount_percent,
        active=True,
    )
    db.add(item)
    try:
        db.flush()
        log_action(
            db,
            actor.id,
            "CREATE_CUSTOMER_CLASS",
            "CustomerClass",
            str(item.id),
            new_value=payload.model_dump(mode="json"),
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(status_code=409, code="DUPLICATE_CLASS", message="Class exists.") from exc
    db.refresh(item)
    return item


@router.patch("/customer-classes/{class_id}", response_model=CustomerClassResponse)
def update_customer_class(
    class_id: UUID, payload: CustomerClassUpdate, db: Db, actor: BuildingAdmin
):
    item = db.scalar(
        select(CustomerClass).where(
            CustomerClass.id == class_id, CustomerClass.building_id == _building_id(actor)
        )
    )
    if item is None:
        raise AppError(status_code=404, code="CLASS_NOT_FOUND", message="Class not found.")
    changes = payload.model_dump(exclude_unset=True)
    if not changes or any(value is None for value in changes.values()):
        raise AppError(status_code=422, code="INVALID_UPDATE", message="Provide non-null changes.")
    if "discount_percent" in changes and not 0 <= changes["discount_percent"] <= 100:
        raise AppError(status_code=422, code="INVALID_DISCOUNT", message="Discount must be 0-100.")
    before = {key: getattr(item, key) for key in changes}
    for key, value in changes.items():
        setattr(item, key, value.strip() if key == "name" else value)
    db.flush()
    log_action(
        db,
        actor.id,
        "UPDATE_CUSTOMER_CLASS",
        "CustomerClass",
        str(item.id),
        old_value=before,
        new_value=changes,
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/ticket-products", response_model=list[TicketProductResponse])
def list_ticket_products(db: Db, actor: CurrentUser) -> list[TicketProduct]:
    building_id = _building_id(actor)
    return list(
        db.scalars(
            select(TicketProduct)
            .where(TicketProduct.building_id == building_id)
            .order_by(TicketProduct.code)
        )
    )


@router.post("/ticket-products", response_model=TicketProductResponse, status_code=201)
def create_ticket_product(payload: TicketProductCreate, db: Db, actor: BuildingAdmin):
    building_id = _building_id(actor)
    if (
        payload.customer_class_id
        and db.scalar(
            select(CustomerClass).where(
                CustomerClass.id == payload.customer_class_id,
                CustomerClass.building_id == building_id,
            )
        )
        is None
    ):
        raise AppError(status_code=422, code="INVALID_CUSTOMER_CLASS", message="Invalid class.")
    item = TicketProduct(
        building_id=building_id,
        **payload.model_dump(exclude={"kind"}),
        kind=payload.kind.value,
    )
    db.add(item)
    try:
        db.flush()
        log_action(
            db,
            actor.id,
            "CREATE_TICKET_PRODUCT",
            "TicketProduct",
            str(item.id),
            new_value=payload.model_dump(mode="json"),
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            status_code=409, code="DUPLICATE_PRODUCT", message="Product exists."
        ) from exc
    db.refresh(item)
    return item


@router.patch("/ticket-products/{product_id}", response_model=TicketProductResponse)
def update_ticket_product(
    product_id: UUID, payload: TicketProductUpdate, db: Db, actor: BuildingAdmin
):
    item = db.scalar(
        select(TicketProduct).where(
            TicketProduct.id == product_id, TicketProduct.building_id == _building_id(actor)
        )
    )
    if item is None:
        raise AppError(status_code=404, code="PRODUCT_NOT_FOUND", message="Product not found.")
    changes = payload.model_dump(exclude_unset=True)
    if not changes or any(value is None for value in changes.values()):
        raise AppError(status_code=422, code="INVALID_UPDATE", message="Provide non-null changes.")
    if "sale_limit" in changes and changes["sale_limit"] < 0:
        raise AppError(
            status_code=422, code="INVALID_LIMIT", message="Sale limit cannot be negative."
        )
    before = {key: getattr(item, key) for key in changes}
    for key, value in changes.items():
        setattr(item, key, value.strip() if key == "name" else value)
    db.flush()
    log_action(
        db,
        actor.id,
        "UPDATE_TICKET_PRODUCT",
        "TicketProduct",
        str(item.id),
        old_value=before,
        new_value=changes,
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/versions", response_model=list[PricingVersionResponse])
def list_pricing_versions(db: Db, actor: CurrentUser) -> list[PricingVersionResponse]:
    building_id = _building_id(actor)
    versions = db.scalars(
        select(PricingVersion)
        .where(PricingVersion.building_id == building_id)
        .order_by(PricingVersion.version_number.desc())
    )
    result = []
    for version in versions:
        rules = db.scalars(select(PricingRule).where(PricingRule.version_id == version.id))
        snapshots = []
        for rule in rules:
            customer_class = db.get(CustomerClass, rule.customer_class_id)
            snapshots.append(
                PriceSnapshot.model_validate(
                    {
                        **rule.rule_data,
                        "version_id": version.id,
                        "rule_id": rule.id,
                        "vehicle_type": rule.vehicle_type,
                        "ticket_kind": rule.ticket_kind,
                        "customer_class": customer_class.code,
                    }
                )
            )
        result.append(
            PricingVersionResponse(
                id=version.id,
                version_number=version.version_number,
                active_from=version.active_from.isoformat(),
                rules=snapshots,
            )
        )
    return result


@router.post("/versions", response_model=PricingVersionResponse, status_code=201)
def create_version(payload: PricingVersionCreate, db: Db, actor: BuildingAdmin):
    version = create_pricing_version(
        db, building_id=_building_id(actor), actor_id=actor.id, payload=payload
    )
    return next(item for item in list_pricing_versions(db, actor) if item.id == version.id)


@router.post("/preview", response_model=FeeResult)
def preview(request: PricingPreviewRequest, db: Db, actor: CurrentUser) -> FeeResult:
    return preview_fee(db, building_id=_building_id(actor), request=request)


@router.get("/active", response_model=PriceSnapshot)
def active_price(
    vehicle_type: str,
    ticket_kind: TicketKind,
    customer_class_id: UUID,
    at: str,
    db: Db,
    actor: CurrentUser,
) -> PriceSnapshot:
    from datetime import datetime

    try:
        at_time = datetime.fromisoformat(at)
    except ValueError as exc:
        raise AppError(status_code=422, code="INVALID_TIME", message="Invalid time.") from exc
    if at_time.tzinfo is None:
        raise AppError(status_code=422, code="INVALID_TIME", message="Time must include timezone.")
    return select_price_snapshot(
        db,
        building_id=_building_id(actor),
        vehicle_type=vehicle_type,
        ticket_kind=ticket_kind,
        customer_class_id=customer_class_id,
        at=at_time,
    )
