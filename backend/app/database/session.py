from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.readiness import ReadinessStatus
from app.database.tenant import TenantSession


class DatabaseManager:
    """Own the SQLAlchemy engine and request-scoped session factory."""

    def __init__(self) -> None:
        self.engine: Engine | None = None
        self.session_factory: sessionmaker[Session] | None = None

    def configure(self, database_url: str, *, echo: bool = False) -> None:
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
        if self.session_factory is None:
            raise RuntimeError("Database has not been configured")
        return self.session_factory()

    def check_readiness(self) -> ReadinessStatus:
        if self.engine is None:
            return ReadinessStatus(False, "Database has not been configured.")
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return ReadinessStatus(True, "Database connection is ready.")
        except Exception:
            return ReadinessStatus(False, "Database connection failed.")

    def dispose(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
        self.engine = None
        self.session_factory = None


database = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """Provide one SQLAlchemy session per request and always close it."""

    session = database.create_session()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_database_readiness() -> ReadinessStatus:
    return database.check_readiness()
