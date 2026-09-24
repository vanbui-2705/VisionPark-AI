# PHAN CONG CONG VIEC PHASE 1 - VISIONPARK

## 1. Thong tin phase

| Thuoc tinh | Noi dung |
| --- | --- |
| Ten phase | Phase 1 - Nen tang va ALPR baseline |
| Thoi luong | 7 ngay lam viec |
| Quy mo team | 5 nguoi |
| PM / Lead | Nguoi 1 |
| Muc tieu demo | Doc video MP4, nhan dien bien so, hien thi ket qua va quan ly lan co ban |
| Dau vao AI | Video MP4 duoc chon tren giao dien Station |
| Trang thai | San sang dua vao backlog |

## 2. Muc tieu Phase 1

Phase 1 tao nen tang ky thuat de cac phase sau phat trien check-in, check-out, ve thang, tinh phi va thanh toan. Ket thuc phase, team phai demo duoc luong sau:

```text
Docker Compose khoi dong he thong
    -> Operator dang nhap
    -> Chon va phat video MP4
    -> Frontend lay frame tu video
    -> Backend goi ALPR
    -> ALPR tra bien so, bbox, confidence va latency
    -> UI hien thi ket qua hoac yeu cau nhap tay
    -> Admin dang nhap va quan ly lan IN/OUT
```

### 2.1. Pham vi bat buoc

- [ ] Khoi tao backend FastAPI dung kien truc modular monolith.
- [ ] Khoi tao mot frontend React dung chung cho Station va Admin.
- [ ] Khoi tao PostgreSQL, migration va du lieu seed.
- [ ] Co dang nhap, authentication va role co ban.
- [ ] Co quan ly lan `IN/OUT` toi thieu.
- [ ] Co pipeline ALPR baseline tu video MP4.
- [ ] Co API nhan frame va tra ket qua ALPR.
- [ ] Co giao dien Station phat video va hien thi ket qua.
- [ ] Co Docker Compose, CI va bo kiem thu Phase 1.

### 2.2. Ngoai pham vi

- Train YOLO/PaddleOCR chinh thuc.
- Check-in/check-out hoan chinh.
- Ve thang, bieu phi, thanh toan va VietQR.
- Dashboard va bao cao nghiep vu that.
- Camera, barrier hoac thiet bi that.
- Dieu khien mo cong tu dong.

### 2.3. Gia dinh demo

| Hang muc | Gia tri Phase 1 |
| --- | --- |
| Bai xe | Mot bai xe |
| Lan | `LANE_IN_01`, `LANE_OUT_01` |
| Nguon video | File MP4 |
| Loai xe | `CAR` |
| Barrier | Mo phong bang ket qua `allow_open`, khong dieu khien thiet bi |
| Tan suat xu ly | Cau hinh, khoi dau 5 frame/giay |
| Dong thoi | Moi Station chi co toi da mot ALPR request dang xu ly |
| Model | Pretrained model de do baseline |

## 3. Co cau va quyen so huu

| Thanh vien | Ho ten | Vai tro | Pham vi so huu chinh |
| --- | --- | --- | --- |
| Nguoi 1 |  | PM Lead + AI Lead + DevOps + QA Lead | ALPR, deployment, CI, test plan, nghiem thu |
| Nguoi 2 |  | Backend Core | FastAPI core, database, auth, users |
| Nguoi 3 |  | Backend Domain | Lanes, ALPR endpoint, storage adapter, health |
| Nguoi 4 |  | Station Frontend | Station layout, video, frame capture, ALPR result |
| Nguoi 5 |  | Admin Frontend | App shell, login, API client, Admin layout, lane UI |

Quy tac ownership:

- Nguoi 2 so huu backend core; Nguoi 3 khong tu thay doi security/database foundation.
- Nguoi 3 so huu API ALPR; Nguoi 1 so huu thuat toan/model ALPR.
- Nguoi 5 so huu app shell va HTTP client; Nguoi 4 dung lai, khong tao client thu hai.
- Moi thanh vien tu viet unit test cho phan cua minh.
- Nguoi 1 so huu test plan, integration test, CI gate va quyet dinh nghiem thu.
- Thay doi API contract phai duoc Nguoi 1 phe duyet truoc khi merge.

## 4. Nguoi 1 - PM Lead, AI Lead, DevOps va QA Lead

### 4.1. Muc tieu

Dieu phoi Phase 1, cung cap ALPR baseline, xay dung moi truong chung va dam bao san pham dat tieu chi nghiem thu.

