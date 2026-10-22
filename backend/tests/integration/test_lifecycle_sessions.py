from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.buildings.models import DEFAULT_BUILDING_ID, UserBuilding
from app.modules.checkin.lifecycle_models import ActorType, LifecycleEventType
from app.modules.checkin.lifecycle_service import record_lifecycle_event
from app.modules.checkin.models import ParkingTransaction
from app.modules.lanes.models import Lane, LaneDirection
from app.modules.users.models import Role, User
from app.modules.users.schemas import RoleName
from tests.conftest import login


def get_lane_by_direction(db_session, direction: LaneDirection):
    return db_session.scalar(
        select(Lane).where(Lane.direction == direction, Lane.is_active.is_(True))
    )


def role_headers(client, db_session, role_name: RoleName) -> dict[str, str]:
    role = db_session.scalar(select(Role).where(Role.name == role_name.value))
    username = f"user_{role_name.value.lower()}_{uuid4().hex[:6]}"
    user = User(
        username=username,
        display_name=f"User {role_name.value}",
        password_hash=hash_password("role-test-password"),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(UserBuilding(user_id=user.id, building_id=DEFAULT_BUILDING_ID))
    db_session.commit()
    token = login(client, username, "role-test-password")["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_sessions_pagination_and_filters(client, db_session, operator_headers):
    """
    BR-4.8: Bảng lượt phân trang và lọc theo biển số, loại xe, trạng thái, làn.
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)

    # 1. Tạo 2 lượt check-in với loại xe khác nhau
    plate_car = "30E-123.45"
    plate_bike = "29D-678.90"

    client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate_car, "vehicle_type": "CAR"},
        headers={**operator_headers, "Idempotency-Key": f"chk-lc-1-{uuid4()}"},
    )
    client.post(
        "/api/v1/parking/check-in",
        json={
            "lane_id": str(in_lane.id),
            "license_plate": plate_bike,
            "vehicle_type": "MOTORBIKE",
        },
        headers={**operator_headers, "Idempotency-Key": f"chk-lc-2-{uuid4()}"},
    )

    # 2. Lấy danh sách không lọc: total >= 2, items có dữ liệu
    res_all = client.get("/api/v1/lifecycle/sessions", headers=operator_headers)
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["total"] >= 2
    assert len(data_all["items"]) >= 2

    # 3. Lọc theo biển số
    res_plate = client.get(
        f"/api/v1/lifecycle/sessions?license_plate={plate_car}",
        headers=operator_headers,
    )
    assert res_plate.status_code == 200
    data_plate = res_plate.json()
    assert data_plate["total"] == 1
    assert data_plate["items"][0]["license_plate"] == "30E12345"
    assert data_plate["items"][0]["vehicle_type"] == "CAR"

    # 4. Lọc theo loại xe
    res_type = client.get(
        "/api/v1/lifecycle/sessions?vehicle_type=MOTORBIKE",
        headers=operator_headers,
    )
    assert res_type.status_code == 200
    data_type = res_type.json()
    assert all(item["vehicle_type"] == "MOTORBIKE" for item in data_type["items"])

    # 5. Lọc theo trạng thái
    res_status = client.get(
        "/api/v1/lifecycle/sessions?status=PARKED",
        headers=operator_headers,
    )
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert all(item["status"] == "PARKED" for item in data_status["items"])

    # 6. Kiểm tra phân trang page=1, page_size=1
    res_p1 = client.get(
        "/api/v1/lifecycle/sessions?page=1&page_size=1",
        headers=operator_headers,
    )
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert len(data_p1["items"]) == 1
    assert data_p1["page"] == 1
    assert data_p1["page_size"] == 1
    assert data_p1["total_pages"] >= 2


def test_list_sessions_has_exception_filter(client, db_session, operator_headers):
    """
    BR-4.8: Bộ lọc cờ ngoại lệ (has_exception = true/false).
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)

    # 1. Phiên bình thường (không ngoại lệ)
    plate_normal = "29A-111.99"
    res1 = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate_normal},
        headers={**operator_headers, "Idempotency-Key": f"chk-normal-{uuid4()}"},
    )
    assert res1.status_code == 201
    tx1_id = UUID(res1.json()["transaction"]["id"])
    tx1 = db_session.get(ParkingTransaction, tx1_id)
    tx1.is_manual_override = False
    db_session.commit()

    # 2. Phiên có ngoại lệ (được ghi nhận sự kiện OVERRIDE_APPLIED)
    plate_exc = "29A-222.99"
    res2 = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate_exc},
        headers={**operator_headers, "Idempotency-Key": f"chk-exc-{uuid4()}"},
    )
    assert res2.status_code == 201
    tx2_id = UUID(res2.json()["transaction"]["id"])

    # Thêm sự kiện ngoại lệ OVERRIDE_APPLIED vào session 2
    record_lifecycle_event(
        session=db_session,
        session_id=tx2_id,
        event_type=LifecycleEventType.OVERRIDE_APPLIED,
        actor_type=ActorType.OPERATOR,
        building_id=DEFAULT_BUILDING_ID,
        details={"reason": "Xác nhận ngoại lệ test"},
    )
    db_session.commit()

    # 3. Lọc has_exception=true
    res_exc = client.get(
        "/api/v1/lifecycle/sessions?has_exception=true",
        headers=operator_headers,
    )
    assert res_exc.status_code == 200
    exc_items = res_exc.json()["items"]
    exc_plates = [it["license_plate"] for it in exc_items]
    assert "29A22299" in exc_plates
    assert "29A11199" not in exc_plates

    # 4. Lọc has_exception=false
    res_no_exc = client.get(
        f"/api/v1/lifecycle/sessions?has_exception=false&license_plate={plate_normal}",
        headers=operator_headers,
    )
    assert res_no_exc.status_code == 200
    no_exc_items = res_no_exc.json()["items"]
    assert len(no_exc_items) == 1
    assert no_exc_items[0]["has_exception"] is False


