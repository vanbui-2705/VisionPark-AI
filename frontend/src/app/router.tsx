import { t as translate } from "../lib/i18n"
import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from '../modules/auth/AuthContext.tsx'
import { can, type Permission } from '../lib/permissions.ts'
import { ProtectedRoute } from '../modules/auth/guards.tsx'
import { LoginPage } from '../modules/auth/LoginPage.tsx'
import { RegisterPage } from '../modules/auth/RegisterPage.tsx'
import { ChangePasswordPage } from '../modules/auth/ChangePasswordPage.tsx'
import { LaneListPage } from '../modules/lanes/LaneListPage.tsx'
import { LaneCreatePage, LaneEditPage, LaneDetailPage } from '../modules/lanes/LanePages.tsx'
import { AppShell } from '../layouts/AppShell.tsx'
import { ForbiddenPage, NotFoundPage } from '../modules/error/ErrorPages.tsx'
import { DashboardPage } from '../modules/dashboard/DashboardPage.tsx'
import { DetectionHistoryPage } from '../modules/detections/DetectionHistoryPage.tsx'
import { DetectionDetailPage } from '../modules/detections/DetectionDetailPage.tsx'
import { UserListPage } from '../modules/users/UserListPage.tsx'
import { CreateUserPage } from '../modules/users/CreateUserPage.tsx'
import { UserDetailPage } from '../modules/users/UserDetailPage.tsx'
import { UserEditPage } from '../modules/users/UserEditPage.tsx'
import { AlprPage } from '../modules/alpr/AlprPage.tsx'
import { AuditLogsPage } from '../modules/audit/AuditLogsPage.tsx'
import { ParkingDetailPage } from '../modules/parking/ParkingDetailPage.tsx'
import { ParkingHistoryPage } from '../modules/parking/ParkingHistoryPage.tsx'
import { ErrorCenterPage } from '../modules/errors/ErrorCenterPage.tsx'
import { SystemPage } from '../modules/system/SystemPage.tsx'
import { ProfilePage } from '../modules/profile/ProfilePage.tsx'
import { SettingsPage } from '../modules/settings/SettingsPage.tsx'
import { NotificationsPage } from '../modules/notifications/NotificationsPage.tsx'
import { HelpPage } from '../modules/help/HelpPage.tsx'
import { DocsLayout } from '../modules/docs/DocsLayout.tsx'
import StationPage from '../modules/station/StationPage.tsx'

const M5Page = lazy(() => import('../modules/m5/M5Page.tsx').then(module => ({ default: module.M5Page })))
const RolesPage = lazy(() => import('../modules/roles/RolesPage.tsx').then(module => ({ default: module.RolesPage })))
const PermissionsPage = lazy(() => import('../modules/permissions/PermissionsPage.tsx').then(module => ({ default: module.PermissionsPage })))
const AlprTestPage = lazy(() => import('../modules/alpr/AlprTestPage.tsx').then(module => ({ default: module.AlprTestPage })))
const UiKitPage = lazy(() => import('../modules/uikit/UiKitPage.tsx').then(module => ({ default: module.UiKitPage })))
const DocsHomePage = lazy(() => import('../modules/docs/DocsHomePage.tsx').then(module => ({ default: module.DocsHomePage })))
const DocsArticlePage = lazy(() => import('../modules/docs/DocsArticlePage.tsx').then(module => ({ default: module.DocsArticlePage })))

function RootRedirect() {
  const { initialized, isAuthenticated, user } = useAuth()
  if (!initialized) return <div style={{ padding: 24 }}>{translate("Đang tải...")}</div>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <Navigate to={can(user, 'dashboard.read') ? '/admin/dashboard' : can(user, 'station.use') ? '/station/scan' : '/profile'} replace />
}

function PermissionGuard({ permission, children }: { permission: Permission; children: React.ReactNode }) {
  const { user } = useAuth()
  return can(user, permission) ? children : <ForbiddenPage />
}

function AdminGuard({ children }: { children: React.ReactNode }) {
  const { isAdmin } = useAuth()
  if (!isAdmin) return <ForbiddenPage />
  return <>{children}</>
}

