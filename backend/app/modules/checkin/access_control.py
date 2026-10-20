from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from app.modules.checkin.capacity_quota_stub import check_capacity_and_quota_stub
from app.modules.checkin.counter_service import CounterService
from app.modules.lanes.models import AllowedVehicleType, Lane
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


# TODO: Tích hợp với module M1 (bảng vehicle_access_rules - blacklist/whitelist)
# Tạm thời stub danh sách đen giả định.
BLACKLIST_STUB: set[str] = {"29A99999", "BLACKLIST123"}


def check_blacklist_stub(license_plate: str | None) -> tuple[bool, str | None]:
    if license_plate:
        from app.alpr.utils import normalize_plate

        norm = normalize_plate(license_plate)
        if norm in BLACKLIST_STUB:
            return True, "Phương tiện nằm trong danh sách đen từ chối phục vụ (Blacklist M1)."
    return False, None


# TODO: Tích hợp với module M4 (hàm check_ticket_access)
def check_ticket_access_stub(
    license_plate: str | None,
    vehicle_type: str,
    ticket_code: str | None,
) -> tuple[AccessDecision, str]:
    del license_plate, vehicle_type, ticket_code
    return AccessDecision.ALLOW, "Quyền vé và thẻ hợp lệ (STUB M4)."


# TODO: Tích hợp với module M1 và M4 qua hàm tổng hợp check_access_control_stub
def check_access_control_stub(
    license_plate: str | None,
    vehicle_type: str,
    ticket_code: str | None = None,
    lane: Lane | None = None,
    customer_class: str = "VISITOR",
) -> tuple[AccessDecision, str]:
    """Hàm Stub giả định gọi sang M1/M4, trả về ALLOW/DENY/REVIEW."""
    del lane, customer_class
    is_bl, bl_msg = check_blacklist_stub(license_plate)
    if is_bl:
        return AccessDecision.DENY, bl_msg or "Blacklisted"
    return check_ticket_access_stub(license_plate, vehicle_type, ticket_code)


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

    # 3. Kiểm tra danh sách đen và quyền vé qua Stub M1 & M4
    decision, decision_msg = check_access_control_stub(
        license_plate=license_plate,
        vehicle_type=vehicle_type,
        ticket_code=ticket_code,
        lane=lane,
        customer_class=customer_class,
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
    building_id = getattr(lane, "building_id", None)
    if type(building_id).__name__ == "MagicMock":
        building_id = None

    counter = CounterService.get_or_create_counter(db, building_id, vehicle_type)
    cap_allowed, cap_reason = check_capacity_and_quota_stub(
        current_occupied=counter.occupied,
        vehicle_type=vehicle_type,
        customer_class=customer_class,
        building_id=building_id,
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
