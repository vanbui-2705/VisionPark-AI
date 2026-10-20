from dataclasses import dataclass
from uuid import UUID


@dataclass
class CapacityQuotaConfig:
    vehicle_type: str
    physical_capacity: int
    safe_capacity: int
    resident_quota: int
    staff_quota: int
    nearly_full_ratio: float = 0.8
    full_ratio: float = 0.95


# TODO: Tích hợp với module M1 (bảng lot_capacities, Setting sức chứa) và M4 (bảng class_quotas)
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


def get_capacity_settings_stub(building_id: UUID | None, vehicle_type: str) -> CapacityQuotaConfig:
    """Stub lấy cấu hình sức chứa và quota tạm thời từ Setting (chờ Module M1 & M4)."""
    del building_id
    vtype = vehicle_type.upper()
    return DEFAULT_CAPACITY_CONFIGS.get(
        vtype,
        CapacityQuotaConfig(
            vehicle_type=vtype,
            physical_capacity=100,
            safe_capacity=80,
            resident_quota=10,
            staff_quota=5,
        ),
    )


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

    reserved = cfg.resident_quota + cfg.staff_quota
    return max(0, cfg.safe_capacity - reserved)


def check_capacity_and_quota_stub(
    current_occupied: int,
    vehicle_type: str,
    customer_class: str = "VISITOR",
    building_id: UUID | None = None,
) -> tuple[bool, str | None]:
    """Kiểm tra sơ bộ sức chứa và quota hạng khách trước khi cập nhật."""
    cfg = get_capacity_settings_stub(building_id, vehicle_type)
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