### 4.2. Cong viec PM/Lead

| ID | Cong viec | Dau ra | Han |
| --- | --- | --- | --- |
| `P1-PM-01` | Chot scope va ngoai pham vi | Noi dung muc 2 duoc team dong y | Ngay 1 |
| `P1-PM-02` | Chot API contract ALPR | Request/response mau, ma loi | Ngay 1 |
| `P1-PM-03` | Tao backlog | Moi task co owner, deadline, dependency, DoD | Ngay 1 |
| `P1-PM-04` | Chot quy tac Git/PR | Branch, review, CI gate | Ngay 1 |
| `P1-PM-05` | Dieu hanh daily | Bien ban blocker va hanh dong xu ly | Hang ngay |
| `P1-PM-06` | Review kien truc | Khong co code sai parent/module | Truoc merge |
| `P1-PM-07` | Dieu phoi integration | Ke hoach ghep API, AI va UI | Ngay 4-6 |
| `P1-PM-08` | To chuc demo noi bo | Bien ban pass/fail tung tieu chi | Ngay 7 |

### 4.3. Cong viec AI

| ID | Cong viec | Dau ra | Tieu chi hoan thanh |
| --- | --- | --- | --- |
| `P1-AI-01` | Chot `ALPRResult` schema | Contract noi bo AI | Co day du plate, bbox, confidence |
| `P1-AI-02` | Chot bbox convention | `[x1,y1,x2,y2]` | Thong nhat pixel coordinate |
| `P1-AI-03` | Tao runtime interface | `detect_and_read(frame)` | Backend goi ma khong phu thuoc chi tiet model |
| `P1-AI-04` | Tao ONNX ALPR provider | ONNX runtime | Load file `.onnx` tu Colab, xu ly OpenCV |
| `P1-AI-05` | Crop va tien xu ly | Plate cropper | Resize hinh anh va cat theo bbox cho OCR |
| `P1-AI-06` | Chuan hoa bien so | Normalizer | Viet hoa; bo khoang trang, dau cham va gach |
| `P1-AI-07` | Tong hop confidence | Confidence policy | `< 0.85` dat `requires_confirmation=true` |
| `P1-AI-08` | Tao schema HTTP ALPR | Request/response models | OpenAPI the hien dung multipart, result va error |
| `P1-AI-09` | Nhan va kiem tra frame | Multipart parser | Chi nhan JPEG/PNG hop le, gioi han size |
| `P1-AI-10` | Tao ALPR application service | Luong dieu phoi detection | Kiem tra lane, goi ONNX runtime, luu anh/ket qua |
| `P1-AI-11` | Tao Detection API | `POST /alpr/detections` | Goi luong xu ly thuc te; handle validation/ONNX errors |
| `P1-AI-12` | Viet test ALPR API | Contract/integration tests | Bao phu API endpoint va validation |

AI Definition of Done:

- [ ] `detect_and_read(frame)` tra cung mot kieu ket qua trong moi truong hop.
- [ ] Frame khong co bien so khong lam phat sinh exception ra ngoai runtime.
- [ ] Co unit test cho normalization va bbox clamp.
- [ ] Ket qua co `model_version` va `processing_time_ms`.
- [ ] Bao cao tach rieng video ro, video toi va video goc lech.
- [ ] Khong cong bo accuracy muc tieu khi chua co test set dai dien.

### 4.4. Cong viec DevOps

| ID | Cong viec | Dau ra | Tieu chi hoan thanh |
| --- | --- | --- | --- |
| `P1-OPS-01` | Khoi tao cay thu muc | Monorepo baseline | Dung `backend`, `frontend`, `deployment`, `tests`, `docs` |
| `P1-OPS-02` | Tao `.env.example` | Mau bien moi truong | Khong co secret that |
| `P1-OPS-03` | Dong goi backend | Backend Dockerfile | Container chay FastAPI va load ALPR |
| `P1-OPS-04` | Dong goi frontend | Frontend Dockerfile | Build React thanh cong |
| `P1-OPS-05` | Tao Docker Compose | `compose.yaml` | Khoi dong backend, frontend va PostgreSQL |
| `P1-OPS-06` | Quan ly model/video volume | Volume/mount convention | Khong dua weight/video lon vao Docker image |
| `P1-OPS-07` | Tao CI backend | Workflow | Chay Ruff va Pytest |
| `P1-OPS-08` | Tao CI frontend | Workflow | Chay lint, test va build |
| `P1-OPS-09` | Tao CI gate | Branch protection convention | CI fail thi khong merge |
| `P1-OPS-10` | Viet huong dan local | README runbook | May moi co the khoi dong theo tai lieu |

