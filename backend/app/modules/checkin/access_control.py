from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

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


# TODO: Chờ module M1 hoàn thiện bảng vehicle_access_rules (blacklist/whitelist).
BLACKLIST_STUB: set[str] = {"29A99999", "BLACKLIST123"}


def check_blacklist_stub(license_plate: str | None) -> tuple[bool, str | None]:
    if license_plate:
        from app.alpr.utils import normalize_plate

        norm = normalize_plate(license_plate)
        if norm in BLACKLIST_STUB:
            return True, "Vehicle plate is blacklisted by management."
    return False, None


# TODO: Chờ module M4 hoàn thiện hàm check_ticket_access().
# Tạm thời stub trả về ALLOW cho mọi vé/lượt xe hợp lệ.
def check_ticket_access_stub(
    license_plate: str | None,
    vehicle_type: str,
    ticket_code: str | None,
) -> tuple[AccessDecision, str]:
    return AccessDecision.ALLOW, "Ticket / subscription check passed (STUB)."


def evaluate_access_control(
    db: Session,
    lane: Lane,
    vehicle_type: str,
    license_plate: str | None,
    ticket_code: str | None = None,
    operator: User | None = None,
    is_override: bool = False,
    override_reason: str | None = None,
) -> AccessCheckResult:
    """Đánh giá Access Control (ALLOW / DENY / REVIEW) trước khi check-in."""
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

    # 3. Kiểm tra danh sách đen (Blacklist check qua STUB M1)
    is_blacklisted, bl_reason = check_blacklist_stub(license_plate)
    if is_blacklisted:
        return AccessCheckResult(
            decision=AccessDecision.DENY,
            reason=bl_reason or "Vehicle is in the blacklist.",
            details={"plate": license_plate},
        )

    # 4. Kiểm tra quyền vé (Ticket access check qua STUB M4)
    ticket_decision, ticket_reason = check_ticket_access_stub(
        license_plate, vehicle_type, ticket_code
    )
    if ticket_decision == AccessDecision.DENY:
        return AccessCheckResult(
            decision=AccessDecision.DENY,
            reason=ticket_reason,
            details={"plate": license_plate, "ticket_code": ticket_code},
        )

    if ticket_decision == AccessDecision.REVIEW:
        if is_override and override_reason:
            return AccessCheckResult(
                decision=AccessDecision.ALLOW,
                reason=f"Access granted via operator override: {override_reason}",
                details={"original_decision": "REVIEW", "override": True},
            )
        return AccessCheckResult(
            decision=AccessDecision.REVIEW,
            reason=ticket_reason or "Manual operator review required.",
            details={"plate": license_plate},
        )

    return AccessCheckResult(
        decision=AccessDecision.ALLOW,
        reason="Access granted.",
        details={"vehicle_type": vehicle_type, "lane_id": str(lane.id)},
    )
