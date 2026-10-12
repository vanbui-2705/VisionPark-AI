"""M4 pricing and payment flow through the public API."""

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import SecretStr

from app.core.config import Settings, get_settings
from app.modules.checkin.models import ParkingTransaction, TransactionStatus
from tests.conftest import login


def test_building_price_snapshot_invoice_payment_and_callback(
    client, admin_token, settings: Settings, db_session
):
    settings.mock_vietqr_callback_secret = SecretStr("test-callback-secret-123")
    client.app.dependency_overrides[get_settings] = lambda: settings
    admin = {"Authorization": f"Bearer {admin_token}"}
    created = client.post(
        "/api/v1/buildings", json={"code": "B1", "name": "Building 1"}, headers=admin
    )
    assert created.status_code == 201, created.text
    building_id = created.json()["id"]
    user = client.post(
        "/api/v1/users",
        headers=admin,
        json={
            "username": "buildingadmin",
            "display_name": "Building Admin",
            "password": "test-password-123",
            "role": "BUILDING_ADMIN",
            "building_id": building_id,
        },
    )
    assert user.status_code == 201, user.text
    token = login(client, "buildingadmin", "test-password-123")["access_token"]
    building = {"Authorization": f"Bearer {token}"}
    changed = client.post(
        "/api/v1/auth/change-password",
        headers=building,
        json={"current_password": "test-password-123", "new_password": "new-building-password"},
    )
    assert changed.status_code == 200, changed.text
    token = login(client, "buildingadmin", "new-building-password")["access_token"]
    building = {"Authorization": f"Bearer {token}"}
    customer_class = client.post(
        "/api/v1/pricing/customer-classes",
        headers=building,
        json={"code": "VISITOR", "name": "Visitor", "discount_percent": 0},
    )
    assert customer_class.status_code == 201, customer_class.text
    class_id = customer_class.json()["id"]
    product = client.post(
        "/api/v1/pricing/ticket-products",
        headers=building,
        json={
            "code": "MONTH_CAR",
            "name": "Monthly car",
            "kind": "MONTHLY",
            "vehicle_type": "CAR",
            "customer_class_id": class_id,
        },
    )
    assert product.status_code == 201, product.text
    quota = client.put(
        "/api/v1/tickets/quotas",
        headers=building,
        json={"customer_class_id": class_id, "vehicle_type": "CAR", "max_active": 1},
    )
    assert quota.status_code == 200, quota.text
    vehicle = client.post(
        "/api/v1/tickets/vehicles",
        headers=building,
        json={"normalized_plate": "29A12345", "vehicle_type": "CAR", "customer_class_id": class_id},
    )
    assert vehicle.status_code == 201, vehicle.text
    zone_id = str(uuid4())
    subscription = client.post(
        "/api/v1/tickets/subscriptions",
        headers=building,
        json={
            "product_id": product.json()["id"],
            "vehicle_id": vehicle.json()["id"],
            "zone_id": zone_id,
            "valid_from": datetime.now(UTC).isoformat(),
            "valid_until": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        },
    )
    assert subscription.status_code == 201, subscription.text
    bike_product = client.post(
        "/api/v1/pricing/ticket-products",
        headers=building,
        json={
            "code": "MONTH_BIKE",
            "name": "Monthly bicycle",
            "kind": "MONTHLY",
            "vehicle_type": "BICYCLE",
            "customer_class_id": class_id,
        },
    )
    assert bike_product.status_code == 201, bike_product.text
    bicycle = client.post(
        "/api/v1/tickets/vehicles",
        headers=building,
        json={"ticket_code": "BIKE-1", "vehicle_type": "BICYCLE", "customer_class_id": class_id},
    )
    assert bicycle.status_code == 201, bicycle.text
    bike_subscription = client.post(
        "/api/v1/tickets/subscriptions",
        headers=building,
        json={
            "product_id": bike_product.json()["id"],
            "vehicle_id": bicycle.json()["id"],
            "zone_id": zone_id,
            "valid_from": datetime.now(UTC).isoformat(),
            "valid_until": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        },
    )
    assert bike_subscription.status_code == 201, bike_subscription.text
    access = client.post(
        "/api/v1/tickets/access",
        headers=building,
        json={
            "at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "plate": "29A12345",
            "zone_id": zone_id,
        },
    )
    assert access.status_code == 200 and access.json()["decision"] == "ALLOW", access.text
    invite = client.post(
        "/api/v1/tickets/guest-invites",
        headers=building,
        json={
            "code": "GUEST-1",
            "valid_from": datetime.now(UTC).isoformat(),
            "valid_until": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "free_minutes": 30,
        },
    )
    assert invite.status_code == 201, invite.text
    version = client.post(
        "/api/v1/pricing/versions",
        headers=building,
        json={
            "active_from": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
            "rules": [
                {
                    "vehicle_type": "CAR",
                    "ticket_kind": "HOURLY",
                    "customer_class_id": class_id,
                    "initial_fee": 5000,
                    "block_fee": 2000,
                },
                {
                    "vehicle_type": "CAR",
                    "ticket_kind": "MONTHLY",
                    "customer_class_id": class_id,
                    "initial_fee": 5000,
                    "block_fee": 2000,
                    "month_pass_fee": 100000,
                },
                {
                    "vehicle_type": "BICYCLE",
                    "ticket_kind": "MONTHLY",
                    "customer_class_id": class_id,
                    "initial_fee": 2000,
                    "block_fee": 1000,
                    "month_pass_fee": 30000,
                },
            ],
        },
    )
    assert version.status_code == 201, version.text
    lot = client.get("/api/v1/settings/lot", headers=building)
    assert lot.status_code == 200, lot.text
    lot_settings = lot.json()["settings"]
    for vehicle_type in ("CAR", "BICYCLE"):
        lot_settings["capacities"][vehicle_type]["physical_capacity"] = 10
        lot_settings["capacities"][vehicle_type]["safe_capacity"] = 10
    configured = client.put(
        "/api/v1/settings/lot",
        headers=building,
        json={"revision": lot.json()["revision"], "settings": lot_settings},
    )
    assert configured.status_code == 200, configured.text
    lane = client.post(
        "/api/v1/lanes",
        headers=building,
        json={
            "name": "B1_IN",
            "direction": "IN",
            "video_source": "test",
        },
    )
    assert lane.status_code == 200, lane.text
    exit_lane = client.post(
        "/api/v1/lanes",
        headers=building,
        json={"name": "B1_OUT", "direction": "OUT", "video_source": "test"},
    )
    assert exit_lane.status_code == 200, exit_lane.text
    bike_checkin = client.post(
        "/api/v1/parking/check-in",
        headers={**building, "Idempotency-Key": uuid4().hex},
        json={
            "lane_id": lane.json()["id"],
            "ticket_code": "BIKE-1",
            "vehicle_type": "BICYCLE",
            "ticket_kind": "MONTHLY",
            "customer_class_id": class_id,
            "zone_id": zone_id,
        },
    )
    assert bike_checkin.status_code == 201, bike_checkin.text
    bike_record = db_session.get(ParkingTransaction, UUID(bike_checkin.json()["transaction"]["id"]))
    assert bike_record.price_snapshot["entitlement_valid_until"] is not None
    checkin = client.post(
        "/api/v1/parking/check-in",
        headers={**building, "Idempotency-Key": uuid4().hex},
        json={
            "lane_id": lane.json()["id"],
            "license_plate": "29A12345",
            "vehicle_type": "CAR",
            "ticket_kind": "HOURLY",
            "customer_class_id": class_id,
        },
    )
    assert checkin.status_code == 201, checkin.text
    transaction = checkin.json()["transaction"]
    invoice = client.post(
        "/api/v1/invoices",
        headers=building,
        json={
            "transaction_id": transaction["id"],
            "check_out": (datetime.now(UTC) + timedelta(minutes=90)).isoformat(),
            "guest_invite_code": "GUEST-1",
        },
    )
    assert invoice.status_code == 201, invoice.text
    assert invoice.json()["price_version_id"] == version.json()["id"]
    assert invoice.json()["total_vnd"] >= 5000
    payment = client.post(
        "/api/v1/payments",
        headers={**building, "Idempotency-Key": "payment-1"},
        json={"invoice_id": invoice.json()["id"], "method": "VIETQR_MOCK"},
    )
    assert payment.status_code == 201, payment.text
    replay = client.post(
        "/api/v1/payments",
        headers={**building, "Idempotency-Key": "payment-1"},
        json={"invoice_id": invoice.json()["id"], "method": "VIETQR_MOCK"},
    )
    assert replay.status_code == 201 and replay.json()["id"] == payment.json()["id"]
    raw = (
        f'{{"provider_ref":"{payment.json()["provider_ref"]}","amount_vnd":{payment.json()["amount_vnd"]},"status":"PAID"}}'
    ).encode()
    secret = settings.mock_vietqr_callback_secret.get_secret_value()
    signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    callback = client.post(
        "/api/v1/payments/callback",
        content=raw,
        headers={"X-Mock-Signature": signature, "Content-Type": "application/json"},
    )
    assert callback.status_code == 200, callback.text
    assert callback.json()["status"] == "PAID"
    assert (
        client.post(
            "/api/v1/payments/callback",
            content=raw,
            headers={"X-Mock-Signature": signature, "Content-Type": "application/json"},
        ).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/invoices/{invoice.json()['id']}", headers=building).json()["status"]
        == "PAID"
    )
    first_transaction = db_session.get(ParkingTransaction, UUID(transaction["id"]))
    first_transaction.status = TransactionStatus.COMPLETED
    db_session.commit()
    pass_checkin = client.post(
        "/api/v1/parking/check-in",
        headers={**building, "Idempotency-Key": uuid4().hex},
        json={
            "lane_id": lane.json()["id"],
            "license_plate": "29A12345",
            "vehicle_type": "CAR",
            "ticket_kind": "MONTHLY",
            "customer_class_id": class_id,
            "zone_id": zone_id,
        },
    )
    assert pass_checkin.status_code == 201, pass_checkin.text
    pass_transaction = db_session.get(
        ParkingTransaction, UUID(pass_checkin.json()["transaction"]["id"])
    )
    assert pass_transaction.price_snapshot["entitlement_valid_until"] is not None
    pass_invoice = client.post(
        "/api/v1/invoices",
        headers=building,
        json={
            "transaction_id": str(pass_transaction.id),
            "check_out": (datetime.now(UTC) + timedelta(days=31)).isoformat(),
        },
    )
    assert pass_invoice.status_code == 201, pass_invoice.text
    assert any(line["code"] == "PASS_OVERAGE" for line in pass_invoice.json()["lines"])
    assert all(line["code"] != "MONTH_PASS" for line in pass_invoice.json()["lines"])
    pass_payment = client.post(
        "/api/v1/payments",
        headers={**building, "Idempotency-Key": "payment-2"},
        json={"invoice_id": pass_invoice.json()["id"], "method": "VIETQR_MOCK"},
    )
    assert pass_payment.status_code == 201, pass_payment.text
    bad_raw = json.dumps(
        {
            "provider_ref": pass_payment.json()["provider_ref"],
            "amount_vnd": pass_payment.json()["amount_vnd"] + 1,
            "status": "PAID",
        }
    ).encode()
    assert (
        client.post(
            "/api/v1/payments/callback",
            content=bad_raw,
            headers={"X-Mock-Signature": "invalid", "Content-Type": "application/json"},
        ).status_code
        == 401
    )
    bad_signature = hmac.new(secret.encode(), bad_raw, hashlib.sha256).hexdigest()
    mismatch = client.post(
        "/api/v1/payments/callback",
        content=bad_raw,
        headers={"X-Mock-Signature": bad_signature, "Content-Type": "application/json"},
    )
    assert mismatch.status_code == 200 and mismatch.json()["status"] == "FAILED"
    reconciliation = client.get("/api/v1/payments/reconcile", headers=building)
    assert reconciliation.status_code == 200
    assert any(row["payment_id"] == pass_payment.json()["id"] for row in reconciliation.json())
    second = client.post(
        "/api/v1/buildings", json={"code": "B2", "name": "Building 2"}, headers=admin
    )
    assert second.status_code == 201, second.text
    second_user = client.post(
        "/api/v1/users",
        headers=admin,
        json={
            "username": "otherbuildingadmin",
            "display_name": "Other building",
            "password": "test-password-123",
            "role": "BUILDING_ADMIN",
            "building_id": second.json()["id"],
        },
    )
    assert second_user.status_code == 201, second_user.text
    other_token = login(client, "otherbuildingadmin", "test-password-123")["access_token"]
    other = {"Authorization": f"Bearer {other_token}"}
    changed = client.post(
        "/api/v1/auth/change-password",
        headers=other,
        json={"current_password": "test-password-123", "new_password": "new-other-password"},
    )
    assert changed.status_code == 200, changed.text
    other_token = login(client, "otherbuildingadmin", "new-other-password")["access_token"]
    other = {"Authorization": f"Bearer {other_token}"}
    assert client.get("/api/v1/pricing/customer-classes", headers=other).json() == []
    assert client.get(f"/api/v1/invoices/{invoice.json()['id']}", headers=other).status_code == 404
