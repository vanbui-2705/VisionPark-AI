"""Idempotent acceptance/demo environment provisioning & readiness checker (BUILD-04 / DEMO-10).

Usage:
    py -3 backend/scripts/seed_demo_environment.py --check
    py -3 backend/scripts/seed_demo_environment.py --apply
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database.session import DatabaseManager  # noqa: E402
from app.modules.buildings.models import Building, ParkingLot, UserBuilding  # noqa: E402
from app.modules.checkin.counter_models import ParkingCounter  # noqa: E402
from app.modules.checkin.models import ParkingTransaction, TransactionStatus  # noqa: E402
from app.modules.lanes.models import Lane, LaneDirection  # noqa: E402
from app.modules.lot_settings.schemas import default_settings  # noqa: E402
from app.modules.pricing.domain import TicketKind  # noqa: E402
from app.modules.pricing.models import (  # noqa: E402
    CustomerClass,
    PricingRule,
    PricingVersion,
    Subscription,
    TicketProduct,
    Vehicle,
)
from app.modules.users.models import Role, User  # noqa: E402
from app.modules.users.schemas import RoleName  # noqa: E402

DEMO_BUILDING_CODE = "DEMO-BUILDING"
DEMO_BUILDING_NAME = "VisionPark Acceptance Demo Building"
DEMO_LANE_IN = "DEMO-IN-01"
DEMO_LANE_OUT = "DEMO-OUT-01"
DEMO_ADMIN_USERNAME = "demo_building_admin"
DEMO_OPERATOR_USERNAME = "demo_operator"
DEMO_ACCOUNTANT_USERNAME = "demo_accountant"
DEMO_MONTHLY_PRODUCT_CODE = "DEMO-MONTHLY-CAR"
DEMO_MONTHLY_PLATE = "30A88888"
DEMO_STANDARD_CLASS_CODE = "STANDARD"
DEMO_ZONE_UUID = uuid5(NAMESPACE_URL, "visionpark:demo-zone:DEMO-BUILDING:ZONE-A")

VEHICLE_CAPACITIES: dict[str, tuple[int, int]] = {
    "CAR": (100, 100),
    "MOTORBIKE": (200, 200),
    "BICYCLE": (50, 50),
}

VEHICLE_PRICING_DEFAULTS: dict[str, dict[str, int]] = {
    "CAR": {
        "free_minutes": 15,
        "initial_minutes": 60,
        "initial_fee": 15000,
        "block_minutes": 60,
        "block_fee": 10000,
        "daily_cap": 120000,
        "overnight_fee": 30000,
        "lost_ticket_fee": 50000,
        "overtime_fee": 15000,
        "day_pass_fee": 80000,
        "month_pass_fee": 1200000,
    },
    "MOTORBIKE": {
        "free_minutes": 15,
        "initial_minutes": 60,
        "initial_fee": 5000,
        "block_minutes": 60,
        "block_fee": 3000,
        "daily_cap": 30000,
        "overnight_fee": 10000,
        "lost_ticket_fee": 20000,
        "overtime_fee": 5000,
        "day_pass_fee": 20000,
        "month_pass_fee": 150000,
    },
    "BICYCLE": {
        "free_minutes": 15,
        "initial_minutes": 60,
        "initial_fee": 2000,
        "block_minutes": 60,
        "block_fee": 1000,
        "daily_cap": 10000,
        "overnight_fee": 5000,
        "lost_ticket_fee": 10000,
        "overtime_fee": 2000,
        "day_pass_fee": 8000,
        "month_pass_fee": 60000,
    },
}


def verify_safe_target_database(
    database_url: str,
    *,
    environment: str = "development",
    confirm_non_local: bool = False,
) -> None:
    """Refuse to mutate production or non-local databases without explicit confirmation."""
    env_norm = (environment or "").strip().lower()
    if env_norm in {"production", "prod"} and not confirm_non_local:
        raise RuntimeError(
            "Refusing to run demo seed against ENVIRONMENT=production without --confirm-non-local."
        )
    parsed = make_url(database_url)
    host = (parsed.host or "").strip().lower()
    is_local = parsed.drivername.startswith("sqlite") or host in {
        "",
        "localhost",
        "127.0.0.1",
        "::1",
        "postgres",
        "db",
    }
    if not is_local and not confirm_non_local:
        raise RuntimeError(
            f"Refusing to run demo seed against non-local database host '{host}' "
            "without --confirm-non-local."
        )


def _resolve_demo_password(env_names: tuple[str, ...]) -> tuple[str, bool]:
    for name in env_names:
        val = os.environ.get(name, "").strip()
        if len(val) >= 8:
            return val, False
    generated = f"Demo#{secrets.token_urlsafe(12)}"
    return generated, True


def check_demo_environment(
    session: Session,
    *,
    building_code: str = DEMO_BUILDING_CODE,
) -> dict[str, Any]:
    """Non-destructive check of all 7 DEMO-10 acceptance environment requirements."""
    now = datetime.now(UTC)
    issues: list[str] = []
    details: dict[str, Any] = {"building_code": building_code}

    # 1. Building
    building = session.scalar(select(Building).where(Building.code == building_code))
    if building is None or not building.is_active:
        issues.append(f"Missing or inactive building '{building_code}'")
        return {"ready": False, "issues": issues, "details": details}

    building_id = building.id
    details["building_id"] = str(building_id)

    # 2. Users (BUILDING_ADMIN & OPERATOR)
    for username, expected_role in (
        (DEMO_ADMIN_USERNAME, RoleName.BUILDING_ADMIN.value),
        (DEMO_OPERATOR_USERNAME, RoleName.OPERATOR.value),
    ):
        user = session.scalar(select(User).where(User.username == username))
        if user is None or not user.is_active:
            issues.append(f"Missing or inactive user '{username}'")
            continue
        if user.must_change_password:
            issues.append(f"User '{username}' is blocked by must_change_password=True")
        role = session.get(Role, user.role_id)
        if role is None or role.name != expected_role:
            issues.append(f"User '{username}' does not have role '{expected_role}'")
        membership = session.scalar(
            select(UserBuilding).where(
                UserBuilding.user_id == user.id,
                UserBuilding.building_id == building_id,
            )
        )
        if membership is None:
            issues.append(f"User '{username}' is not assigned to building '{building_code}'")

    # 3. Active IN & OUT lanes
    lane_in = session.scalar(
        select(Lane).where(
            Lane.building_id == building_id,
            Lane.name == DEMO_LANE_IN,
            Lane.direction == LaneDirection.IN,
            Lane.is_active.is_(True),
        )
    )
    lane_out = session.scalar(
        select(Lane).where(
            Lane.building_id == building_id,
            Lane.name == DEMO_LANE_OUT,
            Lane.direction == LaneDirection.OUT,
            Lane.is_active.is_(True),
        )
    )
    if lane_in is None:
        issues.append(f"Missing active IN lane '{DEMO_LANE_IN}'")
    else:
        details["lane_in_id"] = str(lane_in.id)
    if lane_out is None:
        issues.append(f"Missing active OUT lane '{DEMO_LANE_OUT}'")
    else:
        details["lane_out_id"] = str(lane_out.id)

    # 4. Lot capacities > 0 for CAR, MOTORBIKE, BICYCLE
    lot = session.scalar(select(ParkingLot).where(ParkingLot.building_id == building_id))
    if lot is None or not isinstance(lot.settings, dict):
        issues.append(f"Missing active ParkingLot settings for '{building_code}'")
    else:
        caps = lot.settings.get("capacities") or {}
        for vtype in ("CAR", "MOTORBIKE", "BICYCLE"):
            vcap = caps.get(vtype) if isinstance(caps, dict) else None
            safe_cap = int((vcap or {}).get("safe_capacity", 0) or 0)
            if safe_cap <= 0:
                issues.append(f"safe_capacity for {vtype} must be > 0 (got {safe_cap})")

    # 5. Effective PricingVersion + rules for CAR, MOTORBIKE, BICYCLE with lost_ticket_fee
    std_class = session.scalar(
        select(CustomerClass).where(
            CustomerClass.building_id == building_id,
            CustomerClass.code == DEMO_STANDARD_CLASS_CODE,
            CustomerClass.active.is_(True),
        )
    )
    if std_class is None:
        issues.append(f"Missing active CustomerClass '{DEMO_STANDARD_CLASS_CODE}'")
    else:
        details["customer_class_id"] = str(std_class.id)

    version = session.scalar(
        select(PricingVersion)
        .where(
            PricingVersion.building_id == building_id,
            PricingVersion.active_from <= now,
        )
        .order_by(PricingVersion.active_from.desc(), PricingVersion.version_number.desc())
        .limit(1)
    )
    if version is None:
        issues.append("Missing effective PricingVersion (active_from <= now)")
    elif std_class is not None:
        details["pricing_version_id"] = str(version.id)
        for vtype in ("CAR", "MOTORBIKE", "BICYCLE"):
            rule = session.scalar(
                select(PricingRule).where(
                    PricingRule.version_id == version.id,
                    PricingRule.vehicle_type == vtype,
                    PricingRule.ticket_kind == TicketKind.HOURLY.value,
                    PricingRule.customer_class_id == std_class.id,
                )
            )
            if rule is None:
                issues.append(f"Missing HOURLY PricingRule for {vtype}")
            elif int((rule.rule_data or {}).get("lost_ticket_fee", 0) or 0) <= 0:
                issues.append(f"PricingRule for {vtype} is missing positive lost_ticket_fee")

    # 6. Active MONTHLY TicketProduct, Vehicle, and valid Subscription
    product = session.scalar(
        select(TicketProduct).where(
            TicketProduct.building_id == building_id,
            TicketProduct.code == DEMO_MONTHLY_PRODUCT_CODE,
            TicketProduct.kind == TicketKind.MONTHLY.value,
            TicketProduct.active.is_(True),
        )
    )
    vehicle = session.scalar(
        select(Vehicle).where(
            Vehicle.building_id == building_id,
            Vehicle.normalized_plate == DEMO_MONTHLY_PLATE,
        )
    )
    if product is None:
        issues.append(f"Missing active MONTHLY TicketProduct '{DEMO_MONTHLY_PRODUCT_CODE}'")
    if vehicle is None:
        issues.append(f"Missing sample monthly Vehicle '{DEMO_MONTHLY_PLATE}'")
    if product is not None and vehicle is not None:
        sub = session.scalar(
            select(Subscription)
            .where(
                Subscription.building_id == building_id,
                Subscription.product_id == product.id,
                Subscription.vehicle_id == vehicle.id,
            )
            .order_by(Subscription.valid_until.desc())
        )
        if sub is None:
            issues.append(f"Missing Subscription for vehicle '{DEMO_MONTHLY_PLATE}'")
        else:
            valid_from = (
                sub.valid_from if sub.valid_from.tzinfo else sub.valid_from.replace(tzinfo=UTC)
            )
            valid_until = (
                sub.valid_until if sub.valid_until.tzinfo else sub.valid_until.replace(tzinfo=UTC)
            )
            if not (valid_from <= now <= valid_until):
                issues.append(
                    f"Subscription for '{DEMO_MONTHLY_PLATE}' is expired or not yet active"
                )
            else:
                details["monthly_vehicle_plate"] = DEMO_MONTHLY_PLATE
                details["subscription_id"] = str(sub.id)

    # 7. ParkingCounter matches actual PARKED sessions for CAR, MOTORBIKE, BICYCLE
    for vtype in ("CAR", "MOTORBIKE", "BICYCLE"):
        actual_parked = (
            session.scalar(
                select(func.count())
                .select_from(ParkingTransaction)
                .where(
                    ParkingTransaction.building_id == building_id,
                    ParkingTransaction.vehicle_type == vtype,
                    ParkingTransaction.status == TransactionStatus.PARKED,
                )
            )
            or 0
        )
        counter = session.scalar(
            select(ParkingCounter).where(
                ParkingCounter.building_id == building_id,
                ParkingCounter.vehicle_type == vtype,
            )
        )
        if counter is None:
            issues.append(f"Missing ParkingCounter row for {vtype}")
        elif int(counter.occupied) != int(actual_parked):
            issues.append(
                f"ParkingCounter drift for {vtype}: occupied={counter.occupied} "
                f"!= actual_parked={actual_parked}"
            )

    return {
        "ready": len(issues) == 0,
        "issues": issues,
        "details": details,
    }


def apply_demo_environment(
    session: Session,
    *,
    building_code: str = DEMO_BUILDING_CODE,
    admin_password: str | None = None,
    operator_password: str | None = None,
    reset_open_sessions: bool = True,
) -> dict[str, Any]:
    """Idempotently provision/update the DEMO-BUILDING acceptance namespace (DEMO-10)."""
    now = datetime.now(UTC)
    generated_credentials: dict[str, str] = {}

    if not admin_password:
        admin_password, was_gen = _resolve_demo_password(
            ("DEMO_ADMIN_PASSWORD", "DEMO_SEED_PASSWORD", "SEED_ADMIN_PASSWORD")
        )
        if was_gen:
            generated_credentials[DEMO_ADMIN_USERNAME] = admin_password
    if not operator_password:
        operator_password, was_gen = _resolve_demo_password(
            ("DEMO_OPERATOR_PASSWORD", "DEMO_SEED_PASSWORD", "SEED_OPERATOR_PASSWORD")
        )
        if was_gen:
            generated_credentials[DEMO_OPERATOR_USERNAME] = operator_password

    building_id = uuid5(NAMESPACE_URL, f"visionpark:demo-building:{building_code}")
    building = session.scalar(select(Building).where(Building.code == building_code))
    if building is None:
        building = session.get(Building, building_id)
    if building is None:
        building = Building(
            id=building_id,
            code=building_code,
            name=DEMO_BUILDING_NAME,
            timezone="Asia/Ho_Chi_Minh",
            is_active=True,
        )
        session.add(building)
        session.flush()
    else:
        building.is_active = True
        building_id = building.id

    # ParkingLot + capacities
    lot = session.scalar(select(ParkingLot).where(ParkingLot.building_id == building_id))
    cfg = default_settings(building)
    cfg.ai.plate_confidence = 0.85
    for vtype, (phys, safe) in VEHICLE_CAPACITIES.items():
        if vtype in cfg.capacities:
            cfg.capacities[vtype].physical_capacity = phys
            cfg.capacities[vtype].safe_capacity = safe
    if lot is None:
        lot = ParkingLot(
            building_id=building_id,
            settings=cfg.model_dump(mode="json"),
            settings_revision=1,
        )
        session.add(lot)
    else:
        lot.settings = cfg.model_dump(mode="json")
        lot.settings_revision = int(lot.settings_revision or 0) + 1
    session.flush()

    # Roles & Users
    users_by_role: dict[str, User] = {}
    for username, role_enum, pwd in (
        (DEMO_ADMIN_USERNAME, RoleName.BUILDING_ADMIN, admin_password),
        (DEMO_OPERATOR_USERNAME, RoleName.OPERATOR, operator_password),
        (DEMO_ACCOUNTANT_USERNAME, RoleName.ACCOUNTANT, operator_password),
    ):
        role = session.scalar(select(Role).where(Role.name == role_enum.value))
        if role is None:
            role = Role(name=role_enum.value, description=f"Role {role_enum.value}")
            session.add(role)
            session.flush()

        user = session.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(
                username=username,
                display_name=f"Demo {role_enum.value.title().replace('_', ' ')}",
                password_hash=hash_password(pwd),
                role_id=role.id,
                is_active=True,
                must_change_password=False,
            )
            session.add(user)
            session.flush()
        else:
            user.role_id = role.id
            user.is_active = True
            user.must_change_password = False
            # Update password if explicitly provided via parameter or env var
            if username not in generated_credentials:
                user.password_hash = hash_password(pwd)
            session.flush()

        membership = session.scalar(
            select(UserBuilding).where(
                UserBuilding.user_id == user.id,
                UserBuilding.building_id == building_id,
            )
        )
        if membership is None:
            session.add(UserBuilding(user_id=user.id, building_id=building_id))
            session.flush()
        users_by_role[role_enum.value] = user

    admin_user = users_by_role[RoleName.BUILDING_ADMIN.value]

    # Lanes (DEMO-IN-01 & DEMO-OUT-01)
    for lane_name, direction, barrier_id in (
        (DEMO_LANE_IN, LaneDirection.IN, "BARRIER-DEMO-IN-01"),
        (DEMO_LANE_OUT, LaneDirection.OUT, "BARRIER-DEMO-OUT-01"),
    ):
        lane = session.scalar(
            select(Lane).where(Lane.building_id == building_id, Lane.name == lane_name)
        )
        if lane is None:
            lane = Lane(
                building_id=building_id,
                name=lane_name,
                direction=direction,
                barrier_id=barrier_id,
                video_source=f"fixture://acceptance/{lane_name.lower()}.mp4",
                is_active=True,
            )
            session.add(lane)
        else:
            lane.direction = direction
            lane.barrier_id = barrier_id
            lane.is_active = True
    session.flush()

    # CustomerClass STANDARD
    std_class = session.scalar(
        select(CustomerClass).where(
            CustomerClass.building_id == building_id,
            CustomerClass.code == DEMO_STANDARD_CLASS_CODE,
        )
    )
    if std_class is None:
        std_class = CustomerClass(
            building_id=building_id,
            code=DEMO_STANDARD_CLASS_CODE,
            name="Khách tiêu chuẩn",
            discount_percent=0,
            active=True,
        )
        session.add(std_class)
        session.flush()
    else:
        std_class.active = True
        session.flush()

    # PricingVersion + PricingRules
    effective_from = datetime(2026, 1, 1, tzinfo=UTC)
    version = session.scalar(
        select(PricingVersion)
        .where(
            PricingVersion.building_id == building_id,
            PricingVersion.active_from <= now,
        )
        .order_by(PricingVersion.active_from.desc(), PricingVersion.version_number.desc())
        .limit(1)
    )
    if version is None:
        next_ver = (
            session.scalar(
                select(func.max(PricingVersion.version_number)).where(
                    PricingVersion.building_id == building_id
                )
            )
            or 0
        ) + 1
        version = PricingVersion(
            building_id=building_id,
            version_number=next_ver,
            active_from=effective_from,
            created_by_id=admin_user.id,
        )
        session.add(version)
        session.flush()

    for vtype, rule_cfg in VEHICLE_PRICING_DEFAULTS.items():
        for kind in (TicketKind.HOURLY.value, TicketKind.MONTHLY.value):
            rule_payload = {
                "customer_class": std_class.code,
                "discount_percent": std_class.discount_percent,
                **rule_cfg,
                "windows": [],
            }
            existing_rule = session.scalar(
                select(PricingRule).where(
                    PricingRule.version_id == version.id,
                    PricingRule.vehicle_type == vtype,
                    PricingRule.ticket_kind == kind,
                    PricingRule.customer_class_id == std_class.id,
                )
            )
            if existing_rule is None:
                session.add(
                    PricingRule(
                        version_id=version.id,
                        vehicle_type=vtype,
                        ticket_kind=kind,
                        customer_class_id=std_class.id,
                        rule_data=rule_payload,
                    )
                )
            else:
                existing_rule.rule_data = rule_payload
    session.flush()

    # Monthly TicketProduct, Vehicle, and active Subscription
    product = session.scalar(
        select(TicketProduct).where(
            TicketProduct.building_id == building_id,
            TicketProduct.code == DEMO_MONTHLY_PRODUCT_CODE,
        )
    )
    if product is None:
        product = TicketProduct(
            building_id=building_id,
            code=DEMO_MONTHLY_PRODUCT_CODE,
            name="Vé tháng Ô tô Demo",
            kind=TicketKind.MONTHLY.value,
            vehicle_type="CAR",
            customer_class_id=std_class.id,
            requires_vehicle=True,
            sale_limit=100,
            active=True,
        )
        session.add(product)
        session.flush()
    else:
        product.kind = TicketKind.MONTHLY.value
        product.vehicle_type = "CAR"
        product.customer_class_id = std_class.id
        product.active = True
        session.flush()

    vehicle = session.scalar(
        select(Vehicle).where(
            Vehicle.building_id == building_id,
            Vehicle.normalized_plate == DEMO_MONTHLY_PLATE,
        )
    )
    if vehicle is None:
        vehicle = Vehicle(
            building_id=building_id,
            normalized_plate=DEMO_MONTHLY_PLATE,
            vehicle_type="CAR",
            customer_class_id=std_class.id,
        )
        session.add(vehicle)
        session.flush()
    else:
        vehicle.vehicle_type = "CAR"
        vehicle.customer_class_id = std_class.id
        session.flush()

    sub = session.scalar(
        select(Subscription)
        .where(
            Subscription.building_id == building_id,
            Subscription.product_id == product.id,
            Subscription.vehicle_id == vehicle.id,
        )
        .order_by(Subscription.valid_until.desc())
    )
    valid_from = now - timedelta(days=7)
    valid_until = now + timedelta(days=30)
    if sub is None:
        sub = Subscription(
            building_id=building_id,
            product_id=product.id,
            vehicle_id=vehicle.id,
            zone_id=DEMO_ZONE_UUID,
            valid_from=valid_from,
            valid_until=valid_until,
            grace_days=3,
        )
        session.add(sub)
    else:
        sub.valid_from = valid_from
        sub.valid_until = valid_until
        sub.grace_days = 3
    session.flush()

    # Reset open sessions only within DEMO-BUILDING if requested
    if reset_open_sessions:
        open_txs = list(
            session.scalars(
                select(ParkingTransaction).where(
                    ParkingTransaction.building_id == building_id,
                    ParkingTransaction.status.in_(
                        [
                            TransactionStatus.PARKED,
                            TransactionStatus.PAYMENT_PENDING,
                            TransactionStatus.PAID,
                        ]
                    ),
                )
            )
        )
        for tx in open_txs:
            tx.status = TransactionStatus.CANCELLED
            tx.exit_time = now
            tx.notes = (tx.notes or "") + "\n[DEMO_RESET]"
        session.flush()

    # Reconcile ParkingCounter rows for DEMO-BUILDING
    for vtype in ("CAR", "MOTORBIKE", "BICYCLE"):
        actual_parked = (
            session.scalar(
                select(func.count())
                .select_from(ParkingTransaction)
                .where(
                    ParkingTransaction.building_id == building_id,
                    ParkingTransaction.vehicle_type == vtype,
                    ParkingTransaction.status == TransactionStatus.PARKED,
                )
            )
            or 0
        )
        counter = session.scalar(
            select(ParkingCounter).where(
                ParkingCounter.building_id == building_id,
                ParkingCounter.vehicle_type == vtype,
            )
        )
        if counter is None:
            counter = ParkingCounter(
                building_id=building_id,
                vehicle_type=vtype,
                occupied=int(actual_parked),
            )
            session.add(counter)
        else:
            counter.occupied = int(actual_parked)
    session.flush()
    session.commit()

    check_res = check_demo_environment(session, building_code=building_code)
    if generated_credentials:
        check_res["generated_credentials"] = generated_credentials
    return check_res


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check or apply the idempotent DEMO-BUILDING acceptance environment (DEMO-10)."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="Verify acceptance environment readiness without modifying the database.",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Idempotently provision/update the DEMO-BUILDING acceptance namespace.",
    )
    parser.add_argument(
        "--building-code",
        default=DEMO_BUILDING_CODE,
        help=f"Target demo building code (default: {DEMO_BUILDING_CODE}).",
    )
    parser.add_argument(
        "--keep-open-sessions",
        action="store_true",
        help="Do not cancel existing open sessions inside the demo building on --apply.",
    )
    parser.add_argument(
        "--confirm-non-local",
        action="store_true",
        help="Explicitly confirm running --apply on a non-local database host.",
    )
    args = parser.parse_args(argv)

    settings = Settings()
    if args.apply:
        verify_safe_target_database(
            settings.database_url,
            environment=settings.environment,
            confirm_non_local=args.confirm_non_local,
        )

    manager = DatabaseManager()
    manager.configure(settings.database_url)
    try:
        with manager.create_session() as session:
            if args.check:
                result = check_demo_environment(session, building_code=args.building_code)
            else:
                result = apply_demo_environment(
                    session,
                    building_code=args.building_code,
                    reset_open_sessions=not args.keep_open_sessions,
                )
    finally:
        manager.dispose()

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