def test_session_detail_timeline_and_images(client, db_session, operator_headers):
    """
    BR-4.8: Chi tiết một lượt gửi xe gồm mảng timeline sự kiện, ảnh vào và ảnh ra,
    người xử lý, lý do override.
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "51H-888.88"

    # 1. Check-in (có ảnh vào)
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-dt-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = checkin_res.json()["transaction"]["id"]

    # 2. Check-out với ảnh ra và override
    exit_img = "https://storage.visionpark.vn/test_exit_img.jpg"
    override_reason = "Khách là VIP tòa nhà, mở barrier thủ công"
    checkout_res = client.post(
        "/api/v1/parking/check-out",
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
            "exit_image_url": exit_img,
            "override_reason": override_reason,
            "payment_method": "CASH",
        },
        headers={**operator_headers, "Idempotency-Key": f"chk-out-dt-{uuid4()}"},
    )
    assert checkout_res.status_code == 200

    # 3. GET /api/v1/lifecycle/sessions/{id}
    detail_res = client.get(
        f"/api/v1/lifecycle/sessions/{tx_id}",
        headers=operator_headers,
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()

    assert detail["id"] == tx_id
    assert detail["status"] == "COMPLETED"
    assert detail["exit_image_url"] == exit_img
    assert detail["override_reason"] == override_reason
    assert detail["has_exception"] is True

    # Kiểm tra timeline
    timeline = detail["timeline"]
    assert len(timeline) >= 3
    event_types = [e["event_type"] for e in timeline]
    assert LifecycleEventType.CHECKED_IN.value in event_types
    assert LifecycleEventType.EXIT_CONFIRMED.value in event_types
    assert LifecycleEventType.COMPLETED.value in event_types

    # Sự kiện được sắp xếp theo thời gian tăng dần
    occurred_times = [e["occurred_at"] for e in timeline]
    assert occurred_times == sorted(occurred_times)


def test_session_detail_not_found(client, operator_headers):
    """Truy vấn phiên không tồn tại -> 404 SESSION_NOT_FOUND."""
    random_id = uuid4()
    res = client.get(
        f"/api/v1/lifecycle/sessions/{random_id}",
        headers=operator_headers,
    )
    assert res.status_code == 404
    assert res.json()["code"] == "SESSION_NOT_FOUND"


def test_export_sessions_csv(client, db_session, operator_headers):
    """
    BR-4.8: Xuất dữ liệu CSV theo bộ lọc, có UTF-8 BOM, trả về attachment filename.
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    plate = "99A-777.66"

    client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-csv-{uuid4()}"},
    )

    # Gọi API xuất CSV
    res = client.get(
        f"/api/v1/lifecycle/sessions/export-csv?license_plate={plate}",
        headers=operator_headers,
    )
    assert res.status_code == 200
    assert "text/csv" in res.headers["Content-Type"]
    assert "attachment; filename=" in res.headers["Content-Disposition"]

    content = res.content.decode("utf-8-sig")
    lines = content.strip().splitlines()
    assert len(lines) >= 2

    # Dòng tiêu đề
    headers = lines[0].split(",")
    assert "Mã phiên" in headers
    assert "Biển số" in headers
    assert "Thời gian đỗ (phút)" in headers

    # Dòng dữ liệu
    assert "99A77766" in lines[1]


