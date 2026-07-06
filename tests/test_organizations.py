"""Tier C1 — Multi-tenant organizations."""

from contentos_database.models import UserRole
from contentos_database.org_seed import slugify
from contentos_gateway.services.org_service import effective_role, member_has_min_role


def test_slugify():
    assert slugify("Acme Corp!") == "acme-corp"
    assert slugify("  ") == "org"


def test_effective_role_prefers_membership():
    class User:
        role = UserRole.VIEWER

    class Member:
        role = UserRole.ADMIN

    assert effective_role(User(), Member()) == "admin"
    assert effective_role(User(), None) == "viewer"


def test_member_has_min_role():
    class User:
        role = UserRole.EDITOR

    class EditorMember:
        role = UserRole.EDITOR

    assert member_has_min_role(EditorMember(), User(), "editor") is True
    assert member_has_min_role(EditorMember(), User(), "admin") is False
