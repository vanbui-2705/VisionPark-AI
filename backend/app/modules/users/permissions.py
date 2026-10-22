"""Phase 3 business permissions. Domain routers reuse require_permissions."""

from app.modules.users.schemas import RoleName

ROLE_PERMISSIONS = {
    RoleName.SYSTEM_ADMIN: frozenset(
        {"manage_buildings", "manage_users", "view_revenue", "view_settings", "copy_settings"}
    ),
    RoleName.BUILDING_ADMIN: frozenset(
        {
            "manage_users",
            "view_settings",
            "manage_settings",
            "manage_pricing",
            "manage_incident",
            "override_barrier",
            "view_revenue",
        }
    ),
    RoleName.OPERATOR: frozenset({"view_settings", "override_barrier"}),
    RoleName.ACCOUNTANT: frozenset({"view_settings", "view_revenue"}),
}


def has_permission(user, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.role.name, frozenset())
