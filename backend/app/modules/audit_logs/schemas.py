from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: UUID
    time: datetime
    actor: str
    action: str
    resource: str
    resource_id: str
    before: object | None = None
    after: object | None = None
    correlation_id: str | None = None
    source: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedAuditResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    pageSize: int
    totalPages: int