export function AppRoutes() {
  return (
    <Suspense fallback={<div style={{ padding: 24 }}>{translate("Đang tải...")}</div>}>
      <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={import.meta.env.VITE_PUBLIC_REGISTRATION_ENABLED === 'true' ? <RegisterPage /> : <Navigate to="/login" replace />} />
      <Route path="/change-password" element={<ProtectedRoute><ChangePasswordPage /></ProtectedRoute>} />
      <Route path="/" element={<RootRedirect />} />
      <Route path="/403" element={<ForbiddenPage />} />
      <Route path="/404" element={<NotFoundPage />} />

      {/* Station has one canonical flow; legacy fullscreen URLs redirect to it. */}
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route path="/station" element={<Navigate to="/station/scan" replace />} />
        <Route path="/station/scan" element={<PermissionGuard permission="station.use"><StationPage /></PermissionGuard>} />
        <Route path="/station/scan/fullscreen" element={<Navigate to="/station/scan" replace />} />
        <Route path="/station/history" element={<Navigate to="/detections" replace />} />

        {/* Detections / Parking operations — ADMIN + OPERATOR */}
        <Route path="/detections" element={<PermissionGuard permission="detections.read"><DetectionHistoryPage /></PermissionGuard>} />
        <Route path="/detections/:id" element={<PermissionGuard permission="detections.read"><DetectionDetailPage /></PermissionGuard>} />
        <Route path="/parking" element={<PermissionGuard permission="transactions.read"><ParkingHistoryPage /></PermissionGuard>} />
        <Route path="/parking/:id" element={<PermissionGuard permission="transactions.read"><ParkingDetailPage /></PermissionGuard>} />
        <Route path="/operations/transactions" element={<Navigate to="/parking" replace />} />
        <Route path="/operations/transactions/:id" element={<Navigate to="/parking" replace />} />
        <Route path="/admin/detections" element={<Navigate to="/detections" replace />} />
        <Route path="/admin/detections/:id" element={<Navigate to="/detections" replace />} />
        <Route path="/admin/parking" element={<Navigate to="/parking" replace />} />
        <Route path="/admin/parking/:id" element={<Navigate to="/parking" replace />} />

        {/* Admin-only */}
        <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
        <Route path="/admin/m5" element={<PermissionGuard permission="operations.report.read"><M5Page /></PermissionGuard>} />
        <Route path="/admin/dashboard" element={<PermissionGuard permission="dashboard.read"><DashboardPage /></PermissionGuard>} />
        <Route path="/admin/lanes" element={<PermissionGuard permission="lanes.read"><LaneListPage /></PermissionGuard>} />
        <Route path="/admin/lanes/new" element={<PermissionGuard permission="lanes.create"><LaneCreatePage /></PermissionGuard>} />
        <Route path="/admin/lanes/:id" element={<PermissionGuard permission="lanes.read"><LaneDetailPage /></PermissionGuard>} />
        <Route path="/admin/lanes/:id/edit" element={<PermissionGuard permission="lanes.update"><LaneEditPage /></PermissionGuard>} />
        <Route path="/admin/users" element={<PermissionGuard permission="users.read"><UserListPage /></PermissionGuard>} />
        <Route path="/admin/users/new" element={<PermissionGuard permission="users.manage"><CreateUserPage /></PermissionGuard>} />
        <Route path="/admin/users/:id" element={<PermissionGuard permission="users.read"><UserDetailPage /></PermissionGuard>} />
        <Route path="/admin/users/:id/edit" element={<PermissionGuard permission="users.manage"><UserEditPage /></PermissionGuard>} />
        <Route path="/admin/roles" element={<AdminGuard><RolesPage /></AdminGuard>} />
        <Route path="/admin/permissions" element={<AdminGuard><PermissionsPage /></AdminGuard>} />
        <Route path="/admin/alpr" element={<PermissionGuard permission="alpr.read"><AlprPage /></PermissionGuard>} />
        <Route path="/admin/alpr/test" element={<AdminGuard><AlprTestPage /></AdminGuard>} />
        <Route path="/admin/audit-logs" element={<PermissionGuard permission="audit.read"><AuditLogsPage /></PermissionGuard>} />
        <Route path="/admin/errors" element={<PermissionGuard permission="errors.read"><ErrorCenterPage /></PermissionGuard>} />
        <Route path="/admin/system" element={<PermissionGuard permission="system.read"><SystemPage /></PermissionGuard>} />

        {/* Tài khoản — mọi role đăng nhập */}
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/admin/profile" element={<Navigate to="/profile" replace />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/help" element={<HelpPage />} />
        {import.meta.env.DEV ? <Route path="/dev/ui-kit" element={<AdminGuard><UiKitPage /></AdminGuard>} /> : null}

        {/* Docs & Explore Center — ADMIN only */}
        <Route path="/docs" element={<AdminGuard><DocsLayout /></AdminGuard>}>
          <Route index element={<DocsHomePage />} />
          <Route path=":slug" element={<DocsArticlePage />} />
        </Route>
        <Route path="/explore" element={<Navigate to="/docs" replace />} />
        <Route path="/admin/explore" element={<Navigate to="/docs" replace />} />
      </Route>

      <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </Suspense>
  )
}
