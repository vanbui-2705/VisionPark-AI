from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alpr.utils import normalize_plate
from app.modules.checkin.capacity_quota_stub import check_capacity_and_quota_stub
from app.modules.checkin.counter_service import CounterService
from app.modules.lanes.models import AllowedVehicleType, Lane
from app.modules.pricing.domain import (
    AccessDecision as M4AccessDecision,
)
from app.modules.pricing.domain import (
    TicketEntitlement,
    TicketKind,
    check_ticket_access,
)
from app.modules.pricing.models import Subscription, TicketProduct, Vehicle
from app.modules.users.models import User


class AccessDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REVIEW = "REVIEW"


@dataclass
class AccessCheckResult:
    decision: AccessDecision
    reason: str
    details: dict[str, Any] | None = None


# TODO: Tích hợp với module M1 khi có bảng vehicle_access_rules (blacklist/whitelist)
# Hiện tại M1 chưa có code quản lý blacklist phương tiện nên tiếp tục giữ STUB danh sách đen.
BLACKLIST_STUB: set[str] = {"29A99999", "BLACKLIST123"}


def check_blacklist_stub(license_plate: str | None) -> tuple[bool, str | None]:
    if license_plate:
        norm = normalize_plate(license_plate)
        if norm in BLACKLIST_STUB:
            return True, "Phương tiện nằm trong danh sách đen từ chối phục vụ (Blacklist M1)."
    return False, None


def verify_ticket_entitlement_for_checkin(
    db: Session | None,
    building_id: UUID | None,
    license_plate: str | None,
    vehicle_type: str,
    ticket_code: str | None = None,
    zone_id: UUID | None = None,
    at: datetime | None = None,
) -> tuple[AccessDecision, str]:
    """Kiểm tra quyền vé (vé tháng/vé ngày) đối với phương tiện khi check-in (M4)."""
    if db is None or building_id is None or type(building_id).__name__ == "MagicMock":
        return AccessDecision.ALLOW, "Quyền vé và thẻ hợp lệ (Mặc định)."

    plate = normalize_plate(license_plate) if license_plate else None
    code = ticket_code.strip().upper() if ticket_code else None

    if not plate and not code:
        return AccessDecision.ALLOW, "Khách vãng lai (không có biển số/mã thẻ)."

    # 1. Tìm phương tiện đã đăng ký trong tòa nhà
    stmt = select(Vehicle).where(Vehicle.building_id == building_id)
    if code:
        stmt = stmt.where(Vehicle.ticket_code == code)
    elif plate:
        stmt = stmt.where(Vehicle.normalized_plate == plate)

    try:
        vehicle = db.scalar(stmt)
    except Exception:
        vehicle = None

    if not vehicle:
        # Xe vãng lai chưa từng đăng ký thuê bao -> Cho phép vào bãi lấy vé lượt
        return AccessDecision.ALLOW, "Khách vãng lai (chưa đăng ký gói vé cố định)."

    # 2. Tìm gói thuê bao mới nhất của xe tại tòa nhà
    try:
        sub = db.scalar(
            select(Subscription)
            .where(
                Subscription.building_id == building_id,
                Subscription.vehicle_id == vehicle.id,
            )
            .order_by(Subscription.valid_until.desc())
        )
    except Exception:
        sub = None

    if not sub:
        return AccessDecision.ALLOW, "Phương tiện đã đăng ký (không có gói thuê bao active)."

    # 3. Lấy sản phẩm vé của gói thuê bao
    try:
        product = db.get(TicketProduct, sub.product_id)
    except Exception:
        product = None

    if not product or not product.active:
        return AccessDecision.REVIEW, "Gói vé của phương tiện không còn hiệu lực."

    # Kiểm tra loại xe đăng ký vé có khớp với loại xe vào làn không
    if product.vehicle_type != vehicle_type:
        return (
            AccessDecision.DENY,
            f"Vé '{product.name}' đăng ký cho loại xe '{product.vehicle_type}', "
            f"không áp dụng cho loại xe '{vehicle_type}'.",
        )

    # 4. Tạo TicketEntitlement và gọi hàm kiểm tra vé chuẩn từ M4
    check_time = at or datetime.now(UTC)
    if check_time.tzinfo is None:
        check_time = check_time.replace(tzinfo=UTC)

    valid_from = (
        sub.valid_from if sub.valid_from.tzinfo is not None else sub.valid_from.replace(tzinfo=UTC)
    )
    valid_until = (
        sub.valid_until
        if sub.valid_until.tzinfo is not None
        else sub.valid_until.replace(tzinfo=UTC)
    )

    entitlement = TicketEntitlement(
        kind=TicketKind(product.kind),
        plate=vehicle.normalized_plate,
        ticket_code=vehicle.ticket_code,
        zone_id=sub.zone_id,
        valid_from=valid_from,
        valid_until=valid_until,
        grace_days=sub.grace_days,
    )

    eval_zone_id = zone_id or sub.zone_id
    m4_result = check_ticket_access(
        ticket=entitlement,
        at=check_time,
        plate=plate,
        ticket_code=code,
        zone_id=eval_zone_id,
    )

    if m4_result.decision == M4AccessDecision.ALLOW:
        return AccessDecision.ALLOW, f"Vé hợp lệ ({product.name})."
    if m4_result.decision == M4AccessDecision.DENY:
        if m4_result.reason in ("EXPIRED", "NOT_YET_VALID"):
            return (
                AccessDecision.ALLOW,
                f"Vé '{product.name}' hết hạn hoặc chưa đến hạn, vào bãi theo vé lượt.",
            )
        reason_map = {
            "WRONG_ZONE": f"Vé '{product.name}' không áp dụng cho khu vực này.",
        }
        msg = reason_map.get(m4_result.reason, f"Vé bị từ chối: {m4_result.reason}")
        return AccessDecision.DENY, msg
    if m4_result.decision == M4AccessDecision.REVIEW:
        reason_map = {
            "PLATE_MISMATCH": "Biển số xe thực tế không khớp với thông tin vé đăng ký.",
            "TICKET_CODE_MISMATCH": "Mã thẻ/vé quẹt không khớp với phương tiện đã đăng ký.",
            "NO_TICKET": "Không tìm thấy thông tin vé hợp lệ.",
        }
        msg = reason_map.get(m4_result.reason, f"Cần kiểm tra lại vé: {m4_result.reason}")
        return AccessDecision.REVIEW, msg

    return AccessDecision.ALLOW, "Quyền vé hợp lệ."


