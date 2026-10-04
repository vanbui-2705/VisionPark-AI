# Phase 2 smoke fixtures

The clean-install smoke flow uses deterministic, non-sensitive local fixtures:

- lane: `LANE_IN_01` with direction `IN` and `video_source=fixture://phase-2/in.mp4`
- operator: `operator` with the password supplied by `SEED_OPERATOR_PASSWORD`
- input: a local MP4 selected in the Station UI; a JPEG frame is captured from it
- provider: `mock` with scenario `success` for CI and clean checkout validation

The seeded lane and operator are created idempotently by
`backend/app/database/seed.py`. Model weights are not part of the fixture set and
must be provisioned outside Git using `backend/models/alpr-manifest.json`.

For a no-plate or low-confidence smoke run, set `ALPR_MOCK_SCENARIO` to
`no-plate` or `low-confidence` and restart the backend. Preview requests use
`mode=preview` and `persist=false`, so they do not create media, detections, or
parking transactions. A confirmed result is submitted separately through the
check-in API.
