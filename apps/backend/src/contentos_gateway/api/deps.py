"""JWT authentication, API keys, and RBAC dependencies (Tier A5 + C2 + C5)."""

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from contentos_database.models import OrganizationApiKey, OrganizationMember, User, UserRole
from contentos_database.session import get_session
from contentos_gateway.config import settings
from contentos_gateway.services.api_key_service import scope_to_role, validate_api_key
from contentos_gateway.services.org_service import (
    ORG_HEADER,
    ROLE_RANK,
    get_membership,
    member_has_min_role,
    resolve_org_id,
)
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

security = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"
API_KEY_HEADER = "X-API-Key"

_api_key_ctx: ContextVar[OrganizationApiKey | None] = ContextVar("api_key", default=None)


def get_request_api_key() -> OrganizationApiKey | None:
    return _api_key_ctx.get()


@dataclass
class OrgAuthContext:
    user: User
    org_id: UUID
    member: OrganizationMember | None
    effective_role: str


async def _authenticate_jwt(
    credentials: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id or payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_current_user_jwt_only(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_api_key: str | None = Header(None, alias=API_KEY_HEADER),
    db: AsyncSession = Depends(get_session),
) -> User:
    if x_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="JWT authentication required",
        )
    return await _authenticate_jwt(credentials, db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_api_key: str | None = Header(None, alias=API_KEY_HEADER),
    db: AsyncSession = Depends(get_session),
) -> User:
    if x_api_key:
        validated = await validate_api_key(db, x_api_key)
        _api_key_ctx.set(validated.record)
        return validated.user

    _api_key_ctx.set(None)
    if credentials:
        return await _authenticate_jwt(credentials, db)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def _resolve_active_org_id(
    db: AsyncSession,
    user: User,
    x_organization_id: str | None,
) -> UUID:
    api_key = get_request_api_key()
    if api_key:
        if x_organization_id:
            try:
                header_org = UUID(x_organization_id)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid organization id") from exc
            if header_org != api_key.organization_id:
                raise HTTPException(
                    status_code=403,
                    detail="API key is scoped to a different organization",
                )
        return api_key.organization_id
    return await resolve_org_id(db, user, x_organization_id)


async def get_org_auth_context(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    x_organization_id: str | None = Header(None, alias=ORG_HEADER),
) -> OrgAuthContext:
    api_key = get_request_api_key()
    org_id = await _resolve_active_org_id(db, user, x_organization_id)
    if api_key:
        role = scope_to_role(api_key.scope)
        return OrgAuthContext(user=user, org_id=org_id, member=None, effective_role=role)

    member = await get_membership(db, user.id, org_id)
    role = member.role.value if member else user.role.value
    return OrgAuthContext(user=user, org_id=org_id, member=member, effective_role=role)


def effective_role(user: User, member: OrganizationMember | None) -> str:
    if member:
        return member.role.value
    return user.role.value


def has_role(user: User, *roles: str, member: OrganizationMember | None = None) -> bool:
    return effective_role(user, member) in roles


def has_min_role(user: User, min_role: str, member: OrganizationMember | None = None) -> bool:
    role = effective_role(user, member)
    return ROLE_RANK.get(role, 0) >= ROLE_RANK.get(min_role, 99)


def _api_key_has_min_role(min_role: str) -> bool:
    api_key = get_request_api_key()
    if not api_key:
        return False
    role = scope_to_role(api_key.scope)
    return ROLE_RANK.get(role, 0) >= ROLE_RANK.get(min_role, 99)


def require_platform_admin():
    """Global platform admin — cache, plugins, model defaults (not org-scoped)."""

    async def checker(user: User = Depends(get_current_user)) -> User:
        if get_request_api_key():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API keys cannot access platform admin routes",
            )
        if user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform admin required",
            )
        return user

    return checker


def require_org_min_role(min_role: str):
    """Org-scoped role check via X-Organization-Id (membership role wins over global)."""

    async def checker(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_session),
        x_organization_id: str | None = Header(None, alias=ORG_HEADER),
    ) -> User:
        if get_request_api_key():
            if not _api_key_has_min_role(min_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions (requires {min_role} or higher)",
                )
            return user

        org_id = await resolve_org_id(db, user, x_organization_id)
        member = await get_membership(db, user.id, org_id)
        if not member_has_min_role(member, user, min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions (requires {min_role} or higher in organization)",
            )
        return user

    return checker


async def require_org_admin(
    org_id: UUID,
    user: User = Depends(get_current_user_jwt_only),
    db: AsyncSession = Depends(get_session),
) -> OrganizationMember:
    """Org admin for organization in path (used as Depends on routes with org_id param)."""
    member = await get_membership(db, user.id, org_id)
    if not member or member.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin required",
        )
    return member


def require_role(*roles: str):
    """Require an exact role match in the active organization."""

    async def checker(ctx: OrgAuthContext = Depends(get_org_auth_context)) -> User:
        if ctx.effective_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions (requires one of: {', '.join(roles)})",
            )
        return ctx.user

    return checker


def require_min_role(min_role: str):
    """Require at least this role in the active organization."""

    async def checker(ctx: OrgAuthContext = Depends(get_org_auth_context)) -> User:
        if ROLE_RANK.get(ctx.effective_role, 0) < ROLE_RANK.get(min_role, 99):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions (requires {min_role} or higher)",
            )
        return ctx.user

    return checker


def require_editor():
    """Editor or admin in the active organization."""
    return require_org_min_role(UserRole.EDITOR.value)


def require_admin():
    """Alias for platform admin (backward compatible with Tier A5 platform routes)."""
    return require_platform_admin()


# Annotated shortcuts for route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
JwtUser = Annotated[User, Depends(get_current_user_jwt_only)]
OrgContext = Annotated[OrgAuthContext, Depends(get_org_auth_context)]
EditorUser = Annotated[User, Depends(require_editor())]
AdminUser = Annotated[User, Depends(require_platform_admin())]
PlatformAdminUser = Annotated[User, Depends(require_platform_admin())]
