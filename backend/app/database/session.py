from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.readiness import ReadinessStatus
from app.database.tenant import TenantSession


class DatabaseManager:
    """Quản lý SQLAlchemy engine và bộ tạo session dùng cho từng request."""

    def __init__(self) -> None:
        """Khởi tạo trình quản lý ở trạng thái chưa kết nối database."""

        self.engine: Engine | None = None
        self.session_factory: sessionmaker[Session] | None = None

    def configure(self, database_url: str, *, echo: bool = False) -> None:
        """Tạo engine và cấu hình bộ sinh session từ URL kết nối database."""

        if self.engine is not None:
            self.engine.dispose()
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine = create_engine(
            database_url,
            echo=echo,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            class_=TenantSession,
        )

    def create_session(self) -> Session:
        """Tạo một session mới hoặc báo lỗi nếu database chưa được cấu hình."""

        if self.session_factory is None:
            raise RuntimeError("Database has not been configured")
        return self.session_factory()

    def check_readiness(self) -> ReadinessStatus:
        """Chạy truy vấn đơn giản để kiểm tra database có sẵn sàng hay không."""

        if self.engine is None:
            return ReadinessStatus(False, "Database has not been configured.")
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return ReadinessStatus(True, "Database connection is ready.")
        except Exception:
            return ReadinessStatus(False, "Database connection failed.")

    def dispose(self) -> None:
        """Đóng connection pool và đưa trình quản lý về trạng thái chưa cấu hình."""

        if self.engine is not None:
            self.engine.dispose()
        self.engine = None
        self.session_factory = None


database = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """Cấp một session cho mỗi request, rollback khi lỗi và luôn đóng session."""

    session = database.create_session()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_database_readiness() -> ReadinessStatus:
    """Trả về trạng thái sẵn sàng của kết nối database cho health check."""

    return database.check_readiness()
