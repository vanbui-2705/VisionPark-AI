# VisionPark

VisionPark là hệ thống quản lý bãi đỗ xe thông minh, sử dụng nhận diện biển số
(ALPR) để hỗ trợ quy trình xe vào, xe ra, quản lý vé tháng, tính phí, thanh toán
và điều khiển barrier.

Repository được tổ chức theo kiến trúc **modular monolith**: FastAPI đảm nhiệm API,
nghiệp vụ và ALPR; một ứng dụng React dùng chung cho màn hình vận hành và quản trị;
PostgreSQL là nguồn dữ liệu chuẩn.

![Kiến trúc thành phần VisionPark](docs/VisionPark_Component_Diagram.svg)

## Trạng thái dự án

VisionPark đang trong quá trình phát triển. Kiến trúc và tài liệu mô tả hệ thống
MVP hoàn chỉnh, trong khi mã nguồn hiện tại mới triển khai một phần nền tảng.

| Hạng mục | Trạng thái hiện tại |
| --- | --- |
| FastAPI foundation, cấu hình và xử lý lỗi | Đã có |
| PostgreSQL, SQLAlchemy, Alembic và seed | Đã có nền tảng |
| JWT authentication và RBAC | Đã có |
| Health và readiness API | Đã có |
| ALPR interface, service và ONNX provider | Đã có boundary, đang hoàn thiện wiring |
| Lane, parking, pricing, payment và reporting | Thiết kế mục tiêu, chưa hoàn thiện |
| React Station/Admin | Đã có cấu trúc thư mục, chưa có ứng dụng chạy được |
| Docker Compose và tích hợp thiết bị | Chưa hoàn thiện |

> `/health/ready` có thể trả `503` khi ALPR runtime chưa được cấu hình. Đây là
> hành vi dự kiến, không đồng nghĩa với việc process FastAPI đã dừng.

## Chức năng mục tiêu

- Đăng nhập và phân quyền cho quản trị viên, kế toán và nhân viên vận hành.
- Quản lý người dùng, làn xe và nguồn camera.
- Nhận diện biển số bằng pipeline YOLO/OCR và cho phép xác nhận thủ công.
- Ghi nhận xe vào, chống giao dịch trùng và kiểm tra sức chứa.
- Quản lý vé tháng và phân loại khách vãng lai.
- Đối chiếu ảnh xe vào/ra, tính phí và xử lý thanh toán.
- Tích hợp VietQR/ngân hàng và barrier qua adapter.
- Lưu ảnh phương tiện ngoài database và quản lý metadata trong PostgreSQL.
- Báo cáo, audit log, health check và monitoring.

## Công nghệ

| Thành phần | Công nghệ |
| --- | --- |
| Backend | Python 3.11+, FastAPI, Pydantic |
| Database | PostgreSQL, SQLAlchemy 2, Alembic |
| Authentication | JWT HS256, Argon2id, RBAC |
| ALPR | ONNX Runtime, YOLO/OCR, OpenCV theo provider |
| Frontend mục tiêu | React, TypeScript, Vite |
| Video mục tiêu | Camera RTSP, MediaMTX |
| Triển khai mục tiêu | Docker, Docker Compose, Nginx |
| Kiểm thử | Pytest, Ruff |

## Kiến trúc

Các nguyên tắc chính:

- Backend là modular monolith; ALPR là module nội bộ, không phải microservice riêng.
- HTTP endpoint chỉ xử lý transport; business logic thuộc service.
- Repository phụ trách truy vấn dữ liệu; service sở hữu transaction nghiệp vụ.
- ALPR chỉ trả kết quả nhận diện, không quyết định phí, vé hoặc mở barrier.
- PostgreSQL lưu dữ liệu nghiệp vụ và metadata; ảnh được lưu qua storage adapter.
- Barrier chỉ được mở sau khi dữ liệu bắt buộc đã commit thành công.

Tài liệu kiến trúc:

- [Kiến trúc hệ thống](docs/architecture.md)
- [Component, Deployment và Package Diagram](docs/system-diagrams.md)
- [Activity Diagram](docs/activity-diagrams.md)
- [ERD khái niệm](docs/erd-conceptual.html)
- [Tài liệu nghiệp vụ/BA-SRS](docs/Document.md)

## Cấu trúc repository

```text
VisionPark/
├── backend/
│   ├── alembic/                 # Database migrations
│   ├── app/
│   │   ├── api/                 # HTTP API và router
│   │   ├── core/                # Config, security, logging, middleware
│   │   ├── database/            # Session, ORM base và seed
│   │   ├── modules/             # Các module nghiệp vụ
│   │   ├── alpr/                # ALPR runtime và các port
│   │   └── integrations/        # Camera, barrier, payment, storage adapters
│   └── tests/
├── frontend/
│   └── src/                     # React application theo kiến trúc mục tiêu
├── docs/                        # Tài liệu và sơ đồ hệ thống
├── openspec/                    # Proposal, design, specs và task planning
└── tests/                       # Kiểm thử liên thông toàn hệ thống
```