### 4.5. Cong viec QA

| ID | Kich ban | Ket qua mong doi |
| --- | --- | --- |
| `P1-QA-01` | Backend live health | Tra 200 khi process hoat dong |
| `P1-QA-02` | Backend ready health | Phan anh dung trang thai DB/model can thiet |
| `P1-QA-03` | Dang nhap dung | Tra token/phan dang nhap hop le |
| `P1-QA-04` | Dang nhap sai | Tra 401 va khong tao phien |
| `P1-QA-05` | Kiem tra RBAC | Operator khong truy cap Admin API/page |
| `P1-QA-06` | Lane CRUD | Tao, xem, sua va inactive duoc lan |
| `P1-QA-07` | Video hop le | Video phat va frame duoc gui den API |
| `P1-QA-08` | Video khong hop le | UI bao loi ro rang va khong crash |
| `P1-QA-09` | ALPR co ket qua | Response du contract; UI hien thi du thong tin |
| `P1-QA-10` | ALPR khong doc duoc | UI cho phep nhap/xac nhan thu cong |
| `P1-QA-11` | ALPR timeout/503 | UI dung loading va cho phep thu lai |
| `P1-QA-12` | Nhieu frame lien tiep | Khong co nhieu request dong thoi mat kiem soat |
| `P1-QA-13` | Migration tu DB rong | Tao schema va seed thanh cong |
| `P1-QA-14` | Clean setup | Clone moi va chay Compose theo README |
| `P1-QA-15` | CI gate | Lint/test/build loi lam workflow fail |

## 5. Nguoi 2 - Backend Core

### 5.1. Pham vi so huu

```text
backend/app/main.py
backend/app/core/
backend/app/database/
backend/app/modules/auth/
backend/app/modules/users/
backend/alembic/
```

### 5.2. Danh sach cong viec

| ID | Cong viec | Dau ra | Tieu chi hoan thanh |
| --- | --- | --- | --- |
| `P1-BE1-01` | Khoi tao FastAPI | Application entrypoint | Chay duoc Uvicorn; prefix `/api/v1` |
| `P1-BE1-02` | Xay dung config | Settings module | Doc environment; validate bien bat buoc |
| `P1-BE1-03` | Ket noi PostgreSQL | Session/engine | Quan ly session dung request scope |
| `P1-BE1-04` | Cau hinh Alembic | Migration infrastructure | Upgrade/downgrade chay duoc |
| `P1-BE1-05` | Tao User/Role model | ORM va migration | Co username, password hash, role, status |
| `P1-BE1-06` | Seed role/user demo | Seed command | Co 4 role va tai khoan demo |
| `P1-BE1-07` | Hash password | Security helper | Dung Argon2id hoac thuat toan duoc phe duyet |
| `P1-BE1-08` | Login API | Auth endpoint | Dung tra token/phien; sai tra 401 |
| `P1-BE1-09` | Current user dependency | Auth dependency | Endpoint co the yeu cau dang nhap |
| `P1-BE1-10` | Permission checker | RBAC helper | Backend tu choi role khong phu hop |
| `P1-BE1-11` | Error response chung | Exception handler | Co code, message, details, correlation_id |
| `P1-BE1-12` | Logging/correlation ID | Middleware | Moi request co correlation ID |
| `P1-BE1-13` | Unit/integration test | Test auth va DB | Happy path va loi chinh deu co test |
| `P1-BE1-14` | Ban giao foundation | Huong dan cho Nguoi 3 | Co DB session, base model va auth dependency |

Backend Core Definition of Done:

- [ ] Database rong co the tao schema bang migration.
- [ ] Password khong duoc luu hoac log dang plain text.
- [ ] API ngoai health check yeu cau authentication theo contract.
- [ ] Khong dat business logic trong endpoint.
- [ ] Test dang nhap dung, sai, user inactive va thieu quyen deu dat.

## 6. Nguoi 3 - Backend Domain va AI Integration

### 6.1. Pham vi so huu

```text
backend/app/modules/lanes/
backend/app/alpr/                 # Phan adapter/runtime, khong sua thuat toan cua Nguoi 1
backend/app/integrations/storage/
backend/app/api/endpoints/lanes.py
backend/app/api/endpoints/alpr.py
```