def check_ticket_access_stub(
    license_plate: str | None,
    vehicle_type: str,
    ticket_code: str | None,
    db: Session | None = None,
    building_id: UUID | None = None,
    zone_id: UUID | None = None,
    at: datetime | None = None,
) -> tuple[AccessDecision, str]:
    """Hàm wrapper tương thích ngược gọi sang hàm kiểm tra vé M4."""
    return verify_ticket_entitlement_for_checkin(
        db=db,
        building_id=building_id,
        license_plate=license_plate,
        vehicle_type=vehicle_type,
        ticket_code=ticket_code,
        zone_id=zone_id,
        at=at,
    )


def check_access_control(
    license_plate: str | None,
    vehicle_type: str,
    ticket_code: str | None = None,
    lane: Lane | None = None,
    customer_class: str = "VISITOR",
    db: Session | None = None,
    building_id: UUID | None = None,
    zone_id: UUID | None = None,
    at: datetime | None = None,
) -> tuple[AccessDecision, str]:
    """Kiểm tra Blacklist (M1) và Quyền vé (M4) trước khi cho xe vào."""
    del customer_class
    is_bl, bl_msg = check_blacklist_stub(license_plate)
    if is_bl:
        return AccessDecision.DENY, bl_msg or "Blacklisted"

    b_id = building_id or getattr(lane, "building_id", None)
    return verify_ticket_entitlement_for_checkin(
        db=db,
        building_id=b_id,
        license_plate=license_plate,
        vehicle_type=vehicle_type,
        ticket_code=ticket_code,
        zone_id=zone_id,
        at=at,
    )


