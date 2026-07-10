"""Growth hardening — OAuth audit, health, failure classification (Fase 18)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

OAuthAuditStatus = Literal["ok", "disconnected", "expired", "expiring_soon", "missing_refresh"]
FailureKind = Literal[
    "not_found",
    "validation",
    "oauth",
    "workflow_unreachable",
    "quota",
    "billing",
    "rate_limit",
    "internal",
]


@dataclass(frozen=True)
class OAuthChannelAudit:
    channel_id: str
    project_id: str
    platform: str
    channel_name: str
    status: OAuthAuditStatus
    oauth_connected: bool
    has_refresh_token: bool
    token_expires_at: str | None = None
    needs_reconnect: bool = False
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "project_id": self.project_id,
            "platform": self.platform,
            "channel_name": self.channel_name,
            "status": self.status,
            "oauth_connected": self.oauth_connected,
            "has_refresh_token": self.has_refresh_token,
            "token_expires_at": self.token_expires_at,
            "needs_reconnect": self.needs_reconnect,
            "detail": self.detail,
        }


@dataclass
class GrowthHealthReport:
    status: Literal["healthy", "degraded", "unhealthy"]
    checks: dict[str, bool] = field(default_factory=dict)
    summary: str = ""
    oauth_issues: int = 0
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checks": dict(self.checks),
            "summary": self.summary,
            "oauth_issues": self.oauth_issues,
            "generated_at": self.generated_at,
        }


@dataclass(frozen=True)
class GrowthFailure:
    kind: FailureKind
    message: str
    retryable: bool = False
    http_status: int = 400

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.kind,
            "message": self.message,
            "retryable": self.retryable,
        }


def _parse_expiry(expires_at: Any) -> datetime | None:
    if expires_at is None:
        return None
    try:
        if isinstance(expires_at, (int, float)):
            return datetime.fromtimestamp(float(expires_at), tz=timezone.utc)
        return datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def audit_channel_oauth(
    *,
    channel_id: str,
    project_id: str,
    platform: str,
    channel_name: str,
    credentials: dict[str, Any] | None,
    expiring_soon_hours: int = 48,
) -> OAuthChannelAudit:
    from contentos_database.channel_credentials import credentials_connected, token_expired

    creds = dict(credentials or {})
    connected = credentials_connected(creds)
    has_refresh = bool(creds.get("refresh_token"))
    expires_raw = creds.get("expires_at")
    expires_dt = _parse_expiry(expires_raw)
    expires_iso = expires_dt.isoformat() if expires_dt else None

    if not connected:
        return OAuthChannelAudit(
            channel_id=channel_id,
            project_id=project_id,
            platform=platform,
            channel_name=channel_name,
            status="disconnected",
            oauth_connected=False,
            has_refresh_token=has_refresh,
            token_expires_at=expires_iso,
            needs_reconnect=True,
            detail="Canal sem access_token — conecte OAuth em Publicação.",
        )

    if token_expired(creds):
        return OAuthChannelAudit(
            channel_id=channel_id,
            project_id=project_id,
            platform=platform,
            channel_name=channel_name,
            status="expired",
            oauth_connected=True,
            has_refresh_token=has_refresh,
            token_expires_at=expires_iso,
            needs_reconnect=not has_refresh,
            detail="Token expirado" + (" — refresh disponível" if has_refresh else " — reconecte OAuth"),
        )

    if expires_dt and expires_dt <= datetime.now(timezone.utc) + timedelta(hours=expiring_soon_hours):
        return OAuthChannelAudit(
            channel_id=channel_id,
            project_id=project_id,
            platform=platform,
            channel_name=channel_name,
            status="expiring_soon",
            oauth_connected=True,
            has_refresh_token=has_refresh,
            token_expires_at=expires_iso,
            needs_reconnect=False,
            detail=f"Token expira em breve ({expiring_soon_hours}h)",
        )

    if not has_refresh:
        return OAuthChannelAudit(
            channel_id=channel_id,
            project_id=project_id,
            platform=platform,
            channel_name=channel_name,
            status="missing_refresh",
            oauth_connected=True,
            has_refresh_token=False,
            token_expires_at=expires_iso,
            needs_reconnect=False,
            detail="Sem refresh_token — renovação automática pode falhar",
        )

    return OAuthChannelAudit(
        channel_id=channel_id,
        project_id=project_id,
        platform=platform,
        channel_name=channel_name,
        status="ok",
        oauth_connected=True,
        has_refresh_token=True,
        token_expires_at=expires_iso,
        needs_reconnect=False,
        detail="OAuth válido",
    )


def summarize_oauth_audit(rows: list[OAuthChannelAudit]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1
    needs_action = [row for row in rows if row.needs_reconnect or row.status in ("expired", "disconnected")]
    return {
        "total_channels": len(rows),
        "by_status": by_status,
        "needs_reconnect": len(needs_action),
        "channels": [row.to_dict() for row in rows],
    }


def build_growth_health(
    *,
    checks: dict[str, bool],
    oauth_audits: list[OAuthChannelAudit] | None = None,
) -> GrowthHealthReport:
    oauth_issues = 0
    if oauth_audits:
        oauth_issues = sum(1 for row in oauth_audits if row.status != "ok")

    failed = [name for name, ok in checks.items() if not ok]
    if not failed and oauth_issues == 0:
        status: Literal["healthy", "degraded", "unhealthy"] = "healthy"
        summary = "Growth OS operacional."
    elif "database" in failed or "workflow_engine" in failed:
        status = "unhealthy"
        summary = f"Dependências críticas indisponíveis: {', '.join(failed)}"
    else:
        status = "degraded"
        parts = []
        if failed:
            parts.append(f"checks: {', '.join(failed)}")
        if oauth_issues:
            parts.append(f"{oauth_issues} canal(is) com OAuth pendente")
        summary = " · ".join(parts) or "Degradado"

    return GrowthHealthReport(
        status=status,
        checks=dict(checks),
        summary=summary,
        oauth_issues=oauth_issues,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def classify_growth_error(exc: Exception) -> GrowthFailure:
    message = str(exc)
    lowered = message.lower()

    if "rate limit" in lowered or "too many" in lowered:
        return GrowthFailure(kind="rate_limit", message=message, retryable=True, http_status=429)
    if "quota" in lowered:
        return GrowthFailure(kind="quota", message=message, retryable=False, http_status=429)
    if "credit" in lowered or "billing" in lowered:
        return GrowthFailure(kind="billing", message=message, retryable=False, http_status=402)
    if "workflow" in lowered and ("unreachable" in lowered or "503" in lowered):
        return GrowthFailure(kind="workflow_unreachable", message=message, retryable=True, http_status=503)
    if "oauth" in lowered or "token" in lowered or "credentials" in lowered:
        return GrowthFailure(kind="oauth", message=message, retryable=False, http_status=400)
    if "not found" in lowered:
        return GrowthFailure(kind="not_found", message=message, retryable=False, http_status=404)
    if isinstance(exc, ValueError):
        return GrowthFailure(kind="validation", message=message, retryable=False, http_status=400)
    return GrowthFailure(kind="internal", message=message or "Erro interno Growth", retryable=True, http_status=500)