### 6.2. Danh sach cong viec

| ID | Cong viec | Dau ra | Tieu chi hoan thanh |
| --- | --- | --- | --- |
| `P1-BE2-01` | Tao Lane model | ORM model/migration | Co name, direction, video_source, is_active |
| `P1-BE2-02` | Tao Lane schema | Request/response DTO | Validate `IN/OUT` va du lieu bat buoc |
| `P1-BE2-03` | Tao Lane repository | Data access | Khong dat SQL trong endpoint |
| `P1-BE2-04` | Tao Lane service | Use case | Kiem tra trung ten va trang thai |
| `P1-BE2-05` | Tao Lane CRUD API | REST endpoint | Admin tao/xem/sua/inactive duoc |
| `P1-BE2-06` | Seed hai lan demo | Seed data | Co `LANE_IN_01`, `LANE_OUT_01` |
| `P1-BE2-07` | Tao ALPR request parser | Multipart endpoint | Nhan JPEG va `lane_id` |
| `P1-BE2-08` | Decode frame | Bytes -> OpenCV image | File hong tra loi co kiem soat |
| `P1-BE2-09` | Goi AI runtime | ALPR application adapter | Chi goi interface cua Nguoi 1 |
| `P1-BE2-10` | Map ALPR response | Response DTO | Du raw/normalized plate, bbox, confidence, latency, version |
| `P1-BE2-11` | Xu ly ALPR failure | Error mapping | Timeout/unavailable tra 503 dung format |
| `P1-BE2-12` | Tao health endpoints | Live/ready | Ready phan anh DB va model runtime |
| `P1-BE2-13` | Tao storage interface | Local storage adapter contract | DB chi luu metadata/key, khong luu blob |
| `P1-BE2-14` | Viet test | Unit/integration tests | Dung fake ALPR model; khong can weight trong CI |

Backend Domain Definition of Done:

- [ ] ALPR endpoint khong chua thuat toan detection/OCR.
- [ ] ALPR module khong import parking, pricing, payment hoac lane business service.
- [ ] File anh hong, lane khong ton tai va model loi deu co response ro rang.
- [ ] Test CI khong tai model weight lon tu Internet.
- [ ] Lane API co authentication va authorization backend.

## 7. Nguoi 4 - Station Frontend

### 7.1. Pham vi so huu

```text
frontend/src/layouts/StationLayout.tsx
frontend/src/modules/station/
```

### 7.2. Danh sach cong viec

| ID | Cong viec | Dau ra | Tieu chi hoan thanh |
| --- | --- | --- | --- |
| `P1-FE1-01` | Tao Station layout | Operator shell | Dung router/auth context chung |
| `P1-FE1-02` | Tao video selector | File input | Chi chap nhan video phu hop; co thong bao loi |
| `P1-FE1-03` | Tao video player | Player controls | Play, pause, replay va EOF dung |
| `P1-FE1-04` | Capture frame | Canvas/frame service | Xuat JPEG theo interval cau hinh |
| `P1-FE1-05` | Throttle request | Request controller | Toi da mot request dang xu ly |
| `P1-FE1-06` | Goi ALPR API | Station API hook | Dung HTTP client cua Nguoi 5 |
| `P1-FE1-07` | Hien thi bbox | Overlay | Bbox dung ty le khi video resize |
| `P1-FE1-08` | Hien thi ket qua | Result panel | Co plate, confidence, latency, model version |
| `P1-FE1-09` | Quan ly trang thai | UI state machine | Idle, processing, detected, needs-confirmation, error |
| `P1-FE1-10` | Nhap/sua thu cong | Confirmation form | Validate rong va chuan hoa hien thi |
| `P1-FE1-11` | Xu ly mat API | Error/retry UX | Dung loading; cho thu lai/nhap tay |
| `P1-FE1-12` | Viet test | Component/integration test | Test result, manual input, timeout va file loi |

Station Definition of Done:

- [ ] Video MP4 phat o toc do thuc, khong xu ly toan bo file mot luc.
- [ ] UI khong gui request khi video pause/ket thuc.
- [ ] Request truoc chua xong thi khong tao request moi.
- [ ] Confidence thap hien thi yeu cau xac nhan.
- [ ] Video/API loi khong lam crash application.
- [ ] Text, bbox va nut thao tac khong bi de len nhau tren man hinh demo.

