"""Tier C2 — org-scoped RBAC."""

from contentos_database.models import UserRole
from contentos_gateway.services.org_service import effective_role, member_has_min_role


def test_org_membership_overrides_global():
    class User:
        role = UserRole.EDITOR

    class Member:
        role = UserRole.VIEWER

    assert effective_role(User(), Member()) == "viewer"
    assert member_has_min_role(Member(), User(), "editor") is False


def test_org_admin_elevates_global_viewer():
    class User:
        role = UserRole.VIEWER

    class Member:
        role = UserRole.ADMIN

    assert member_has_min_role(Member(), User(), "editor") is True
