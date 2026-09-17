# VisionPark — Overview

Smart Parking Control Center — Phase 1 frontend (React + Vite + TS + Router + Vitest).

## Mục tiêu Phase 1
- Admin/Operator portal: đăng nhập, dashboard, quét biển số (shell), lịch sử/sửa xác nhận, quản lý lanes/users/roles, ALPR, audit, system, profile.
- Không Phase 2: Payment, VietQR, Barrier, RTSP, Monthly Ticket, Fee, CRM, Slot Map, Redis, WebSocket.

## Vai trò
- ADMIN: toàn quyền quản lý.
- OPERATOR: station.use, detections.read/confirm, lanes.read, profile.read/update, help/notifications/settings.

## Nguồn
- Source: `frontend/docs/*.md`
- Health live: `GET /health/ready`
