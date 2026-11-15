# app/services/tenant_slug.py
# Single source of truth for turning a company name into a new tenant slug.
# Used by the public self-serve signup (app/api/auth.py) and the superadmin
# invite (app/api/admin_invite.py).

import re

from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.user import User

# Slugs no new tenant may ever be given.
#   "ryze" is the functional house-tenant slug: it gates the billing bypass,
#   the AI-budget exemption and superadmin access, and it has no `tenants`
#   row, so a collision check against `tenants` alone never sees it.
#   The rest are platform words kept free to avoid confusion.
RESERVED_SLUGS = frozenset({"ryze", "greenscene", "admin", "api", "platform"})

# Base used when a company name has no ASCII letters or digits. An empty slug
# must never be stored: every `tenant_id or "ryze"` fallback would treat it
# as the house tenant.
FALLBACK_BASE = "firm"


def normalize_slug_base(company_name: str) -> str:
    """Lower-case the name and collapse every run of non-alphanumerics to
    '_'. e.g. 'Acme Recruiting' -> 'acme_recruiting'. Never returns ''."""
    base = re.sub(r"[^a-z0-9]+", "_", (company_name or "").lower()).strip("_")
    return base or FALLBACK_BASE


def _is_taken(slug: str, db: Session) -> bool:
    """A slug is taken if it is reserved, has a `tenants` row, or is already
    the tenant_id of any user (legacy / house tenants have no `tenants` row)."""
    if slug in RESERVED_SLUGS:
        return True
    if db.query(Tenant.id).filter(Tenant.slug == slug).first():
        return True
    if db.query(User.id).filter(User.tenant_id == slug).first():
        return True
    return False


def generate_tenant_slug(company_name: str, db: Session) -> str:
    """Return an unused, non-reserved slug for a new tenant, appending a
    numeric suffix on collision ('acme' -> 'acme_1' -> 'acme_2')."""
    base = normalize_slug_base(company_name)
    slug = base
    attempt = 0
    while _is_taken(slug, db):
        attempt += 1
        slug = f"{base}_{attempt}"
    return slug
