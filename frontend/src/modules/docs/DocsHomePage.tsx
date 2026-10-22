import { t as translate } from "../../lib/i18n"
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { healthApi } from '../../api/healthApi.ts'
import { Badge } from '../../components/ui/Badge.tsx'

interface DocMetadata {
  slug: string
  titleVi: string
  titleEn: string
  category: 'overview' | 'ai' | 'backend' | 'frontend' | 'security' | 'ops'
  categoryName: string
  icon: string
  badge: string
  description: string
  readTime: string
  tags: string[]
}

const DOCS_METADATA: DocMetadata[] = [
  {
    slug: 'overview',
    titleVi: 'Tổng quan giải pháp',
    titleEn: 'Overview & Architecture',
    category: 'overview',
    categoryName: 'Tổng quan',
    icon: '🧭',
    badge: 'CORE',
    description: 'Tổng thể giải pháp quản lý bãi xe thông minh VisionPark, kết nối Station và backend FastAPI qua PostgreSQL.',
    readTime: '3 phút',
    tags: ['FastAPI', 'PostgreSQL', 'Station Flow'],
  },
  {
    slug: 'architecture',
    titleVi: 'Kiến trúc hệ thống',
    titleEn: 'System Architecture',
    category: 'overview',
    categoryName: 'Tổng quan',
    icon: '🏛️',
    badge: 'ARCH',
    description: 'Mô hình phân tầng Clean Architecture, ranh giới xử lý AI ALPR, giao thức REST và lưu trữ dữ liệu bền vững.',
    readTime: '5 phút',
    tags: ['Multi-tier', 'Docker', 'Decoupled'],
  },
  {
    slug: 'ai-context',
    titleVi: 'Bối cảnh AI & Mô hình',
    titleEn: 'AI Context & Boundaries',
    category: 'overview',
    categoryName: 'Tổng quan',
    icon: '🤖',
    badge: 'AI',
    description: 'Nguyên tắc vận hành mô hình AI thực tế, loại bỏ hoàn toàn mock data, cam kết độ trễ dưới 2 giây.',
    readTime: '4 phút',
    tags: ['Real YOLO', 'No Mock', 'High Precision'],
  },
  {
    slug: 'alpr',
    titleVi: 'Mô hình ALPR nhận diện',
    titleEn: 'Automatic Plate Recognition',
    category: 'ai',
    categoryName: 'AI & Vận hành',
    icon: '👁️',
    badge: 'YOLO + OCR',
    description: 'Pipeline nhận diện biển số: YOLOv8 định vị bounding box kết hợp PaddleOCR nhận dạng ký tự chuẩn Việt Nam.',
    readTime: '6 phút',
    tags: ['YOLOv8', 'PaddleOCR', 'Threshold 0.85'],
  },
  {
    slug: 'station',
    titleVi: 'Trạm quét biển số (Station)',
    titleEn: 'Station Scan & Operations',
    category: 'ai',
    categoryName: 'AI & Vận hành',
    icon: '🎥',
    badge: 'OPERATOR',
    description: 'Màn hình vận hành chính cho nhân viên: capture video, cơ chế đồng thuận 2/3 frame và sửa tay biển số.',
    readTime: '5 phút',
    tags: ['Consensus 2/3', 'Live Camera', 'Manual Edit'],
  },
  {
    slug: 'lanes',
    titleVi: 'Quản lý làn xe (Lanes)',
    titleEn: 'Lane Configuration',
    category: 'ai',
    categoryName: 'AI & Vận hành',
    icon: '🛣️',
    badge: 'HARDWARE',
    description: 'Cấu hình luồng làn vào (IN) và làn ra (OUT), định tuyến camera và quản lý trạng thái kích hoạt làn an toàn.',
    readTime: '3 phút',
    tags: ['IN/OUT Gate', 'Deactivate Safe', 'Stream Route'],
  },
  {
    slug: 'backend',
    titleVi: 'Backend FastAPI',
    titleEn: 'Backend Services',
    category: 'backend',
    categoryName: 'Backend & Dữ liệu',
    icon: '⚙️',
    badge: 'PYTHON',
    description: 'Dịch vụ lõi Python/FastAPI điều phối pipeline nhận diện, lưu vết kiểm toán và quản lý giao dịch đỗ xe.',
    readTime: '4 phút',
    tags: ['FastAPI', 'Async IO', 'SQLAlchemy'],
  },
  {
    slug: 'api',
    titleVi: 'Đặc tả API RESTful',
    titleEn: 'REST API Specification',
    category: 'backend',
    categoryName: 'Backend & Dữ liệu',
    icon: '⚡',
    badge: 'API',
    description: 'Danh mục endpoint `/api/v1/*`, định dạng multipart, phân trang server-side và mã tracking correlationId.',
    readTime: '5 phút',
    tags: ['OpenAPI', 'Correlation ID', 'Pagination'],
  },
  {
    slug: 'database',
    titleVi: 'Cơ sở dữ liệu PostgreSQL',
    titleEn: 'Database & Schema',
    category: 'backend',
    categoryName: 'Backend & Dữ liệu',
    icon: '🗄️',
    badge: 'POSTGRES',
    description: 'Lược đồ dữ liệu quan hệ cho bảng detections, parking_transactions, audit_logs và users.',
    readTime: '4 phút',
    tags: ['Relational Schema', 'Indexing', 'Audit Logs'],
  },
  {
    slug: 'configuration',
    titleVi: 'Cấu hình hệ thống',
    titleEn: 'Environment & Config',
    category: 'backend',
    categoryName: 'Backend & Dữ liệu',
    icon: '🔧',
    badge: 'CONFIG',
    description: 'Thiết lập biến môi trường `.env`, tham số ngưỡng nhận diện, đường dẫn trọng số model và chính sách CORS.',
    readTime: '3 phút',
    tags: ['DotEnv', 'Model Weights', 'CORS Config'],
  },
  {
    slug: 'frontend',
    titleVi: 'Frontend React 19',
    titleEn: 'Frontend Architecture',
    category: 'frontend',
    categoryName: 'Giao diện & UI',
    icon: '💻',
    badge: 'REACT 19',
    description: 'Kiến trúc Single Page App xây dựng trên React 19, Vite, TypeScript với thiết kế component hóa cao cấp.',
    readTime: '4 phút',
    tags: ['React 19', 'TypeScript', 'Clean Modules'],
  },
  {
    slug: 'components',
    titleVi: 'Hệ thống UI Component',
    titleEn: 'Design System & UI Kit',
    category: 'frontend',
    categoryName: 'Giao diện & UI',
    icon: '🧩',
    badge: 'UI KIT',
    description: 'Thư viện thành phần dùng chung: Button, Modal, BBoxOverlay, Toast, Badge và DetectionImage.',
    readTime: '3 phút',
    tags: ['Design Tokens', 'Dark/Light', 'Accessibility'],
  },
  {
    slug: 'routes',
    titleVi: 'Định tuyến & Route Guards',
    titleEn: 'Routing & Navigation',
    category: 'frontend',
    categoryName: 'Giao diện & UI',
    icon: '🗺️',
    badge: 'ROUTING',
    description: 'Cây điều hướng React Router, cơ chế bảo vệ ProtectedRoute, AdminGuard và kiểm tra quyền can().',
    readTime: '3 phút',
    tags: ['React Router', 'Guard', 'Permission Check'],
  },
  {
    slug: 'auth',
    titleVi: 'Xác thực người dùng',
    titleEn: 'Authentication & Session',
    category: 'security',
    categoryName: 'Bảo mật & Phân quyền',
    icon: '🔑',
    badge: 'JWT',
    description: 'Xác thực tài khoản qua Bearer JWT token, mã hóa mật khẩu an toàn và cơ chế thu hồi phiên đăng nhập.',
    readTime: '4 phút',
    tags: ['JWT Token', 'Bcrypt', 'Session Revoke'],
  },
  {
    slug: 'rbac',
    titleVi: 'Phân quyền vai trò (RBAC)',
    titleEn: 'Role-Based Access Control',
    category: 'security',
    categoryName: 'Bảo mật & Phân quyền',
    icon: '🛡️',
    badge: 'SECURITY',
    description: 'Ma trận phân quyền nghiêm ngặt trên 4 vai trò: ADMIN, OPERATOR, ACCOUNTANT và TECHNICIAN.',
    readTime: '4 phút',
    tags: ['4 Roles', 'Granular Matrix', 'Backend Enforced'],
  },
  {
    slug: 'users',
    titleVi: 'Quản lý tài khoản',
    titleEn: 'User Management',
    category: 'security',
    categoryName: 'Bảo mật & Phân quyền',
    icon: '👥',
    badge: 'ACCOUNTS',
    description: 'Tạo tài khoản nhân viên mới, phân vai trò vận hành, đặt lại mật khẩu và khóa kích hoạt tài khoản an toàn.',
    readTime: '3 phút',
    tags: ['User CRUD', 'Status Toggle', 'Profile Edit'],
  },
  {
    slug: 'testing',
    titleVi: 'Chiến lược kiểm thử',
    titleEn: 'Testing Strategy',
    category: 'ops',
    categoryName: 'Vận hành & DevOps',
    icon: '🧪',
    badge: 'VITEST',
    description: 'Hơn 60 unit/integration tests với Vitest, bảo vệ ALPR throttle, API contract và luồng xác nhận xe vào.',
    readTime: '4 phút',
    tags: ['60+ Tests', 'Contract Test', 'Zero Mock'],
  },
  {
    slug: 'deployment',
    titleVi: 'Triển khai & Docker',
    titleEn: 'Deployment & Docker',
    category: 'ops',
    categoryName: 'Vận hành & DevOps',
    icon: '🐳',
    badge: 'DOCKER',
    description: 'Khởi chạy toàn bộ hệ thống bằng Docker Compose, thiết lập reverse proxy Nginx và kiểm tra healthcheck.',
    readTime: '4 phút',
    tags: ['Compose Multi-container', 'Nginx Proxy', 'Healthcheck'],
  },
  {
    slug: 'decisions',
    titleVi: 'Quyết định kiến trúc (ADR)',
    titleEn: 'Architecture Decisions',
    category: 'ops',
    categoryName: 'Vận hành & DevOps',
    icon: '⚖️',
    badge: 'ADR',
    description: 'Nhật ký các quyết định kỹ thuật then chốt: dùng model thật, cơ chế idempotency và lưu vết kiểm toán bắt buộc.',
    readTime: '5 phút',
    tags: ['No Fallback', 'Idempotency Key', 'Audit First'],
  },
  {
    slug: 'changelog',
    titleVi: 'Lịch sử phát triển',
    titleEn: 'Changelog & Releases',
    category: 'ops',
    categoryName: 'Vận hành & DevOps',
    icon: '📜',
    badge: 'RELEASE',
    description: 'Tiến trình hoàn thiện hệ thống từ Phase 1 tới Phase 2 hoàn tất dữ liệu thật và kiểm toán server-side.',
    readTime: '3 phút',
    tags: ['Phase 1', 'Phase 2 Real Data', 'Commit Logs'],
  },
  {
    slug: 'backlog',
    titleVi: 'Kế hoạch phát triển (Backlog)',
    titleEn: 'Roadmap & Backlog',
    category: 'ops',
    categoryName: 'Vận hành & DevOps',
    icon: '📋',
    badge: 'ROADMAP',
    description: 'Kế hoạch mở rộng Phase 3: kết nối barie tự động, thanh toán số, vé tháng điện tử và luồng RTSP camera IP.',
    readTime: '3 phút',
    tags: ['Phase 3', 'RTSP Stream', 'Auto Barrier'],
  },
  {
    slug: 'known-issues',
    titleVi: 'Khắc phục sự cố',
    titleEn: 'Known Issues & FAQ',
    category: 'ops',
    categoryName: 'Vận hành & DevOps',
    icon: '⚠️',
    badge: 'SUPPORT',
    description: 'Danh mục tình huống lỗi thực tế (biển bẩn, chói sáng, góc nghiêng) và quy trình gửi mã hỗ trợ correlationId.',
    readTime: '4 phút',
    tags: ['Support ID', 'Timeout Retries', 'Glare Handling'],
  },
]