def test_role_based_access_accountant(client, db_session, operator_headers):
    """
    BR-4.8: Phân quyền vai trò ACCOUNTANT chỉ xem phần tài chính (ẩn ảnh và timeline nhạy cảm).
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    out_lane = get_lane_by_direction(db_session, LaneDirection.OUT)
    plate = "65A-333.22"

    # 1. Thực hiện check-in và check-out tạo phiên hoàn tất
    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={
            "lane_id": str(in_lane.id),
            "license_plate": plate,
            "image_url": "https://storage.visionpark.vn/secret_in.jpg",
        },
        headers={**operator_headers, "Idempotency-Key": f"chk-in-acc-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = checkin_res.json()["transaction"]["id"]

    client.post(
        "/api/v1/parking/check-out",
        json={
            "license_plate": plate,
            "exit_lane_id": str(out_lane.id),
            "exit_image_url": "https://storage.visionpark.vn/secret_out.jpg",
            "override_reason": "Bảo vệ xử lý sự cố bí mật",
            "payment_method": "CASH",
        },
        headers={**operator_headers, "Idempotency-Key": f"chk-out-acc-{uuid4()}"},
    )

    # 2. Đăng nhập với vai trò ACCOUNTANT
    accountant_headers = role_headers(client, db_session, RoleName.ACCOUNTANT)

    # 3. Kế toán gọi GET /api/v1/lifecycle/sessions
    res_list = client.get(
        f"/api/v1/lifecycle/sessions?license_plate={plate}",
        headers=accountant_headers,
    )
    assert res_list.status_code == 200
    assert len(res_list.json()["items"]) == 1

    # 4. Kế toán gọi GET /api/v1/lifecycle/sessions/{id}
    res_detail = client.get(
        f"/api/v1/lifecycle/sessions/{tx_id}",
        headers=accountant_headers,
    )
    assert res_detail.status_code == 200
    detail = res_detail.json()

    # Ảnh camera và lý do override bí mật bị ẩn đối với Kế toán
    assert detail["check_in_image_url"] is None
    assert detail["exit_image_url"] is None
    assert detail["override_reason"] is None
    assert detail["check_in_operator_name"] is None

    # Timeline của Kế toán chỉ có các sự kiện mang tính tài chính (hoặc rỗng nếu không có)
    # Các sự kiện vận hành thuần túy như CHECKED_IN, BARRIER_OPENED_IN bị loại bỏ
    timeline_event_types = [e["event_type"] for e in detail["timeline"]]
    assert LifecycleEventType.CHECKED_IN.value not in timeline_event_types
    assert LifecycleEventType.BARRIER_OPENED_IN.value not in timeline_event_types

    # 5. Kế toán gọi xuất CSV -> Các cột điều tra nội bộ bị loại bỏ
    res_csv = client.get(
        f"/api/v1/lifecycle/sessions/export-csv?license_plate={plate}",
        headers=accountant_headers,
    )
    assert res_csv.status_code == 200
    csv_text = res_csv.content.decode("utf-8-sig")
    csv_headers = csv_text.splitlines()[0].split(",")
    assert "Người vào" not in csv_headers
    assert "Ghi chú" not in csv_headers
    assert "Phí (VNĐ)" in csv_headers


def test_role_based_access_building_admin(client, db_session, operator_headers):
    """
    BR-4.8: Phân quyền vai trò BUILDING_ADMIN có đầy đủ quyền xem danh sách và chi tiết vòng đời xe.
    """
    in_lane = get_lane_by_direction(db_session, LaneDirection.IN)
    plate = "30A-999.88"

    checkin_res = client.post(
        "/api/v1/parking/check-in",
        json={"lane_id": str(in_lane.id), "license_plate": plate},
        headers={**operator_headers, "Idempotency-Key": f"chk-in-ba-{uuid4()}"},
    )
    assert checkin_res.status_code == 201
    tx_id = checkin_res.json()["transaction"]["id"]

    admin_headers = role_headers(client, db_session, RoleName.BUILDING_ADMIN)

    # BUILDING_ADMIN gọi GET /api/v1/lifecycle/sessions
    res_list = client.get(
        f"/api/v1/lifecycle/sessions?license_plate={plate}",
        headers=admin_headers,
    )
    assert res_list.status_code == 200
    assert len(res_list.json()["items"]) == 1

    # BUILDING_ADMIN gọi GET /api/v1/lifecycle/sessions/{id}
    res_detail = client.get(
        f"/api/v1/lifecycle/sessions/{tx_id}",
        headers=admin_headers,
    )
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["id"] == tx_id
    assert len(detail["timeline"]) >= 1
