import csv
import io
import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.checkin.lifecycle_models import LifecycleEvent, LifecycleEventType
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
from app.modules.checkin.service import normalize_plate
from app.modules.lanes.models import Lane
from app.modules.users.models import User
from app.modules.users.schemas import RoleName

from .schemas import (
    LifecycleTimelineEvent,
    SessionDetailResponse,
    SessionLifecycleFilter,
    SessionListItemResponse,
    SessionListPaginatedResponse,
)


def _normalize_tz(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


# Các loại sự kiện tính là ngoại lệ trong vòng đời xe (BR-4.8)
EXCEPTION_EVENT_TYPES = {
    LifecycleEventType.OVERRIDE_APPLIED.value,
    LifecycleEventType.OPERATOR_CORRECTED.value,
    LifecycleEventType.MANUAL_SESSION_CREATED.value,
    LifecycleEventType.SESSION_REOPENED.value,
    LifecycleEventType.CANCELLED.value,
    LifecycleEventType.COUNTER_ADJUSTED.value,
    LifecycleEventType.PAYMENT_FAILED.value,
}

# Các sự kiện tài chính dành riêng cho vai trò Kế toán (ACCOUNTANT)
FINANCIAL_EVENT_TYPES = {
    LifecycleEventType.FEE_CALCULATED.value,
    LifecycleEventType.INVOICE_CREATED.value,
    LifecycleEventType.PAYMENT_RECEIVED.value,
    LifecycleEventType.PAYMENT_FAILED.value,
    LifecycleEventType.COMPLETED.value,
}


class LifecycleService:
    def __init__(self, session: Session):
        self.session = session

    def _build_query(
        self,
        filter_params: SessionLifecycleFilter,
        current_user: User,
        building_id: UUID | None = None,
    ):
        target_building = building_id or self.session.info.get("building_id")
        stmt = select(ParkingTransaction)

        if target_building is not None:
            stmt = stmt.where(ParkingTransaction.building_id == target_building)

        if filter_params.license_plate:
            p = filter_params.license_plate.strip()
            norm = normalize_plate(p)
            stmt = stmt.where(
                or_(
                    ParkingTransaction.normalized_plate.like(f"%{norm}%"),
                    ParkingTransaction.license_plate.ilike(f"%{p}%"),
                )
            )

        if filter_params.ticket_code:
            code = filter_params.ticket_code.strip()
            stmt = stmt.where(ParkingTransaction.ticket_code.ilike(f"%{code}%"))

        if filter_params.from_time:
            stmt = stmt.where(ParkingTransaction.check_in_time >= filter_params.from_time)

        if filter_params.to_time:
            stmt = stmt.where(ParkingTransaction.check_in_time <= filter_params.to_time)

        if filter_params.vehicle_type:
            stmt = stmt.where(
                ParkingTransaction.vehicle_type == filter_params.vehicle_type.strip().upper()
            )

        if filter_params.status:
            stmt = stmt.where(ParkingTransaction.status == filter_params.status.strip().upper())

        if filter_params.lane_id:
            stmt = stmt.where(
                or_(
                    ParkingTransaction.lane_id == filter_params.lane_id,
                    ParkingTransaction.exit_lane_id == filter_params.lane_id,
                )
            )

        if filter_params.ticket_kind:
            kind_upper = filter_params.ticket_kind.strip().upper()
            stmt = stmt.where(
                ParkingTransaction.price_snapshot["ticket_kind"].as_string() == kind_upper
            )

        # Biểu thức kiểm tra ngoại lệ
        exception_subq = (
            select(1)
            .where(
                LifecycleEvent.session_id == ParkingTransaction.id,
                LifecycleEvent.event_type.in_(EXCEPTION_EVENT_TYPES),
            )
            .exists()
        )
        has_exception_expr = or_(
            ParkingTransaction.is_manual_override.is_(True),
            ParkingTransaction.status == TransactionStatus.EXCEPTION.value,
            exception_subq,
        )

        if filter_params.has_exception is True:
            stmt = stmt.where(has_exception_expr)
        elif filter_params.has_exception is False:
            stmt = stmt.where(~has_exception_expr)

        return stmt

    def list_sessions(
        self,
        filter_params: SessionLifecycleFilter,
        current_user: User,
        building_id: UUID | None = None,
    ) -> SessionListPaginatedResponse:
        """Lấy danh sách các lượt gửi xe có phân trang và áp dụng bộ lọc (BR-4.8)."""
        base_query = self._build_query(filter_params, current_user, building_id)

        # Tính tổng số bản ghi
        count_query = select(func.count()).select_from(base_query.subquery())
        total = self.session.scalar(count_query) or 0

        # Phân trang
        offset = (filter_params.page - 1) * filter_params.page_size
        stmt = (
            base_query.order_by(ParkingTransaction.check_in_time.desc())
            .offset(offset)
            .limit(filter_params.page_size)
        )
        transactions = list(self.session.scalars(stmt))

        if not transactions:
            return SessionListPaginatedResponse(
                items=[],
                total=total,
                page=filter_params.page,
                page_size=filter_params.page_size,
                total_pages=max(1, (total + filter_params.page_size - 1) // filter_params.page_size)
                if total > 0
                else 1,
            )

        # Gom danh sách ID session có sự kiện ngoại lệ
        session_ids = [tx.id for tx in transactions]
        exception_session_ids = set(
            self.session.scalars(
                select(LifecycleEvent.session_id).where(
                    LifecycleEvent.session_id.in_(session_ids),
                    LifecycleEvent.event_type.in_(EXCEPTION_EVENT_TYPES),
                )
            )
        )

        # Gom tên làn
        lane_ids = {tx.lane_id for tx in transactions if tx.lane_id} | {
            tx.exit_lane_id for tx in transactions if tx.exit_lane_id
        }
        lane_map = {}
        if lane_ids:
            lanes = self.session.scalars(select(Lane).where(Lane.id.in_(lane_ids)))
            lane_map = {lane.id: lane.name for lane in lanes}

        items: list[SessionListItemResponse] = []
        now = datetime.now(UTC)
        for tx in transactions:
            t_in = _normalize_tz(tx.check_in_time)
            t_out = _normalize_tz(tx.exit_time) if tx.exit_time else now
            duration_mins = max(0, int((t_out - t_in).total_seconds() // 60))

            snap = getattr(tx, "price_snapshot", None) or {}
            ticket_kind = snap.get("ticket_kind", "HOURLY") if isinstance(snap, dict) else "HOURLY"

            has_exc = bool(
                tx.is_manual_override
                or tx.status == TransactionStatus.EXCEPTION.value
                or tx.id in exception_session_ids
            )

            in_name = (
                lane_map.get(tx.lane_id)
                or tx.lane_name_snapshot
                or tx.lane_snapshot_name
                or (tx.lane.name if getattr(tx, "lane", None) else None)
            )
            out_name = lane_map.get(tx.exit_lane_id) or (
                tx.exit_lane.name if getattr(tx, "exit_lane", None) else None
            )

            items.append(
                SessionListItemResponse(
                    id=tx.id,
                    building_id=tx.building_id,
                    license_plate=tx.license_plate,
                    normalized_plate=tx.normalized_plate,
                    ticket_code=tx.ticket_code,
                    vehicle_type=tx.vehicle_type,
                    ticket_kind=ticket_kind,
                    check_in_time=tx.check_in_time,
                    exit_time=tx.exit_time,
                    duration_minutes=duration_mins,
                    fee=float(tx.fee or 0.0),
                    status=tx.status,
                    has_exception=has_exc,
                    in_lane_name=in_name,
                    exit_lane_name=out_name,
                )
            )

        total_pages = (
            max(1, (total + filter_params.page_size - 1) // filter_params.page_size)
            if total > 0
            else 1
        )
        return SessionListPaginatedResponse(
            items=items,
            total=total,
            page=filter_params.page,
            page_size=filter_params.page_size,
            total_pages=total_pages,
        )

    def get_session_detail(
        self,
        session_id: UUID,
        current_user: User,
    ) -> SessionDetailResponse:
        """Lấy chi tiết 1 lượt gửi xe gồm dòng thời gian các sự kiện và ảnh vào/ra (BR-4.8)."""
        tx = self.session.get(ParkingTransaction, session_id)
        if tx is None:
            raise AppError(
                status_code=404,
                code="SESSION_NOT_FOUND",
                message="Phiên gửi xe không tồn tại.",
            )

        # Tenant isolation
        user_building = self.session.info.get("building_id")
        if (
            user_building is not None
            and current_user.role.name != RoleName.SYSTEM_ADMIN.value
            and tx.building_id != user_building
        ):
            raise AppError(
                status_code=403,
                code="BUILDING_ACCESS_DENIED",
                message="Không có quyền truy cập phiên gửi xe của tòa nhà khác.",
            )

        # Lấy toàn bộ sự kiện vòng đời
        events = list(
            self.session.scalars(
                select(LifecycleEvent)
                .where(LifecycleEvent.session_id == session_id)
                .order_by(LifecycleEvent.occurred_at.asc())
            )
        )

        # Thu thập tên diễn viên và làn
        actor_ids = {e.actor_id for e in events if e.actor_id}
        lane_ids = {e.lane_id for e in events if e.lane_id} | {tx.lane_id, tx.exit_lane_id}
        lane_ids.discard(None)

        actor_map = {}
        if actor_ids:
            actors = self.session.scalars(select(User).where(User.id.in_(actor_ids)))
            actor_map = {u.id: (u.display_name or u.username) for u in actors}

        lane_map = {}
        if lane_ids:
            lanes = self.session.scalars(select(Lane).where(Lane.id.in_(lane_ids)))
            lane_map = {lane.id: lane.name for lane in lanes}

        # Trích xuất ảnh vào / ra, người xử lý, lý do override
        check_in_image = tx.image_url
        exit_image = None
        override_reason = None
        op_rel = getattr(tx, "check_in_operator", None)
        check_in_op = (
            tx.operator_name_snapshot
            or tx.operator_snapshot_name
            or (op_rel.display_name if op_rel else None)
        )
        exit_op = None

        has_exc = bool(
            tx.is_manual_override
            or tx.status == TransactionStatus.EXCEPTION.value
            or any(e.event_type in EXCEPTION_EVENT_TYPES for e in events)
        )

        # Tìm exit_image và override_reason từ các events
        for e in events:
            details = e.details or {}
            if "override_reason" in details and details["override_reason"]:
                override_reason = details["override_reason"]

            if e.event_type in {
                LifecycleEventType.EXIT_CONFIRMED.value,
                LifecycleEventType.GATE_OUT_DETECTED.value,
            }:
                if e.image_ref:
                    exit_image = e.image_ref
                if "exit_image_url" in details and details["exit_image_url"]:
                    exit_image = details["exit_image_url"]

            if e.event_type in {
                LifecycleEventType.EXIT_CONFIRMED.value,
                LifecycleEventType.COMPLETED.value,
                LifecycleEventType.PAYMENT_RECEIVED.value,
            }:
                if e.actor_id and e.actor_id in actor_map:
                    exit_op = actor_map[e.actor_id]

        # Fallback ảnh ra từ notes nếu có tag [EXIT_IMAGE:url]
        if not exit_image and tx.notes:
            match = re.search(r"\[EXIT_IMAGE:(.*?)\]", tx.notes)
            if match:
                exit_image = match.group(1).strip()

        # Xây dựng timeline
        timeline: list[LifecycleTimelineEvent] = []
        is_accountant = current_user.role.name == RoleName.ACCOUNTANT.value

        for e in events:
            # Phân quyền: Kế toán (ACCOUNTANT) chỉ xem các sự kiện có tính chất tài chính
            if is_accountant and e.event_type not in FINANCIAL_EVENT_TYPES:
                continue

            actor_name = actor_map.get(e.actor_id) if e.actor_id else None
            lane_name = lane_map.get(e.lane_id) if e.lane_id else None

            # Đối với kế toán: ẩn đường dẫn ảnh nhạy cảm
            img_ref = None if is_accountant else e.image_ref

            timeline.append(
                LifecycleTimelineEvent(
                    id=e.id,
                    event_type=e.event_type,
                    occurred_at=e.occurred_at,
                    actor_type=e.actor_type,
                    actor_id=e.actor_id if not is_accountant else None,
                    actor_name=actor_name if not is_accountant else None,
                    lane_id=e.lane_id,
                    lane_name=lane_name,
                    details=e.details,
                    image_ref=img_ref,
                )
            )

        t_in = _normalize_tz(tx.check_in_time)
        t_out = _normalize_tz(tx.exit_time) if tx.exit_time else datetime.now(UTC)
        duration_mins = max(0, int((t_out - t_in).total_seconds() // 60))

        snap = getattr(tx, "price_snapshot", None) or {}
        ticket_kind = snap.get("ticket_kind", "HOURLY") if isinstance(snap, dict) else "HOURLY"

        in_lane_name = (
            lane_map.get(tx.lane_id)
            or tx.lane_name_snapshot
            or tx.lane_snapshot_name
            or (tx.lane.name if getattr(tx, "lane", None) else None)
        )
        exit_lane_name = lane_map.get(tx.exit_lane_id) or (
            tx.exit_lane.name if getattr(tx, "exit_lane", None) else None
        )

        return SessionDetailResponse(
            id=tx.id,
            building_id=tx.building_id,
            license_plate=tx.license_plate,
            normalized_plate=tx.normalized_plate,
            ticket_code=tx.ticket_code,
            vehicle_type=tx.vehicle_type,
            ticket_kind=ticket_kind,
            check_in_time=tx.check_in_time,
            exit_time=tx.exit_time,
            duration_minutes=duration_mins,
            fee=float(tx.fee or 0.0),
            status=tx.status,
            has_exception=has_exc,
            check_in_image_url=None if is_accountant else check_in_image,
            exit_image_url=None if is_accountant else exit_image,
            check_in_operator_name=None if is_accountant else check_in_op,
            exit_operator_name=None if is_accountant else exit_op,
            override_reason=None if is_accountant else override_reason,
            in_lane_name=in_lane_name,
            exit_lane_name=exit_lane_name,
            timeline=timeline,
        )

    def export_sessions_csv(
        self,
        filter_params: SessionLifecycleFilter,
        current_user: User,
        building_id: UUID | None = None,
    ) -> str:
        """Xuất danh sách lượt xe theo bộ lọc ra định dạng CSV (UTF-8 có BOM) (BR-4.8)."""
        base_query = self._build_query(filter_params, current_user, building_id)
        # Giới hạn tối đa 5000 bản ghi để chống tràn bộ nhớ
        stmt = base_query.order_by(ParkingTransaction.check_in_time.desc()).limit(5000)
        transactions = list(self.session.scalars(stmt))

        # Gom ngoại lệ
        session_ids = [tx.id for tx in transactions]
        exception_session_ids = set()
        if session_ids:
            exception_session_ids = set(
                self.session.scalars(
                    select(LifecycleEvent.session_id).where(
                        LifecycleEvent.session_id.in_(session_ids),
                        LifecycleEvent.event_type.in_(EXCEPTION_EVENT_TYPES),
                    )
                )
            )

        # Gom tên làn
        lane_ids = {tx.lane_id for tx in transactions if tx.lane_id} | {
            tx.exit_lane_id for tx in transactions if tx.exit_lane_id
        }
        lane_map = {}
        if lane_ids:
            lanes = self.session.scalars(select(Lane).where(Lane.id.in_(lane_ids)))
            lane_map = {lane.id: lane.name for lane in lanes}

        is_accountant = current_user.role.name == RoleName.ACCOUNTANT.value
        output = io.StringIO()
        # UTF-8 BOM để Excel hiển thị đúng dấu tiếng Việt
        output.write("\ufeff")
        writer = csv.writer(output)

        if is_accountant:
            headers = [
                "Mã phiên",
                "Biển số",
                "Mã vé",
                "Loại xe",
                "Loại vé",
                "Giờ vào",
                "Giờ ra",
                "Thời gian đỗ (phút)",
                "Phí (VNĐ)",
                "Trạng thái",
            ]
        else:
            headers = [
                "Mã phiên",
                "Biển số",
                "Mã vé",
                "Loại xe",
                "Loại vé",
                "Giờ vào",
                "Giờ ra",
                "Thời gian đỗ (phút)",
                "Phí (VNĐ)",
                "Trạng thái",
                "Có ngoại lệ",
                "Làn vào",
                "Làn ra",
                "Người vào",
                "Ghi chú",
            ]
        writer.writerow(headers)

        now = datetime.now(UTC)
        for tx in transactions:
            t_in = _normalize_tz(tx.check_in_time)
            t_out = _normalize_tz(tx.exit_time) if tx.exit_time else now
            duration_mins = max(0, int((t_out - t_in).total_seconds() // 60))
            snap = getattr(tx, "price_snapshot", None) or {}
            ticket_kind = snap.get("ticket_kind", "HOURLY") if isinstance(snap, dict) else "HOURLY"
            fee_str = f"{float(tx.fee or 0.0):,.0f}"

            if is_accountant:
                writer.writerow(
                    [
                        str(tx.id),
                        tx.license_plate or "",
                        tx.ticket_code or "",
                        tx.vehicle_type,
                        ticket_kind,
                        tx.check_in_time.isoformat() if tx.check_in_time else "",
                        tx.exit_time.isoformat() if tx.exit_time else "",
                        str(duration_mins),
                        fee_str,
                        tx.status,
                    ]
                )
            else:
                has_exc = bool(
                    tx.is_manual_override
                    or tx.status == TransactionStatus.EXCEPTION.value
                    or tx.id in exception_session_ids
                )
                in_lane = (
                    lane_map.get(tx.lane_id) or tx.lane_name_snapshot or tx.lane_snapshot_name or ""
                )
                out_lane = lane_map.get(tx.exit_lane_id) or ""
                op_name = tx.operator_name_snapshot or tx.operator_snapshot_name or ""

                writer.writerow(
                    [
                        str(tx.id),
                        tx.license_plate or "",
                        tx.ticket_code or "",
                        tx.vehicle_type,
                        ticket_kind,
                        tx.check_in_time.isoformat() if tx.check_in_time else "",
                        tx.exit_time.isoformat() if tx.exit_time else "",
                        str(duration_mins),
                        fee_str,
                        tx.status,
                        "CÓ" if has_exc else "KHÔNG",
                        in_lane,
                        out_lane,
                        op_name,
                        tx.notes or "",
                    ]
                )

        return output.getvalue()