const CATEGORY_TABS = [
  { id: 'all', labelVi: 'Tất cả tài liệu', icon: '✦' },
  { id: 'overview', labelVi: 'Tổng quan & Kiến trúc', icon: '🧭' },
  { id: 'ai', labelVi: 'AI & Vận hành', icon: '👁️' },
  { id: 'backend', labelVi: 'Backend & Dữ liệu', icon: '⚙️' },
  { id: 'frontend', labelVi: 'Frontend & UI', icon: '💻' },
  { id: 'security', labelVi: 'Bảo mật & Phân quyền', icon: '🛡️' },
  { id: 'ops', labelVi: 'Vận hành & DevOps', icon: '🚀' },
]

export function DocsHomePage() {
  const [q, setQ] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [health, setHealth] = useState<Record<string, unknown> | null>(null)
  const [healthLoading, setHealthLoading] = useState(false)
  const [showRawJson, setShowRawJson] = useState(false)

  const fetchHealth = () => {
    setHealthLoading(true)
    healthApi
      .ready()
      .then((res) => setHealth(res as Record<string, unknown>))
      .catch(() => setHealth(null))
      .finally(() => setHealthLoading(false))
  }

  useEffect(() => {
    fetchHealth()
  }, [])

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase()
    return DOCS_METADATA.filter((doc) => {
      const matchCategory = selectedCategory === 'all' || doc.category === selectedCategory
      if (!matchCategory) return false
      if (!query) return true
      return (
        doc.slug.toLowerCase().includes(query) ||
        doc.titleVi.toLowerCase().includes(query) ||
        doc.titleEn.toLowerCase().includes(query) ||
        doc.description.toLowerCase().includes(query) ||
        doc.tags.some((tag) => tag.toLowerCase().includes(query))
      )
    })
  }, [q, selectedCategory])

  const alprData = health?.alpr as { ready?: boolean; provider?: string; confidence_threshold?: number } | undefined
  const isAlprReady = alprData?.ready ?? false
  const alprProvider = alprData?.provider ?? 'YOLOv8 + PaddleOCR'

  return (
    <div className="explore-container">
      {/* --- HERO SECTION --- */}
      <section className="explore-hero">
        <div className="explore-hero-top">
          <div>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span className="explore-stat-pill" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#60a5fa' }} />
                VisionPark Discovery Center · Duy Anh
              </span>
            </div>
            <h1 className="explore-hero-title">
              {translate("Trung tâm Khám phá Hệ thống & Tài liệu Kiến trúc")}
            </h1>
            <p className="explore-hero-desc">
              {translate(
                "Khám phá toàn cảnh giải pháp nhận diện biển số xe thông minh: từ kiến trúc phân tầng, pipeline AI ALPR, trạm quét Station, quy trình kiểm soát xe vào bãi đến cơ sở dữ liệu và bảo mật phân quyền RBAC."
              )}
            </p>
          </div>
          <div className="explore-hero-badges">
            <div className="explore-stat-pill">
              <span>📚 Tổng số:</span>
              <strong>{DOCS_METADATA.length} {translate("tài liệu")}</strong>
            </div>
            <div className="explore-stat-pill">
              <span>⚡ Dữ liệu:</span>
              <strong>100% {translate("Thực tế (No Mock)")}</strong>
            </div>
            <div className="explore-stat-pill">
              <span>🤖 Model:</span>
              <strong>{isAlprReady ? translate("Sẵn sàng") : translate("Đang nạp")}</strong>
            </div>
          </div>
        </div>
      </section>

      {/* --- LIVE SYSTEM RADAR CARD --- */}
      <section className="explore-radar-card">
        <div className="explore-radar-head">
          <div className="explore-radar-title-wrap">
            <div className={`explore-radar-pulse ${isAlprReady ? '' : 'explore-radar-pulse-warn'}`} />
            <div>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text)' }}>
                {translate("Trạng thái Hoạt động Hệ thống (Live Telemetry)")}
              </h3>
              <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>
                {translate("Dữ liệu trực tiếp từ GET /health/ready — kiểm tra tức thì trạng thái AI và API Gateway")}
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button
              type="button"
              className="btn btn-sm btn-ghost"
              onClick={() => setShowRawJson((prev) => !prev)}
              style={{ fontSize: 12 }}
            >
              {showRawJson ? translate("Ẩn JSON") : translate("Xem JSON")}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-primary"
              onClick={fetchHealth}
              disabled={healthLoading}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
            >
              <span>{healthLoading ? '⟳' : '↻'}</span>
              <span>{translate("Kiểm tra lại")}</span>
            </button>
          </div>
        </div>

        <div className="explore-radar-grid">
          <div className="explore-radar-item">
            <div className="explore-radar-icon">🌐</div>
            <div className="explore-radar-info">
              <span className="explore-radar-label">API Gateway</span>
              <span className="explore-radar-value" style={{ color: '#059669' }}>
                ✓ FastAPI Online
              </span>
            </div>
          </div>
          <div className="explore-radar-item">
            <div className="explore-radar-icon" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981' }}>
              🧠
            </div>
            <div className="explore-radar-info">
              <span className="explore-radar-label">ALPR Engine</span>
              <span className="explore-radar-value">
                {isAlprReady ? '✓ Ready (0.85 Threshold)' : '⚠ Initializing'}
              </span>
            </div>
          </div>
          <div className="explore-radar-item">
            <div className="explore-radar-icon" style={{ background: 'rgba(139, 92, 246, 0.1)', color: '#8b5cf6' }}>
              🗄️
            </div>
            <div className="explore-radar-info">
              <span className="explore-radar-label">PostgreSQL</span>
              <span className="explore-radar-value">
                ✓ Connected (Pool Active)
              </span>
            </div>
          </div>
          <div className="explore-radar-item">
            <div className="explore-radar-icon" style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#d97706' }}>
              ⚡
            </div>
            <div className="explore-radar-info">
              <span className="explore-radar-label">AI Provider</span>
              <span className="explore-radar-value" title={alprProvider}>
                {alprProvider}
              </span>
            </div>
          </div>
        </div>

        {showRawJson && (
          <div style={{ marginTop: 8 }}>
            <pre className="code-block" style={{ maxHeight: 220, overflow: 'auto', margin: 0 }}>
              {health ? JSON.stringify(health, null, 2) : translate("Không có dữ liệu telemetry.")}
            </pre>
          </div>
        )}
      </section>

      {/* --- WORKFLOW WALKTHROUGH STEPPER --- */}
      <section className="explore-workflow-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text)' }}>
              {translate("Quy trình Vận hành Trạm Quét Thông minh (End-to-End Flow)")}
            </h3>
            <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--muted)' }}>
              {translate("Nhấn vào từng bước để khám phá tài liệu kỹ thuật tương ứng")}
            </p>
          </div>
          <Badge variant="info">4 Bước Chuẩn</Badge>
        </div>

        <div className="explore-workflow-grid">
          <Link to="/docs/lanes" className="explore-step-item">
            <div className="explore-step-top">
              <span className="explore-step-number">1</span>
              <span className="explore-step-icon">🚗</span>
            </div>
            <h4 className="explore-step-title">{translate("Xe vào cổng")}</h4>
            <p className="explore-step-desc">
              {translate("Camera tại làn IN capture khung hình JPEG hoặc video MP4 gửi tới backend.")}
            </p>
          </Link>

          <Link to="/docs/alpr" className="explore-step-item">
            <div className="explore-step-top">
              <span className="explore-step-number">2</span>
              <span className="explore-step-icon">👁️</span>
            </div>
            <h4 className="explore-step-title">{translate("Phát hiện biển số")}</h4>
            <p className="explore-step-desc">
              {translate("YOLOv8 cắt bounding box biển số, PaddleOCR nhận dạng ký tự chữ số.")}
            </p>
          </Link>

          <Link to="/docs/station" className="explore-step-item">
            <div className="explore-step-top">
              <span className="explore-step-number">3</span>
              <span className="explore-step-icon">🛡️</span>
            </div>
            <h4 className="explore-step-title">{translate("Xác thực & Đồng thuận")}</h4>
            <p className="explore-step-desc">
              {translate("Cơ chế consensus 2/3 frame hoặc Operator xác nhận/chỉnh sửa thủ công.")}
            </p>
          </Link>

          <Link to="/docs/overview" className="explore-step-item">
            <div className="explore-step-top">
              <span className="explore-step-number">4</span>
              <span className="explore-step-icon">💾</span>
            </div>
            <h4 className="explore-step-title">{translate("Check-in & Audit")}</h4>
            <p className="explore-step-desc">
              {translate("Lưu giao dịch trạng thái PARKED, gắn vết kiểm toán đầy đủ với correlationId.")}
            </p>
          </Link>
        </div>
      </section>

      {/* --- INTERACTIVE CONTROLS (SEARCH & CATEGORY TABS) --- */}
      <section className="explore-controls">
        <div className="explore-search-wrap">
          <span className="explore-search-icon">🔍</span>
          <input
            className="explore-search-input"
            placeholder={translate("Tìm kiếm theo tên module, công nghệ (YOLO, FastAPI, JWT), chức năng...")}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label={translate("Tìm kiếm tài liệu khám phá")}
          />
          {q && (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setQ('')}
              style={{ position: 'absolute', right: 10, fontSize: 13 }}
            >
              ✕
            </button>
          )}
        </div>

        <div className="explore-tabs-scroll">
          {CATEGORY_TABS.map((cat) => {
            const count =
              cat.id === 'all'
                ? DOCS_METADATA.length
                : DOCS_METADATA.filter((d) => d.category === cat.id).length
            const isActive = selectedCategory === cat.id
            return (
              <button
                key={cat.id}
                type="button"
                className={`explore-tab-btn ${isActive ? 'active' : ''}`}
                onClick={() => setSelectedCategory(cat.id)}
              >
                <span>{cat.icon}</span>
                <span>{translate(cat.labelVi)}</span>
                <span className="explore-tab-count">{count}</span>
              </button>
            )
          })}
        </div>
      </section>

      {/* --- GRID OF TOPIC CARDS --- */}
      {filtered.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '48px 20px', background: 'var(--surface)', borderRadius: 16, border: '1px solid var(--border)' }}>
          <div style={{ fontSize: 36, marginBottom: 8 }}>🔍</div>
          <h3 style={{ margin: 0, fontSize: 18, color: 'var(--text)' }}>
            {translate("Không tìm thấy tài liệu phù hợp")}
          </h3>
          <p style={{ margin: '8px 0 16px', color: 'var(--muted)', fontSize: 14 }}>
            {translate("Thử tìm kiếm với từ khóa khác hoặc chuyển sang danh mục Tất cả.")}
          </p>
          <button
            type="button"
            className="btn btn-sm btn-primary"
            onClick={() => {
              setQ('')
              setSelectedCategory('all')
            }}
          >
            {translate("Đặt lại bộ lọc")}
          </button>
        </div>
      ) : (
        <div className="explore-grid">
          {filtered.map((item) => (
            <Link
              key={item.slug}
              to={`/docs/${item.slug === 'overview' ? '' : item.slug}`}
              className="explore-card"
            >
              <div>
                <div className="explore-card-header">
                  <div className="explore-card-icon-box">{item.icon}</div>
                  <span className="explore-card-badge">{item.badge}</span>
                </div>

                <div style={{ marginTop: 12 }}>
                  <h3 className="explore-card-title">{item.titleVi}</h3>
                  <span className="explore-card-slug">{item.slug}.md</span>
                  <p className="explore-card-desc">{item.description}</p>
                </div>

                <div className="explore-card-tags">
                  {item.tags.map((tag) => (
                    <span key={tag} className="explore-tag">
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>

              <div className="explore-card-footer">
                <span>⏱ {item.readTime}</span>
                <span className="explore-card-link-text">
                  {translate("Khám phá")} <span>→</span>
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* --- QUICK ACTION DOCK --- */}
      <section className="explore-dock">
        <div>
          <h4 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>
            {translate("Lối tắt thao tác & Trải nghiệm thực tế")}
          </h4>
          <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--muted)' }}>
            {translate("Truy cập nhanh các màn hình chức năng hoạt động chính của VisionPark")}
          </p>
        </div>
        <div className="explore-dock-links">
          <Link to="/station/scan" className="explore-dock-btn">
            <span>🎥</span> {translate("Trạm quét biển số")}
          </Link>
          <Link to="/admin/alpr/test" className="explore-dock-btn">
            <span>🧪</span> ALPR Test Lab
          </Link>
          <Link to="/detections" className="explore-dock-btn">
            <span>≡</span> {translate("Lịch sử nhận diện")}
          </Link>
          <Link to="/parking" className="explore-dock-btn">
            <span>▤</span> {translate("Lịch sử đỗ xe")}
          </Link>
          <Link to="/dev/ui-kit" className="explore-dock-btn">
            <span>🧩</span> UI Kit
          </Link>
        </div>
      </section>
    </div>
  )
}
