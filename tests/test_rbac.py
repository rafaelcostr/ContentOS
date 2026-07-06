"""Tier A5 + C2 — RBAC helpers."""

from contentos_database.models import User, UserRole
from contentos_gateway.api.deps import has_min_role, has_role
from contentos_gateway.services.org_service import ROLE_RANK, effective_role, member_has_min_role


def _user(role: UserRole) -> User:
    return User(email=f"{role.value}@test.dev", hashed_password="x", role=role)


class _Member:
    def __init__(self, role: UserRole):
        self.role = role


def test_role_rank_order():
    assert ROLE_RANK["admin"] > ROLE_RANK["editor"] > ROLE_RANK["viewer"]


def test_has_role_exact():
    admin = _user(UserRole.ADMIN)
    assert has_role(admin, "admin")
    assert not has_role(admin, "viewer")


def test_has_min_role_hierarchy():
    viewer = _user(UserRole.VIEWER)
    editor = _user(UserRole.EDITOR)
    admin = _user(UserRole.ADMIN)

    assert has_min_role(viewer, "viewer")
    assert not has_min_role(viewer, "editor")
    assert has_min_role(editor, "viewer")
    assert has_min_role(editor, "editor")
    assert not has_min_role(editor, "admin")
    assert has_min_role(admin, "editor")
    assert has_min_role(admin, "admin")


def test_org_membership_overrides_global_role():
    """C2: viewer in org cannot use global editor for org mutations."""
    global_editor = _user(UserRole.EDITOR)
    viewer_member = _Member(UserRole.VIEWER)

    assert effective_role(global_editor, viewer_member) == "viewer"
    assert not member_has_min_role(viewer_member, global_editor, "editor")
    assert not has_min_role(global_editor, "editor", viewer_member)


def test_org_admin_beats_global_viewer():
    global_viewer = _user(UserRole.VIEWER)
    admin_member = _Member(UserRole.ADMIN)

    assert member_has_min_role(admin_member, global_viewer, "admin")
    assert has_min_role(global_viewer, "editor", admin_member)
