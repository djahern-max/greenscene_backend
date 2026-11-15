"""
The platform's default brand name is "Greenscene", and the functional house
slug `ryze` still resolves under that name.

The display name and the slug are different things: the slug gates billing,
the AI budget and row ownership and is not renamed (see the GUARDRAIL section
of CLAUDE.md). These tests pin both halves so a future rename of one cannot
silently drag the other along.

No database is needed: get_branding(None, ...) returns the defaults.
"""

import pytest

from app.services.branding import RYZE_TENANT, get_branding


def test_default_brand_name_is_greenscene():
    assert get_branding(None, None).brand_name == "Greenscene"


def test_ryze_slug_still_resolves_under_the_new_name():
    branding = get_branding(None, "ryze")
    assert branding.tenant_id == "ryze"
    assert branding.brand_name == "Greenscene"


def test_null_tenant_falls_back_to_the_ryze_slug():
    assert RYZE_TENANT == "ryze"
    assert get_branding(None, None).tenant_id == RYZE_TENANT


@pytest.mark.parametrize("tenant_id", ["ryze", None, "no_such_tenant"])
def test_default_from_line_carries_the_brand_name(tenant_id):
    assert get_branding(None, tenant_id).email_from_line.startswith("Greenscene <")
