# Phase 2 runbook

## Mock CI/local gate

From `backend`:

```powershell
py -3 scripts/release_gate.py
```

This validates all deterministic mock scenarios, confirms real-provider
not-ready behavior when the manifest is missing, runs the benchmark, pytest and
Ruff. It does not download weights or require a GPU. Reports are written under
`backend/var/benchmarks/`, which is ignored by Git.

The frontend gate is run from `frontend`:

```powershell
npm run test -- --run
npm run lint
npm run build
```

## Real provider demo

Provision the `.pt` asset outside Git at the path declared by
`backend/models/alpr-manifest.json`, verify its SHA-256, install
`.[dev,real,ocr]`, and set:

```powershell
$env:ALPR_PROVIDER = "real"
$env:ALPR_OCR_ENABLED = "true"
py -3 scripts/benchmark_alpr.py --provider real --dataset var/datasets/labelled-plates.json --split smoke
```

Readiness must be `ready` only after both detector and OCR load. If the model,
manifest, dependency or OCR cache is unavailable, rollback is:

```powershell
$env:ALPR_PROVIDER = "mock"
$env:ALPR_OCR_ENABLED = "false"
```

## Failure and duplicate checks

Run the existing integration suite for restart/migration, provider timeout,
duplicate `PARKED` rejection, idempotency retry, audit and authorization:

```powershell
cd backend
py -3 -m pytest tests/integration -q
```

The Station flow sends preview frames with `persist=false`. The chosen candidate is persisted with `capture_id` in a final capture; then
`POST /api/v1/alpr/detections/{id}/confirm` with `confirmed_plate`, `check_in=true`
and `Idempotency-Key` atomically confirms the detection and creates `PARKED`.
Manual entry calls `/api/v1/parking/check-in` without invoking ALPR.
Capture screenshots or screen recordings for success, low confidence, no plate,
manual correction, duplicate and retry in the local evidence folder; never
commit private vehicle footage or model weights.


## Local Compose and browser verification

Set root `.env` with a unique JWT secret and seed credentials, then run
`docker compose up --build -d`. Compose migrates the existing database before backend
startup. To install real detector/OCR in Docker set `INSTALL_REAL_ALPR=true` and
`INSTALL_OCR=true`, provision the detector and OCR cache in the runtime image/mount,
then set `ALPR_PROVIDER=real`, `ALPR_OCR_ENABLED=true` and rebuild. Frontend always
uses the backend provider; there is no frontend ALPR mock switch.

Real benchmark requires a labelled dataset whose `image` files exist. The
repository's synthetic fixture splits only validate mock behavior. Local readiness
is verified, but a real demo video, accuracy measurements and cold/warm real p95
remain release gates.

From backend, install `.[e2e]`, run `py -3 -m playwright install chromium`, then:

```powershell
py -3 scripts/smoke_station_e2e.py
```

On Windows the script uses installed Microsoft Edge for H.264 MP4 support; override
with `E2E_BROWSER_CHANNEL` when needed. Playwright Chromium on Windows omits H.264.

This uses ffmpeg to generate a gray MP4, logs in as Operator, verifies preview,
corrected check-in, duplicate rejection, idempotent replay and manual fallback
following an injected ALPR 503. The parking API and PostgreSQL persistence are real;
ALPR uses the configured backend mock. Screenshots and a sanitized report go to
`docs/phase-2-evidence`. The script removes only its uniquely named QA lane and owned
records/images. Existing user and vehicle records are preserved.


## Bật nhận diện thật trong Docker (CPU)

Model YOLO phải nằm tại `backend/app/alpr/weights/best.pt` và đúng checksum manifest.
Provision cache OCR đã tải sẵn, rồi áp dụng override:

```powershell
cd backend
py -3 scripts/provision_real_docker.py
cd ..
docker compose -f docker-compose.yml -f deployment/compose.real.yml build backend
docker compose -f docker-compose.yml -f deployment/compose.real.yml up -d --no-build
```

Nếu OCR cache ở vị trí khác, truyền `--ocr-model-dir <folder>` cho script.
Override cài YOLO, PaddleOCR và PyTorch CPU, mount detector/cache/manifest read-only,
và load model trước khi mở HTTP listener. Model assets vẫn nằm ngoài Git/image.
Các build args của migrate/backend giống nhau vì hai service dùng chung image.

Trên máy hiện tại `.env` đặt `COMPOSE_FILE=docker-compose.yml;deployment/compose.real.yml`
và `COMPOSE_PATH_SEPARATOR=;`, nên `docker compose up -d --no-build` giữ provider real.

Station: chọn lane IN, chọn MP4, bấm Play và Start Auto Capture (hoặc Capture Frame).
Chọn video chỉ tạo object URL; nhận diện chạy trên JPEG capture từ video, không upload
nguyên MP4 lên backend. Frame không có biển hoặc crop không đạt quality gate trả
no-plate/quality flags, không trả biển mẫu. Operator vẫn cần xác nhận trước khi tạo PARKED.

Current provider is real-only. Test doubles belong to the tests directory. See [data preservation runbook](real-data-runbook.md).
