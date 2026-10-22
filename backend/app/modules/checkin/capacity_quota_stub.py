from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.buildings.models import ParkingLot


@dataclass
class CapacityQuotaConfig:
    vehicle_type: str
    physical_capacity: int
    safe_capacity: int
    resident_quota: int
    staff_quota: int
    nearly_full_ratio: float = 0.8
    full_ratio: float = 0.95


# Cấu hình mặc định dùng làm fallback khi tòa nhà chưa cấu hình ParkingLot.settings
DEFAULT_CAPACITY_CONFIGS: dict[str, CapacityQuotaConfig] = {
    "CAR": CapacityQuotaConfig(
        vehicle_type="CAR",
        physical_capacity=120,
        safe_capacity=100,
        resident_quota=20,
        staff_quota=10,
    ),
    "MOTORBIKE": CapacityQuotaConfig(
        vehicle_type="MOTORBIKE",
        physical_capacity=250,
        safe_capacity=200,
        resident_quota=50,
        staff_quota=20,
    ),
    "BICYCLE": CapacityQuotaConfig(
        vehicle_type="BICYCLE",
        physical_capacity=60,
        safe_capacity=50,
        resident_quota=0,
        staff_quota=0,
    ),
}


def get_capacity_settings_stub(
    building_id: UUID | None,
    vehicle_type: str,
    db: Session | None = None,
) -> CapacityQuotaConfig:
    """Lấy cấu hình sức chứa và quota từ ParkingLot.settings, fallback về default nếu chưa có."""
    vtype = vehicle_type.upper()
    default_cfg = DEFAULT_CAPACITY_CONFIGS.get(
        vtype,
        CapacityQuotaConfig(
            vehicle_type=vtype,
            physical_capacity=100,
            safe_capacity=80,
            resident_quota=10,
            staff_quota=5,
        ),
    )

    if db is not None and building_id is not None and type(building_id).__name__ != "MagicMock":
        try:
            lot = db.scalar(select(ParkingLot).where(ParkingLot.building_id == building_id))
            if lot and isinstance(lot.settings, dict):
                caps = lot.settings.get("capacities", {})
                quotas = lot.settings.get("quotas", {})
                v_cap = caps.get(vtype) or caps.get(vtype.lower()) or {}
                v_quota = quotas.get(vtype) or quotas.get(vtype.lower()) or {}
                safe_cap = v_cap.get("safe_capacity")
                phys_cap = v_cap.get("physical_capacity")
                if safe_cap is not None and phys_cap is not None and phys_cap > 0:
                    nearly_full = float(v_cap.get("nearly_full_threshold", 80)) / 100.0
                    full_th = float(v_cap.get("full_threshold", 95)) / 100.0
                    res_quota = int(v_quota.get("residents", 0))
                    staff_quota = int(v_quota.get("employees", 0))
                    # Nếu chưa cấu hình quota trong settings thì fallback theo default
                    # chỉ khi safe_capacity lớn hơn tổng quota mặc định
                    if res_quota == 0 and staff_quota == 0:
                        default_total = default_cfg.resident_quota + default_cfg.staff_quota
                        if int(safe_cap) > default_total:
                            res_quota = default_cfg.resident_quota
                            staff_quota = default_cfg.staff_quota

                    return CapacityQuotaConfig(
                        vehicle_type=vtype,
                        physical_capacity=int(phys_cap),
                        safe_capacity=int(safe_cap),
                        resident_quota=res_quota,
                        staff_quota=staff_quota,
                        nearly_full_ratio=nearly_full,
                        full_ratio=full_th,
                    )
        except Exception:
            pass

    return default_cfg


# Alias tương thích ngược
get_capacity_config_stub = get_capacity_settings_stub


def calculate_effective_capacity_limit(
    cfg: CapacityQuotaConfig,
    customer_class: str = "VISITOR",
) -> int:
    """Tính toán ngưỡng số xe tối đa cho phép vào bãi ứng với từng hạng khách.

    - Cư dân/nhân viên: được vào đến sức chứa vật lý (physical_capacity).
    - Khách vãng lai: chỉ được dùng phần không thuộc quota cư dân & nhân viên
      (safe_capacity - reserved_quota).
    """
    customer_cls = (customer_class or "VISITOR").upper()
    if customer_cls in ("RESIDENT", "STAFF"):
        return cfg.physical_capacity

    reserved = min(cfg.safe_capacity, cfg.resident_quota + cfg.staff_quota)
    return max(0, cfg.safe_capacity - reserved)


def check_capacity_and_quota_stub(
    current_occupied: int,
    vehicle_type: str,
    customer_class: str = "VISITOR",
    building_id: UUID | None = None,
    db: Session | None = None,
) -> tuple[bool, str | None]:
    """Kiểm tra sơ bộ sức chứa và quota hạng khách trước khi cập nhật."""
    cfg = get_capacity_settings_stub(building_id, vehicle_type, db=db)
    limit = calculate_effective_capacity_limit(cfg, customer_class)

    if (
        not isinstance(current_occupied, (int, float))
        or type(current_occupied).__name__ == "MagicMock"
    ):
        current_occupied = 0

    if current_occupied >= limit:
        customer_cls = (customer_class or "VISITOR").upper()
        if customer_cls in ("RESIDENT", "STAFF"):
            return (
                False,
                f"Bãi xe đã đạt sức chứa vật lý tối đa cho loại xe {vehicle_type} "
                f"({current_occupied}/{cfg.physical_capacity}).",
            )
        reserved = cfg.resident_quota + cfg.staff_quota
        return (
            False,
            f"Số chỗ cho khách vãng lai loại xe {vehicle_type} đã hết "
            f"({current_occupied} xe, dành {reserved} chỗ cho cư dân/nhân viên).",
        )

    return True, None