## 8. Nguoi 5 - Admin Frontend va App Foundation

### 8.1. Pham vi so huu

```text
frontend/src/app/
frontend/src/api/
frontend/src/layouts/AdminLayout.tsx
frontend/src/modules/auth/
frontend/src/modules/lanes/
```

### 8.2. Danh sach cong viec

| ID | Cong viec | Dau ra | Tieu chi hoan thanh |
| --- | --- | --- | --- |
| `P1-FE2-01` | Khoi tao React/TypeScript/Vite | Frontend application | Dev server, test va build chay duoc |
| `P1-FE2-02` | Tao router | Route structure | Co login, station va admin routes |
| `P1-FE2-03` | Tao auth provider | Session state | Luu/clear phien va current user dung contract |
| `P1-FE2-04` | Tao HTTP client chung | API client | Gan token va map error response |
| `P1-FE2-05` | Tao man hinh login | Login form | Loading, sai mat khau va thanh cong ro rang |
| `P1-FE2-06` | Tao role route guard | Authorization UI | Operator bi chan khoi Admin route |
| `P1-FE2-07` | Tao Admin layout | Admin shell/navigation | Cung application voi Station |
| `P1-FE2-08` | Tao Lane list | Data table | Hien thi name, direction, source, status |
| `P1-FE2-09` | Tao Lane form | Create/edit form | Validate truong bat buoc va `IN/OUT` |
| `P1-FE2-10` | Active/inactive lane | Admin action | Co confirm va feedback thanh cong/loi |
| `P1-FE2-11` | Ban giao app shell | Integration guide | Nguoi 4 gan Station route khong sua app core |
| `P1-FE2-12` | Viet test | Frontend tests | Test login, route guard, client va Lane form |

Admin Definition of Done:

- [ ] Station va Admin dung chung router, auth context va API client.
- [ ] UI an chuc nang theo role, nhung khong duoc thay the backend authorization.
- [ ] Refresh trang khong lam frontend roi vao trang sai role.
- [ ] Form co loading, validation, success va error states.
- [ ] Khong tao dashboard gia bang du lieu hard-code trong Phase 1.

## 9. API contract bat buoc

### 9.1. ALPR detection

