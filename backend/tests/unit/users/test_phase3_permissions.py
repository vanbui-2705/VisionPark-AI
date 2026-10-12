from types import SimpleNamespace

import pytest

from app.modules.users.permissions import has_permission


@pytest.mark.parametrize(
    "role,granted",
    [
        ("SYSTEM_ADMIN", {"view_revenue", "copy_settings"}),
        (
            "BUILDING_ADMIN",
            {"override_barrier", "manage_incident", "view_revenue", "manage_pricing"},
        ),
        ("OPERATOR", {"override_barrier"}),
        ("ACCOUNTANT", {"view_revenue"}),
    ],
)
def test_document_business_permission_matrix(role, granted):
    user = SimpleNamespace(role=SimpleNamespace(name=role))
    for permission in {
        "override_barrier",
        "manage_incident",
        "view_revenue",
        "manage_pricing",
        "copy_settings",
    }:
        assert has_permission(user, permission) == (permission in granted)
