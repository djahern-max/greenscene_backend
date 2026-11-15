"""
tests/test_invite_gate.py

Deterministic, no-DB, no-network tier.

POST /api/admin/invite creates new tenants, so it is superadmin-only:
the caller must have is_superuser AND be on the house tenant (a NULL
tenant_id counts as the house tenant, as everywhere else).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api.admin_invite import InviteRequest, invite_firm, router
from app.core.deps import get_current_superuser

PAYLOAD = InviteRequest(
    company_name="Gate Test Co", full_name="Gate Test", email="gate@example.com"
)


def _user(is_superuser: bool, tenant_id):
    return SimpleNamespace(
        is_superuser=is_superuser, tenant_id=tenant_id, email="caller@example.com"
    )


def _db_where_email_already_exists():
    """A stand-in session whose duplicate-email lookup finds a user, so a
    caller who passes the gate stops at the 400 right after it — nothing is
    created and no email is sent."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = object()
    return db


def test_route_depends_on_get_current_superuser():
    route = next(r for r in router.routes if r.path == "/api/admin/invite")
    dependencies = {d.call for d in route.dependant.dependencies}
    assert get_current_superuser in dependencies


def test_dependency_rejects_a_non_superuser_admin():
    with pytest.raises(HTTPException) as exc:
        get_current_superuser(current_user=_user(False, "ryze"))
    assert exc.value.status_code == 403


def test_superuser_on_another_tenant_is_rejected():
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        invite_firm(PAYLOAD, db=db, current_user=_user(True, "some_other_firm"))
    assert exc.value.status_code == 403
    db.query.assert_not_called()


@pytest.mark.parametrize("tenant_id", ["ryze", None, ""])
def test_house_tenant_superuser_passes_the_gate(tenant_id):
    with pytest.raises(HTTPException) as exc:
        invite_firm(
            PAYLOAD,
            db=_db_where_email_already_exists(),
            current_user=_user(True, tenant_id),
        )
    # 400 = past the gate, stopped by the duplicate-email check.
    assert exc.value.status_code == 400
