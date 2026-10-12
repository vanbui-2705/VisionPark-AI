"""Building-scoped ticket inventory, subscriptions and access decisions."""

import csv
import io
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.alpr.utils import normalize_plate
from app.core.errors import AppError
from app.database.session import get_db
from app.modules.audit_logs.service import log_action
from app.modules.auth.dependencies import CurrentUser, require_roles
from app.modules.buildings.models import Building
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

from .domain import AccessResult, TicketEntitlement, TicketKind, check_ticket_access
from .models import ClassQuota, CustomerClass, GuestInvite, Subscription, TicketProduct, Vehicle

router = APIRouter(prefix="/tickets", tags=["tickets"])
Db = Annotated[Session, Depends(get_db)]
BuildingAdmin = Annotated[User, Depends(require_roles(RoleName.BUILDING_ADMIN))]


def _building(actor: User) -> UUID:
    if actor.building_id is None:
        raise AppError(
            status_code=403, code="BUILDING_REQUIRED", message="Building assignment required."
        )
    return actor.building_id


class VehicleCreate(BaseModel):
    normalized_plate: str | None = Field(default=None, max_length=50)
    ticket_code: str | None = Field(default=None, max_length=80)
    vehicle_type: str = Field(min_length=1, max_length=40)
    customer_class_id: UUID | None = None

    @model_validator(mode="after")
    def identifier_required(self) -> "VehicleCreate":
        self.normalized_plate = (
            normalize_plate(self.normalized_plate) if self.normalized_plate else None
        )
        self.ticket_code = self.ticket_code.strip().upper() if self.ticket_code else None
        if not (self.normalized_plate or self.ticket_code):
            raise ValueError("Plate or ticket code is required")
        return self


