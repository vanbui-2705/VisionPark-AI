from copy import deepcopy

from sqlalchemy import select

from app.modules.buildings.models import DEFAULT_BUILDING_ID, ParkingLot
from app.modules.lanes.models import Lane
from app.modules.lot_settings.review_policy import apply_plate_review_policy
from tests.alpr_double import FakeALPRRuntime


def test_building_threshold_controls_preview_and_persisted_result(
    client, db_session, operator_headers
):
    import cv2
    import numpy as np

    lane = db_session.scalar(select(Lane).where(Lane.direction == "IN"))
    lot = db_session.scalar(select(ParkingLot).where(ParkingLot.building_id == DEFAULT_BUILDING_ID))
    image = cv2.imencode(".png", np.zeros((40, 80, 3), dtype=np.uint8))[1].tobytes()
    client.app.state.alpr_runtime = FakeALPRRuntime("low-confidence")
    result = client.app.state.alpr_runtime.detect_and_read(image)
    assert apply_plate_review_policy(db_session, str(lane.id), result).requires_confirmation is True
    config = deepcopy(lot.settings)
    config["ai"] = {"plate_confidence": 0.4, "vehicle_confidence": None}
    lot.settings = config
    db_session.commit()
    assert (
        apply_plate_review_policy(db_session, str(lane.id), result).requires_confirmation is False
    )
    for mode in ("preview", "final"):
        response = client.post(
            "/api/v1/alpr/detections",
            data={"lane_id": str(lane.id), "mode": mode},
            files={"image": ("policy.png", image, "image/png")},
            headers=operator_headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["requires_confirmation"] is False
        if mode == "final":
            detail = client.get(
                f"/api/v1/alpr/detections/{response.json()['detection_id']}",
                headers=operator_headers,
            )
            assert detail.json()["requires_confirmation"] is False
    config = deepcopy(lot.settings)
    config["ai"]["plate_confidence"] = None
    lot.settings = dict(config)
    db_session.commit()
    assert apply_plate_review_policy(db_session, str(lane.id), result).requires_confirmation is True
