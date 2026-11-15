"""
tests/test_tenant_slug.py

Deterministic, no-LLM tier — no external API calls.

Guards the new-tenant slug generator (app.services.tenant_slug) shared by
POST /api/auth/signup-firm and POST /api/admin/invite:

  1. No company name can produce the functional house slug `ryze`, or any
     other reserved slug, or an empty slug (which every
     `tenant_id or "ryze"` fallback would treat as `ryze`).
  2. A slug already used as a `users.tenant_id` is taken even when no
     `tenants` row has it.
  3. Both endpoints actually use the shared generator.

Like test_signup_tenant_resolution.py, this file defines its own `db`
fixture (shadowing conftest.py's read-only one): rows are added + flushed
but never committed, and always rolled back in teardown.
"""

from __future__ import annotations

import inspect
import uuid

import pytest

from app.core.database import SessionLocal
from app.core.deps import RYZE_TENANT

# Imported (unused directly) so SQLAlchemy can resolve FK targets on insert.
from app.models.booking import Booking  # noqa: F401
from app.models.candidate import Candidate  # noqa: F401
from app.models.employer_profile import EmployerProfile  # noqa: F401
from app.models.tenant import Tenant
from app.models.user import User, UserType
from app.services.tenant_slug import (
    FALLBACK_BASE,
    RESERVED_SLUGS,
    generate_tenant_slug,
)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _unique_base() -> str:
    return f"slugtest_{uuid.uuid4().hex[:12]}"


# --------------------------------------------------------------------------
# 1. The house slug can never be produced
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "company_name",
    ["Ryze", "RYZE!", " ryze ", "R.Y.Z.E", "ryze", "Ryze_", "--RyZe--", "\tRYZE\n"],
)
def test_company_name_never_yields_ryze(db, company_name):
    slug = generate_tenant_slug(company_name, db)
    assert slug != RYZE_TENANT
    assert slug not in RESERVED_SLUGS
    assert slug  # never empty


def test_ryze_gets_a_numeric_suffix(db):
    slug = generate_tenant_slug("Ryze", db)
    assert slug.startswith("ryze_")
    assert slug[len("ryze_"):].isdigit()


def test_reserved_list_contains_the_agreed_words():
    assert RESERVED_SLUGS == {"ryze", "greenscene", "admin", "api", "platform"}


@pytest.mark.parametrize("reserved", sorted(RESERVED_SLUGS))
def test_reserved_words_are_never_returned(db, reserved):
    slug = generate_tenant_slug(reserved.upper(), db)
    assert slug not in RESERVED_SLUGS
    assert slug.startswith(f"{reserved}_")


# --------------------------------------------------------------------------
# Empty slug — a name with no ASCII letters or digits
# --------------------------------------------------------------------------
@pytest.mark.parametrize("company_name", ["", "   ", "!!!", "___", "Ｒｙｚｅ", "日本"])
def test_name_without_alphanumerics_never_yields_empty_slug(db, company_name):
    slug = generate_tenant_slug(company_name, db)
    assert slug
    assert slug == FALLBACK_BASE or slug.startswith(f"{FALLBACK_BASE}_")
    assert slug not in RESERVED_SLUGS


# --------------------------------------------------------------------------
# 2. Collisions: users.tenant_id counts, not just tenants.slug
# --------------------------------------------------------------------------
def test_slug_present_only_in_users_is_taken(db):
    base = _unique_base()
    assert db.query(Tenant).filter(Tenant.slug == base).first() is None
    db.add(
        User(
            email=f"{uuid.uuid4().hex}@example.com",
            user_type=UserType.ADMIN,
            tenant_id=base,
        )
    )
    db.flush()

    assert generate_tenant_slug(base, db) == f"{base}_1"


def test_slug_present_in_tenants_is_taken(db):
    base = _unique_base()
    db.add(Tenant(slug=base, company_name="Slug Test", status="trial"))
    db.flush()

    assert generate_tenant_slug(base, db) == f"{base}_1"


def test_suffix_skips_taken_suffixes(db):
    base = _unique_base()
    db.add(Tenant(slug=base, company_name="Slug Test", status="trial"))
    db.add(
        User(
            email=f"{uuid.uuid4().hex}@example.com",
            user_type=UserType.ADMIN,
            tenant_id=f"{base}_1",
        )
    )
    db.flush()

    assert generate_tenant_slug(base, db) == f"{base}_2"


def test_unused_name_is_unchanged(db):
    base = _unique_base()
    assert generate_tenant_slug(f"  {base.upper()}!  ", db) == base


# --------------------------------------------------------------------------
# 3. Both endpoints use the shared generator (no private copies)
# --------------------------------------------------------------------------
def test_both_endpoints_use_the_shared_generator():
    import app.api.admin_invite as admin_invite
    import app.api.auth as auth

    for module, endpoint in ((auth, auth.signup_firm), (admin_invite, admin_invite.invite_firm)):
        assert module.generate_tenant_slug is generate_tenant_slug
        assert "generate_tenant_slug(" in inspect.getsource(endpoint)
        assert not hasattr(module, "_generate_firm_slug")
        assert not hasattr(module, "_generate_slug")
