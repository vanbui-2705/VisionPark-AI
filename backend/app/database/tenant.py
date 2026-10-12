"""Server-resolved tenancy for the shared request session (VAN-60)."""

from uuid import UUID

from sqlalchemy import event, select
from sqlalchemy.orm import Session, attributes, with_loader_criteria
from sqlalchemy.sql.elements import TextClause

from app.core.errors import AppError
from app.modules.buildings.models import Building, BuildingOwnedMixin, ParkingLot, UserBuilding
from app.modules.users.models import User


def forbidden_scope():
    return AppError(
        status_code=403,
        code="BUILDING_ACCESS_DENIED",
        message="The account has no access to this building.",
    )


def resolve_building(session: Session, user: User, claim: str | None = None) -> UUID | None:
    if user.role.name == "SYSTEM_ADMIN":
        return None
    statement = (
        select(UserBuilding.building_id)
        .join(Building)
        .where(UserBuilding.user_id == user.id, Building.is_active.is_(True))
    )
    memberships = list(session.scalars(statement))
    if claim is not None:
        try:
            candidate = UUID(claim)
        except (ValueError, TypeError, AttributeError) as exc:
            raise forbidden_scope() from exc
        if candidate not in memberships:
            raise forbidden_scope()
        return candidate
    if len(memberships) != 1:
        raise AppError(
            status_code=403,
            code="BUILDING_REQUIRED",
            message="The account must have one active building assigned before login.",
        )
    return memberships[0]


class TenantSession(Session):
    """All application repositories use this session; no per-module engine is needed."""

    def get(self, entity, ident, **kwargs):
        # Session.get may return a cached object without triggering a SELECT event.
        value = super().get(entity, ident, **kwargs)
        building_id = self.info.get("building_id")
        if value is not None and building_id is not None:
            if isinstance(value, BuildingOwnedMixin) and value.building_id != building_id:
                return None
            if isinstance(value, Building) and value.id != building_id:
                return None
            if isinstance(value, ParkingLot | UserBuilding) and value.building_id != building_id:
                return None
            if isinstance(value, User) and not self.scalar(
                select(UserBuilding.id).where(
                    UserBuilding.user_id == value.id,
                    UserBuilding.building_id == building_id,
                )
            ):
                return None
        return value


@event.listens_for(TenantSession, "do_orm_execute")
def filter_building(execution):
    building_id = execution.session.info.get("building_id")
    if building_id is None:
        return
    if isinstance(execution.statement, TextClause) or not execution.is_orm_statement:
        raise AppError(
            status_code=403,
            code="UNSCOPED_QUERY",
            message="Use the shared ORM repository for building-owned data.",
        )
    # Preserve atomic token revocation; every other bulk mutation must use the unit of work.
    mapper = execution.bind_arguments.get("mapper")
    values = getattr(execution.statement, "_values", None) or {}
    revocation = (
        execution.is_update
        and mapper is not None
        and mapper.class_ is User
        and {getattr(key, "key", key) for key in values} == {"token_version"}
    )
    if not execution.is_select and not revocation:
        raise AppError(
            status_code=403,
            code="UNSCOPED_WRITE",
            message="Persist building-owned changes through the shared unit of work.",
        )
    execution.statement = execution.statement.options(
        with_loader_criteria(
            BuildingOwnedMixin, lambda cls: cls.building_id == building_id, include_aliases=True
        ),
        with_loader_criteria(Building, Building.id == building_id, include_aliases=True),
        with_loader_criteria(
            ParkingLot, ParkingLot.building_id == building_id, include_aliases=True
        ),
        with_loader_criteria(
            UserBuilding, UserBuilding.building_id == building_id, include_aliases=True
        ),
        with_loader_criteria(
            User,
            User.id.in_(
                select(UserBuilding.user_id).where(UserBuilding.building_id == building_id)
            ),
            include_aliases=True,
        ),
    )


@event.listens_for(TenantSession, "before_flush")
def enforce_building_writes(session, _context, _instances):
    building_id = session.info.get("building_id")
    if building_id is None:
        return
    for obj in session.new | session.dirty | session.deleted:
        if isinstance(obj, BuildingOwnedMixin):
            if attributes.get_history(obj, "building_id").deleted:
                raise forbidden_scope()
            if obj in session.new and obj.building_id is None:
                obj.building_id = building_id
            if obj.building_id != building_id:
                raise forbidden_scope()
            # An owned row cannot point at a lane/detection from another building.
            for column in obj.__table__.columns:
                for foreign_key in column.foreign_keys:
                    target = foreign_key.column.table
                    reference = getattr(obj, column.key, None)
                    if reference is not None and "building_id" in target.c:
                        owner = session.connection().scalar(
                            select(target.c.building_id).where(foreign_key.column == reference)
                        )
                        if owner != building_id:
                            raise forbidden_scope()
        elif isinstance(obj, ParkingLot | UserBuilding) and obj.building_id != building_id:
            raise forbidden_scope()
        elif isinstance(obj, Building) and obj.id != building_id:
            raise forbidden_scope()
