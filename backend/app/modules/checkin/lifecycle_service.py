from uuid import UUID

from sqlalchemy.orm import Session

from .lifecycle_models import ActorType, LifecycleEvent, LifecycleEventType


def record_lifecycle_event(
    session: Session,
    session_id: UUID,
    event_type: LifecycleEventType | str,
    actor_type: ActorType | str = ActorType.SYSTEM,
    actor_id: UUID | None = None,
    lane_id: UUID | None = None,
    building_id: UUID | None = None,
    details: dict | None = None,
    image_ref: str | None = None,
) -> LifecycleEvent:
    """Record an append-only lifecycle event within the active transaction."""
    event = LifecycleEvent(
        session_id=session_id,
        building_id=building_id,
        event_type=str(event_type),
        actor_type=str(actor_type),
        actor_id=actor_id,
        lane_id=lane_id,
        details=details or {},
        image_ref=image_ref,
    )
    session.add(event)
    return event