## Chạy backend trên máy local

### 1. Yêu cầu

- Python 3.11 trở lên.
- PostgreSQL đang hoạt động.
- Git.

### 2. Tạo môi trường và cài dependencies

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Trên Linux/macOS, kích hoạt virtual environment bằng:

```bash
source .venv/bin/activate
```

### 3. Cấu hình môi trường

```powershell
Copy-Item .env.example .env
```

Cập nhật tối thiểu các biến sau trong `backend/.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://visionpark:visionpark@localhost:5432/visionpark
JWT_SECRET_KEY=thay-bang-chuoi-ngau-nhien-it-nhat-32-ky-tu
SEED_ADMIN_PASSWORD=mat-khau-admin-local
SEED_OPERATOR_PASSWORD=mat-khau-operator-local
```

Không commit file `.env` hoặc secret thật vào repository.

### 4. Migration và seed dữ liệu

```powershell
alembic upgrade head
python -m app.database.seed
```

Seed mặc định tạo hai tài khoản local theo biến môi trường:

- `SEED_ADMIN_USERNAME` — vai trò `ADMIN`.
- `SEED_OPERATOR_USERNAME` — vai trò `OPERATOR`.

### 5. Khởi động API

```powershell
uvicorn app.main:app --reload
```

Sau khi khởi động:

- Swagger UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Liveness: <http://localhost:8000/health/live>
- Readiness: <http://localhost:8000/health/ready>

## API hiện có

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| `GET` | `/health/live` | Kiểm tra process FastAPI |
| `GET` | `/health/ready` | Kiểm tra database và ALPR dependency |
| `POST` | `/api/v1/auth/login` | Đăng nhập và nhận JWT |
| `GET` | `/api/v1/auth/me` | Lấy thông tin người dùng hiện tại |

Mã nguồn endpoint nhận diện đã có tại
`backend/app/api/endpoints/alpr.py`, nhưng dependency injection và đăng ký router
vẫn cần được hoàn thiện trước khi sử dụng như một API chính thức.

## Chạy backend bằng Docker

Build image từ thư mục gốc của repository:

```powershell
docker build -t visionpark-backend ./backend
```

Khởi động API tại port `8000`:

```powershell
docker run --rm -p 8000:8000 visionpark-backend
```

Nếu PostgreSQL chạy trực tiếp trên máy host, truyền `DATABASE_URL` sử dụng
`host.docker.internal` để container truy cập được database:

```powershell
docker run --rm -p 8000:8000 `
  -e DATABASE_URL=postgresql+psycopg://visionpark:visionpark@host.docker.internal:5432/visionpark `
  visionpark-backend
```

Docker healthcheck sử dụng `/health/live`. Endpoint `/health/ready` chỉ trả trạng
thái sẵn sàng khi PostgreSQL và ALPR provider đã được cấu hình.

## Kiểm thử và kiểm tra mã nguồn

Chạy từ thư mục `backend`:

```powershell
pytest
ruff check .
ruff format --check .
```

Kiểm tra migration rollback/upgrade:

```powershell
alembic downgrade base
alembic upgrade head
```

## Sơ đồ hệ thống

| Sơ đồ | Bản xem | Nguồn PlantUML |
| --- | --- | --- |
| Component | [SVG](docs/VisionPark_Component_Diagram.svg) | [PUML](docs/component-diagram.puml) |
| Deployment | [SVG](docs/VisionPark_Deployment_Diagram.svg) | [PUML](docs/deployment-diagram.puml) |
| Package | [SVG](docs/VisionPark_Package_Diagram.svg) | [PUML](docs/package-diagram.puml) |
| Activity tổng quan | [SVG](docs/VisionPark_Activity_Overview.svg) | [PUML](docs/activity-overview.puml) |
| Activity check-in | [PNG](docs/VisionPark_Activity_CheckIn.png) | [PUML](docs/activity-check-in.puml) |
| Activity check-out | [PNG](docs/VisionPark_Activity_CheckOut.png) | [PUML](docs/activity-check-out.puml) |

## Quy ước phát triển

- Mã backend đặt dưới `backend/app`; domain nghiệp vụ đặt trong `app/modules`.
- Mã ALPR đặt trong `app/alpr`; integration bên ngoài đặt trong `app/integrations`.
- Mã frontend đặt dưới `frontend/src`; chức năng đặt trong `src/modules`.
- Không đưa business logic vào HTTP endpoint hoặc React component.
- Critical write phải có authorization, transaction, idempotency và audit phù hợp.
- Test riêng của backend/frontend nằm trong parent tương ứng; `tests/` ở root dành
  cho E2E, performance và security test toàn hệ thống.

Xem thêm quy định kiến trúc tại [CLAUDE.md](CLAUDE.md) và
[Nguyen_tac.md](Nguyen_tac.md).