```http
POST /api/v1/alpr/detections
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

Request:

| Field | Type | Bat buoc | Mo ta |
| --- | --- | :---: | --- |
| `image` | JPEG/PNG file | Co | Frame trich tu video |
| `lane_id` | string/UUID theo schema | Co | Lan dang xu ly |

Response thanh cong:

```json
{
  "detection_id": "uuid",
  "raw_plate_number": "29A-123.45",
  "normalized_plate_number": "29A12345",
  "bbox": [120, 340, 250, 410],
  "confidence": 0.91,
  "processing_time_ms": 185,
  "model_version": "alpr-baseline-0.1.0",
  "requires_confirmation": false
}
```

Response khong doc duoc bien so van la ket qua xu ly hop le:

```json
{
  "detection_id": "uuid",
  "raw_plate_number": null,
  "normalized_plate_number": null,
  "bbox": null,
  "confidence": 0.0,
  "processing_time_ms": 170,
  "model_version": "alpr-baseline-0.1.0",
  "requires_confirmation": true
}
```

Loi he thong dung format chung:

```json
{
  "code": "DEPENDENCY_UNAVAILABLE",
  "message": "ALPR runtime is unavailable.",
  "details": {},
  "correlation_id": "uuid"
}
```

## 10. Dependency va ban giao

| Ben giao | Ben nhan | Noi dung | Han |
| --- | --- | --- | --- |
| Nguoi 1 | Nguoi 3 | ALPR interface va response schema | Cuoi ngay 1 |
| Nguoi 1 | Ca team | Compose convention, env va CI rule | Cuoi ngay 2 |
| Nguoi 2 | Nguoi 3 | DB session, base model, auth dependency | Cuoi ngay 2 |
| Nguoi 2 | Nguoi 5 | Login contract va role data | Cuoi ngay 2 |
| Nguoi 3 | Nguoi 4 | ALPR endpoint va Lane endpoint | Cuoi ngay 4 |
| Nguoi 5 | Nguoi 4 | App shell, auth context va API client | Cuoi ngay 2 |
| Nguoi 4 | Nguoi 1 | Station demo build | Cuoi ngay 5 |
| Tat ca | Nguoi 1 | Test evidence va PR da review | Cuoi ngay 6 |

Neu mot ban giao tre hon 0.5 ngay, owner phai bao PM trong daily va ghi ro tac dong den task phu thuoc.

## 11. Lich thuc hien 7 ngay

| Ngay | Muc tieu | Ket qua cuoi ngay |
| --- | --- | --- |
| 1 | Chot contract va scaffold | Backlog, API schema, repo skeleton, frontend/backend boot |
| 2 | Nen tang doc lap | Auth/DB foundation, app shell, video reader, Compose baseline |
| 3 | Xay dung chuc nang | Lane API, YOLO/OCR baseline, Station video player |
| 4 | Tich hop lan 1 | Frontend gui frame, backend goi ALPR, Admin goi Lane API |
| 5 | Hoan thien trang thai loi | Manual fallback, timeout, validation, unit test |
| 6 | Integration va regression | Chay QA checklist, clean environment, sua bug High |
| 7 | Release va demo noi bo | CI xanh, tai lieu hoan tat, demo va bien ban nghiem thu |

## 12. Quy trinh quan ly cong viec

### 12.1. Trang thai task

```text
TODO -> IN PROGRESS -> CODE REVIEW -> QA -> DONE
```

Task bi chan dung trang thai `BLOCKED`, kem nguyen nhan, nguoi can ho tro va thoi diem can giai quyet.

### 12.2. Quy tac pull request

- Mot PR chi nen giai quyet mot task hoac mot nhom task lien quan chat che.
- PR phai ghi task ID, noi dung thay doi, cach test va anh/log chung minh.
- Toi thieu mot thanh vien khac review truoc khi merge.
- PR thay doi contract phai co Nguoi 1 phe duyet.
- Khong merge neu lint, test hoac build that bai.
- Khong commit secret, anh/video du lieu that hoac model weight lon.

### 12.3. Daily 15 phut

Moi thanh vien bao cao dung ba noi dung:

1. Hom qua da hoan thanh task nao va co evidence gi.
2. Hom nay se dua task nao sang Code Review/QA.
3. Dang bi chan boi ai, contract nao hoac moi truong nao.

## 13. Definition of Done chung

Mot task chi duoc chuyen sang `DONE` khi:

- [ ] Code nam dung parent/module da chot.
- [ ] Khong dat business logic trong endpoint hoac React component.
- [ ] Co migration neu thay doi schema database.
- [ ] Co test cho happy path va ngoai le chinh.
- [ ] Authorization, error handling va log duoc them khi can.
- [ ] CI dat.
- [ ] Pull request da duoc review.
- [ ] Co evidence: test log, screenshot hoac video demo.
- [ ] Tai lieu/API contract duoc cap nhat neu co thay doi.
- [ ] Khong commit secret, weight lon hoac du lieu nhay cam.

## 14. Tieu chi nghiem thu Phase 1

Phase 1 dat khi toan bo cac dieu kien sau thanh cong tren mot moi truong sach:

- [ ] `docker compose up --build` khoi dong duoc he thong.
- [ ] Migration tao duoc database va du lieu seed.
- [ ] Operator dang nhap va truy cap Station.
- [ ] Admin dang nhap va truy cap Admin.
- [ ] Operator khong truy cap duoc Admin API/page.
- [ ] Admin xem, tao, sua va inactive duoc Lane.
- [ ] Station chon va phat duoc video MP4.
- [ ] Station trich frame va gui den ALPR API.
- [ ] ALPR tra dung response contract.
- [ ] UI hien thi bien so, bbox, confidence, latency va model version.
- [ ] Ket qua confidence thap/khong doc duoc cho phep nhap tay.
- [ ] Video loi, API loi va model loi khong lam crash he thong.
- [ ] `/health/live` va `/health/ready` hoat dong dung.
- [ ] Backend lint/test va frontend lint/test/build deu dat.
- [ ] Khong con loi Critical/High.
- [ ] README du de mot thanh vien moi khoi dong va chay demo.

## 15. Dau ra ban giao cuoi Phase 1

- Source code backend va frontend.
- Migration va seed data.
- Dockerfile, Docker Compose va `.env.example`.
- ALPR baseline runtime va model manifest.
- Bo video fixture duoc phep su dung.
- Bao cao baseline AI.
- Bao cao QA va evidence test.
- OpenAPI contract.
- README cai dat/chay demo.
- Backlog de xuat Phase 2: dataset, fine-tune detector/OCR va luong check-in.