class VehicleResponse(VehicleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class QuotaCreate(BaseModel):
    customer_class_id: UUID
    vehicle_type: str = Field(min_length=1, max_length=40)
    max_active: int = Field(ge=0)


class QuotaResponse(QuotaCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class SubscriptionCreate(BaseModel):
    product_id: UUID
    vehicle_id: UUID
    zone_id: UUID
    valid_from: datetime
    valid_until: datetime
    grace_days: int = Field(default=3, ge=0)

    @model_validator(mode="after")
    def valid_range(self) -> "SubscriptionCreate":
        if (
            self.valid_from.tzinfo is None
            or self.valid_until.tzinfo is None
            or self.valid_until <= self.valid_from
        ):
            raise ValueError("A timezone-aware, increasing validity range is required")
        return self


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    product_id: UUID
    vehicle_id: UUID
    zone_id: UUID
    valid_from: datetime
    valid_until: datetime
    grace_days: int


class InviteCreate(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    resident_vehicle_id: UUID | None = None
    valid_from: datetime
    valid_until: datetime
    free_minutes: int = Field(ge=0)

    @model_validator(mode="after")
    def valid_range(self) -> "InviteCreate":
        if (
            self.valid_from.tzinfo is None
            or self.valid_until.tzinfo is None
            or self.valid_until <= self.valid_from
        ):
            raise ValueError("A timezone-aware, increasing validity range is required")
        return self


class InviteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    resident_vehicle_id: UUID | None
    valid_from: datetime
    valid_until: datetime
    free_minutes: int
    redeemed_at: datetime | None


class AccessRequest(BaseModel):
    at: datetime
    plate: str | None = None
    ticket_code: str | None = None
    zone_id: UUID | None = None


def _class_exists(db: Session, building_id: UUID, class_id: UUID) -> bool:
    return (
        db.scalar(
            select(CustomerClass.id).where(
                CustomerClass.id == class_id, CustomerClass.building_id == building_id
            )
        )
        is not None
    )


@router.get("/vehicles", response_model=list[VehicleResponse])
def list_vehicles(db: Db, actor: CurrentUser) -> list[Vehicle]:
    return list(
        db.scalars(
            select(Vehicle)
            .where(Vehicle.building_id == _building(actor))
            .order_by(Vehicle.created_at.desc())
        )
    )


@router.post("/vehicles", response_model=VehicleResponse, status_code=201)
def create_vehicle(payload: VehicleCreate, db: Db, actor: BuildingAdmin) -> Vehicle:
    building_id = _building(actor)
    if payload.customer_class_id and not _class_exists(db, building_id, payload.customer_class_id):
        raise AppError(status_code=422, code="INVALID_CUSTOMER_CLASS", message="Invalid class.")
    vehicle = Vehicle(building_id=building_id, **payload.model_dump())
    db.add(vehicle)
    try:
        db.flush()
        log_action(
            db,
            actor.id,
            "CREATE_VEHICLE",
            "Vehicle",
            str(vehicle.id),
            new_value=payload.model_dump(mode="json"),
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            status_code=409, code="VEHICLE_EXISTS", message="Vehicle identifier exists."
        ) from exc
    db.refresh(vehicle)
    return vehicle


@router.get("/quotas", response_model=list[QuotaResponse])
def list_quotas(db: Db, actor: CurrentUser) -> list[ClassQuota]:
    return list(db.scalars(select(ClassQuota).where(ClassQuota.building_id == _building(actor))))


@router.put("/quotas", response_model=QuotaResponse)
def set_quota(payload: QuotaCreate, db: Db, actor: BuildingAdmin) -> ClassQuota:
    building_id = _building(actor)
    db.scalar(select(Building.id).where(Building.id == building_id).with_for_update())
    if not _class_exists(db, building_id, payload.customer_class_id):
        raise AppError(status_code=422, code="INVALID_CUSTOMER_CLASS", message="Invalid class.")
    item = db.scalar(
        select(ClassQuota)
        .where(
            ClassQuota.building_id == building_id,
            ClassQuota.customer_class_id == payload.customer_class_id,
            ClassQuota.vehicle_type == payload.vehicle_type,
        )
        .with_for_update()
    )
    old = {"max_active": item.max_active} if item else None
    if item is None:
        item = ClassQuota(building_id=building_id, **payload.model_dump())
        db.add(item)
    else:
        item.max_active = payload.max_active
    db.flush()
    log_action(
        db,
        actor.id,
        "SET_CLASS_QUOTA",
        "ClassQuota",
        str(item.id),
        old_value=old,
        new_value=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/subscriptions", response_model=list[SubscriptionResponse])
def list_subscriptions(db: Db, actor: CurrentUser) -> list[Subscription]:
    return list(
        db.scalars(
            select(Subscription)
            .where(Subscription.building_id == _building(actor))
            .order_by(Subscription.created_at.desc())
        )
    )


@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=201)
def create_subscription(payload: SubscriptionCreate, db: Db, actor: BuildingAdmin) -> Subscription:
    building_id = _building(actor)
    db.scalar(select(Building.id).where(Building.id == building_id).with_for_update())
    product = db.scalar(
        select(TicketProduct).where(
            TicketProduct.id == payload.product_id,
            TicketProduct.building_id == building_id,
            TicketProduct.active.is_(True),
        )
    )
    vehicle = db.scalar(
        select(Vehicle).where(Vehicle.id == payload.vehicle_id, Vehicle.building_id == building_id)
    )
    if product is None or vehicle is None or product.vehicle_type != vehicle.vehicle_type:
        raise AppError(
            status_code=422, code="INVALID_TICKET", message="Product or vehicle is invalid."
        )
    if product.customer_class_id and product.customer_class_id != vehicle.customer_class_id:
        raise AppError(
            status_code=422, code="CLASS_MISMATCH", message="Customer class does not match product."
        )
    if product.sale_limit is not None:
        sold = (
            db.scalar(
                select(func.count())
                .select_from(Subscription)
                .where(Subscription.product_id == product.id)
            )
            or 0
        )
        if sold >= product.sale_limit:
            raise AppError(
                status_code=409, code="SALE_LIMIT", message="Product sale limit reached."
            )
    if vehicle.customer_class_id:
        quota = db.scalar(
            select(ClassQuota).where(
                ClassQuota.building_id == building_id,
                ClassQuota.customer_class_id == vehicle.customer_class_id,
                ClassQuota.vehicle_type == vehicle.vehicle_type,
            )
        )
        if quota is not None:
            occupied = (
                db.scalar(
                    select(func.count())
                    .select_from(Subscription)
                    .join(Vehicle, Subscription.vehicle_id == Vehicle.id)
                    .where(
                        Subscription.building_id == building_id,
                        Vehicle.customer_class_id == vehicle.customer_class_id,
                        Vehicle.vehicle_type == vehicle.vehicle_type,
                        Subscription.valid_until >= datetime.now(UTC),
                    )
                )
                or 0
            )
            if occupied >= quota.max_active:
                raise AppError(
                    status_code=409, code="CLASS_QUOTA", message="Customer class quota reached."
                )
    overlap = db.scalar(
        select(Subscription.id)
        .where(
            Subscription.building_id == building_id,
            Subscription.vehicle_id == vehicle.id,
            Subscription.zone_id == payload.zone_id,
            Subscription.valid_from <= payload.valid_until,
            Subscription.valid_until >= payload.valid_from,
        )
        .limit(1)
    )
    if overlap is not None:
        raise AppError(
            status_code=409,
            code="SUBSCRIPTION_OVERLAP",
            message="Vehicle already has a package in this zone.",
        )
    item = Subscription(building_id=building_id, **payload.model_dump())
    db.add(item)
    db.flush()
    log_action(
        db,
        actor.id,
        "CREATE_SUBSCRIPTION",
        "Subscription",
        str(item.id),
        new_value=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/guest-invites", response_model=list[InviteResponse])
def list_invites(db: Db, actor: CurrentUser) -> list[GuestInvite]:
    return list(
        db.scalars(
            select(GuestInvite)
            .where(GuestInvite.building_id == _building(actor))
            .order_by(GuestInvite.created_at.desc())
        )
    )


@router.post("/guest-invites", response_model=InviteResponse, status_code=201)
def create_invite(payload: InviteCreate, db: Db, actor: BuildingAdmin) -> GuestInvite:
    building_id = _building(actor)
    if (
        payload.resident_vehicle_id
        and db.scalar(
            select(Vehicle.id).where(
                Vehicle.id == payload.resident_vehicle_id, Vehicle.building_id == building_id
            )
        )
        is None
    ):
        raise AppError(status_code=422, code="INVALID_VEHICLE", message="Invalid resident vehicle.")
    item = GuestInvite(building_id=building_id, **payload.model_dump())
    db.add(item)
    try:
        db.flush()
        log_action(
            db,
            actor.id,
            "CREATE_GUEST_INVITE",
            "GuestInvite",
            str(item.id),
            new_value=payload.model_dump(mode="json"),
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            status_code=409, code="INVITE_EXISTS", message="Invite code exists."
        ) from exc
    db.refresh(item)
    return item


@router.post("/access", response_model=AccessResult)
def access_decision(payload: AccessRequest, db: Db, actor: CurrentUser) -> AccessResult:
    building_id = _building(actor)
    if payload.at.tzinfo is None:
        raise AppError(status_code=422, code="INVALID_TIME", message="Time must include timezone.")
    plate = normalize_plate(payload.plate) if payload.plate else None
    code = payload.ticket_code.strip().upper() if payload.ticket_code else None
    vehicle = (
        db.scalar(
            select(Vehicle).where(
                Vehicle.building_id == building_id,
                (Vehicle.normalized_plate == plate) if plate else (Vehicle.ticket_code == code),
            )
        )
        if (plate or code)
        else None
    )
    if vehicle is None:
        return check_ticket_access(
            None, at=payload.at, plate=plate, ticket_code=code, zone_id=payload.zone_id
        )
    subscriptions = db.scalars(
        select(Subscription)
        .where(Subscription.building_id == building_id, Subscription.vehicle_id == vehicle.id)
        .order_by(Subscription.valid_until.desc())
    )
    last_result = None
    for subscription in subscriptions:
        product = db.get(TicketProduct, subscription.product_id)
        result = check_ticket_access(
            TicketEntitlement(
                kind=TicketKind(product.kind),
                plate=vehicle.normalized_plate,
                ticket_code=vehicle.ticket_code,
                zone_id=subscription.zone_id,
                valid_from=subscription.valid_from.replace(
                    tzinfo=subscription.valid_from.tzinfo or UTC
                ),
                valid_until=subscription.valid_until.replace(
                    tzinfo=subscription.valid_until.tzinfo or UTC
                ),
                grace_days=subscription.grace_days,
            ),
            at=payload.at,
            plate=plate,
            ticket_code=code,
            zone_id=payload.zone_id,
        )
        if result.decision.value == "ALLOW":
            return result
        last_result = result
    return last_result or check_ticket_access(
        None, at=payload.at, plate=plate, ticket_code=code, zone_id=payload.zone_id
    )


@router.post("/vehicles/import", response_model=dict)
async def import_vehicles(db: Db, actor: BuildingAdmin, file: UploadFile = File(...)) -> dict:
    raw = await file.read(1_000_001)
    if len(raw) > 1_000_000:
        raise AppError(status_code=413, code="CSV_TOO_LARGE", message="CSV exceeds 1 MB.")
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
    except (UnicodeError, csv.Error) as exc:
        raise AppError(status_code=422, code="INVALID_CSV", message="Invalid CSV.") from exc
    if (
        len(rows) > 1000
        or not reader.fieldnames
        or not {"normalized_plate", "vehicle_type", "customer_class_id"}.issubset(reader.fieldnames)
    ):
        raise AppError(
            status_code=422, code="INVALID_CSV", message="CSV columns or row count invalid."
        )
    building_id = _building(actor)
    for row in rows:
        item = VehicleCreate.model_validate({key: value or None for key, value in row.items()})
        if item.customer_class_id and not _class_exists(db, building_id, item.customer_class_id):
            raise AppError(status_code=422, code="INVALID_CUSTOMER_CLASS", message="Invalid class.")
        db.add(Vehicle(building_id=building_id, **item.model_dump()))
    try:
        db.flush()
        log_action(
            db,
            actor.id,
            "IMPORT_VEHICLES",
            "Vehicle",
            str(building_id),
            new_value={"count": len(rows)},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            status_code=409,
            code="VEHICLE_EXISTS",
            message="CSV contains duplicate vehicle identifiers.",
        ) from exc
    return {"imported": len(rows)}
