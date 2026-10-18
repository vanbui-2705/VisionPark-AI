"""Alembic model import registry.

Domain owners add their model imports here so Alembic can discover metadata without placing
business models inside the database package.
"""

from app.modules.alpr.models import Detection
from app.modules.audit_logs.models import AuditLog
from app.modules.buildings.models import Building, ParkingLot, UserBuilding
from app.modules.checkin.models import ParkingTransaction
from app.modules.lanes.models import Lane
from app.modules.pricing.models import (
    ClassQuota,
    CustomerClass,
    GuestInvite,
    Invoice,
    Payment,
    PricingRule,
    PricingVersion,
    Subscription,
    TicketProduct,
    Vehicle,
)
from app.modules.users.models import Role, User

__all__ = [
    "Role",
    "User",
    "Lane",
    "Detection",
    "AuditLog",
    "ParkingTransaction",
    "Building",
    "ParkingLot",
    "UserBuilding",
    "CustomerClass",
    "ClassQuota",
    "TicketProduct",
    "PricingVersion",
    "PricingRule",
    "Vehicle",
    "Subscription",
    "GuestInvite",
    "Invoice",
    "Payment",
]

from app.modules.m5.models import DailyStat, Device  # noqa: F401
from app.modules.operations.models import ErrorEvent, Notification, UserPreference  # noqa: F401