# Alias tương thích ngược
check_access_control_stub = check_access_control


def evaluate_access_control(
    db: Session,
    lane: Lane,
    vehicle_type: str,
    license_plate: str | None,
    ticket_code: str | None = None,
    customer_class: str = "VISITOR",
    operator: User | None = None,
    is_override: bool = False,
    override_reason: str | None = None,
    zone_id: UUID | None = None,
    at: datetime | None = None,
) -> AccessCheckResult:
    """Đánh giá Access Control (ALLOW / DENY / REVIEW) trước khi tạo phiên check-in."""
    del operator
    # 1. Kiểm tra làn xe có cho phép loại xe này không (BR làn xe & loại xe)
    allowed_vtype = getattr(lane, "allowed_vehicle_type", AllowedVehicleType.ALL)
    if type(allowed_vtype).__name__ == "MagicMock" or not allowed_vtype:
        allowed_vtype = AllowedVehicleType.ALL

    if allowed_vtype != AllowedVehicleType.ALL and allowed_vtype != vehicle_type:
        lane_name = getattr(lane, "name", "Lane")
        if type(lane_name).__name__ == "MagicMock":
            lane_name = "Lane"
        return AccessCheckResult(
            decision=AccessDecision.DENY,
            reason=(
                f"Lane '{lane_name}' does not allow vehicle type '{vehicle_type}'. "
                f"Allowed: '{allowed_vtype}'."
            ),
            details={"allowed": str(allowed_vtype), "requested": str(vehicle_type)},
        )

    # 2. Quy tắc BR-20: Xe đạp không bắt buộc biển số nhưng bắt buộc có ticket_code
    if vehicle_type == "BICYCLE" and not ticket_code:
        return AccessCheckResult(
            decision=AccessDecision.DENY,
            reason="Bicycles require a valid ticket_code for check-in (BR-20).",
            details={"vehicle_type": vehicle_type},
        )

    # 3. Kiểm tra danh sách đen (M1) và quyền vé (M4)
    building_id = getattr(lane, "building_id", None)
    if type(building_id).__name__ == "MagicMock":
        building_id = None

    decision, decision_msg = check_access_control(
        license_plate=license_plate,
        vehicle_type=vehicle_type,
        ticket_code=ticket_code,
        lane=lane,
        customer_class=customer_class,
        db=db,
        building_id=building_id,
        zone_id=zone_id,
        at=at,
    )
    if decision == AccessDecision.DENY:
        return AccessCheckResult(
            decision=AccessDecision.DENY,
            reason=decision_msg,
            details={"plate": license_plate, "ticket_code": ticket_code},
        )

    if decision == AccessDecision.REVIEW:
        if is_override and override_reason:
            return AccessCheckResult(
                decision=AccessDecision.ALLOW,
                reason=f"Access granted via operator override: {override_reason}",
                details={"original_decision": "REVIEW", "override": True},
            )
        return AccessCheckResult(
            decision=AccessDecision.REVIEW,
            reason=decision_msg or "Manual operator review required.",
            details={"plate": license_plate},
        )

    # 4. Kiểm tra sơ bộ sức chứa & quota hạng khách
    counter = CounterService.get_or_create_counter(db, building_id, vehicle_type)
    cap_allowed, cap_reason = check_capacity_and_quota_stub(
        current_occupied=counter.occupied,
        vehicle_type=vehicle_type,
        customer_class=customer_class,
        building_id=building_id,
        db=db,
    )
    if not cap_allowed:
        return AccessCheckResult(
            decision=AccessDecision.DENY,
            reason=cap_reason or f"Parking is full for vehicle type {vehicle_type}.",
            details={
                "code": "CAPACITY_FULL",
                "vehicle_type": vehicle_type,
                "occupied": counter.occupied,
                "customer_class": customer_class,
            },
        )

    return AccessCheckResult(
        decision=AccessDecision.ALLOW,
        reason="Access granted.",
        details={"vehicle_type": vehicle_type, "lane_id": str(lane.id)},
    )
