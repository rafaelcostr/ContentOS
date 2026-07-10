"""Growth readiness checks for manual OAuth/publishing setup."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

from contentos_growth.platform_registry import list_growth_platforms

ReadinessStatus = Literal["ready", "missing", "manual", "warning", "not_supported"]
ReportStatus = Literal["ready", "manual_required", "blocked"]


@dataclass(frozen=True)
class GrowthReadinessCheck:
    key: str
    label: str
    status: ReadinessStatus
    detail: str
    required: bool = True
    variables: tuple[str, ...] = ()
    manual_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status,
            "detail": self.detail,
            "required": self.required,
            "variables": list(self.variables),
            "manual_action": self.manual_action,
        }


@dataclass(frozen=True)
class PlatformReadiness:
    platform: str
    label: str
    status: ReportStatus
    oauth_supported: bool
    analytics_supported: bool
    publish_supported: bool
    checks: list[GrowthReadinessCheck] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "label": self.label,
            "status": self.status,
            "oauth_supported": self.oauth_supported,
            "analytics_supported": self.analytics_supported,
            "publish_supported": self.publish_supported,
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(frozen=True)
class GrowthReadinessReport:
    status: ReportStatus
    summary: str
    generated_at: str
    totals: dict[str, int]
    global_checks: list[GrowthReadinessCheck]
    platforms: list[PlatformReadiness]
    next_steps: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "summary": self.summary,
            "generated_at": self.generated_at,
            "totals": dict(self.totals),
            "global_checks": [check.to_dict() for check in self.global_checks],
            "platforms": [platform.to_dict() for platform in self.platforms],
            "next_steps": list(self.next_steps),
        }


def _has_any(env: Mapping[str, str], names: tuple[str, ...]) -> bool:
    return any((env.get(name) or "").strip() for name in names)


def _credential_check(
    *,
    env: Mapping[str, str],
    key: str,
    label: str,
    variables: tuple[str, ...],
    detail_ready: str,
    detail_missing: str,
) -> GrowthReadinessCheck:
    ready = _has_any(env, variables)
    return GrowthReadinessCheck(
        key=key,
        label=label,
        status="ready" if ready else "missing",
        detail=detail_ready if ready else detail_missing,
        required=True,
        variables=variables,
    )


def _manual_check(key: str, label: str, detail: str, manual_action: str) -> GrowthReadinessCheck:
    return GrowthReadinessCheck(
        key=key,
        label=label,
        status="manual",
        detail=detail,
        required=True,
        manual_action=manual_action,
    )


def _platform_status(checks: list[GrowthReadinessCheck]) -> ReportStatus:
    if any(check.status == "missing" and check.required for check in checks):
        return "blocked"
    if any(check.status in ("manual", "warning") for check in checks):
        return "manual_required"
    return "ready"


def _platform_checks(platform: str, env: Mapping[str, str]) -> list[GrowthReadinessCheck]:
    if platform == "youtube":
        return [
            _credential_check(
                env=env,
                key="youtube_client_id",
                label="YouTube Client ID",
                variables=("YOUTUBE_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_ID"),
                detail_ready="Client ID encontrado para OAuth do YouTube.",
                detail_missing="Informe YOUTUBE_CLIENT_ID ou GOOGLE_OAUTH_CLIENT_ID.",
            ),
            _credential_check(
                env=env,
                key="youtube_client_secret",
                label="YouTube Client Secret",
                variables=("YOUTUBE_CLIENT_SECRET", "GOOGLE_OAUTH_CLIENT_SECRET"),
                detail_ready="Client Secret encontrado para OAuth do YouTube.",
                detail_missing="Informe YOUTUBE_CLIENT_SECRET ou GOOGLE_OAUTH_CLIENT_SECRET.",
            ),
            _manual_check(
                key="youtube_console",
                label="Google Cloud Console",
                detail="O ContentOS não consegue habilitar APIs nem aprovar consent screen automaticamente.",
                manual_action=(
                    "Habilite YouTube Data API v3, YouTube Analytics API, configure OAuth consent screen "
                    "e cadastre a redirect URI do ContentOS."
                ),
            ),
        ]

    if platform == "tiktok":
        return [
            _credential_check(
                env=env,
                key="tiktok_client_key",
                label="TikTok Client Key",
                variables=("TIKTOK_CLIENT_KEY", "TIKTOK_OAUTH_CLIENT_KEY"),
                detail_ready="Client Key encontrado para OAuth do TikTok.",
                detail_missing="Informe TIKTOK_CLIENT_KEY ou TIKTOK_OAUTH_CLIENT_KEY.",
            ),
            _credential_check(
                env=env,
                key="tiktok_client_secret",
                label="TikTok Client Secret",
                variables=("TIKTOK_CLIENT_SECRET", "TIKTOK_OAUTH_CLIENT_SECRET"),
                detail_ready="Client Secret encontrado para OAuth do TikTok.",
                detail_missing="Informe TIKTOK_CLIENT_SECRET ou TIKTOK_OAUTH_CLIENT_SECRET.",
            ),
            _manual_check(
                key="tiktok_review",
                label="TikTok Developer App",
                detail="O TikTok exige app, permissão e revisão para publicação real.",
                manual_action="Configure Login Kit/Content Posting API, adicione redirect URI e solicite as permissões.",
            ),
        ]

    if platform == "instagram":
        return [
            _credential_check(
                env=env,
                key="meta_app_id",
                label="Meta App ID",
                variables=("META_APP_ID", "INSTAGRAM_APP_ID"),
                detail_ready="App ID encontrado para OAuth do Instagram/Meta.",
                detail_missing="Informe META_APP_ID ou INSTAGRAM_APP_ID.",
            ),
            _credential_check(
                env=env,
                key="meta_app_secret",
                label="Meta App Secret",
                variables=("META_APP_SECRET", "INSTAGRAM_APP_SECRET"),
                detail_ready="App Secret encontrado para OAuth do Instagram/Meta.",
                detail_missing="Informe META_APP_SECRET ou INSTAGRAM_APP_SECRET.",
            ),
            _manual_check(
                key="instagram_business",
                label="Conta profissional Meta",
                detail="A publicação via Instagram exige conta profissional vinculada a uma página Facebook.",
                manual_action=(
                    "Vincule Instagram Business/Creator a uma página Facebook e aprove instagram_content_publish, "
                    "insights e permissões de página."
                ),
            ),
        ]

    return [
        GrowthReadinessCheck(
            key=f"{platform}_not_supported",
            label="Publicação automática",
            status="not_supported",
            detail="Esta plataforma está no Growth como planejamento/análise, mas ainda não tem OAuth/publicação real.",
            required=False,
            manual_action="Use como canal de estratégia até implementar o conector oficial.",
        )
    ]


def build_growth_readiness(env: Mapping[str, str] | None = None) -> GrowthReadinessReport:
    env_map = env or os.environ
    publish_mode = (env_map.get("PUBLISH_MODE") or "dry_run").strip().lower()
    redirect_uri = (env_map.get("OAUTH_REDIRECT_URI") or "").strip()

    global_checks = [
        GrowthReadinessCheck(
            key="oauth_redirect_uri",
            label="OAuth Redirect URI",
            status="ready" if redirect_uri else "warning",
            detail=redirect_uri or "Sem OAUTH_REDIRECT_URI explícito; o sistema usa o fallback local.",
            required=False,
            variables=("OAUTH_REDIRECT_URI",),
            manual_action="Cadastre esta URI em cada console OAuth antes de conectar perfis reais.",
        ),
        GrowthReadinessCheck(
            key="publish_mode",
            label="Modo de publicação",
            status="ready" if publish_mode in {"prepare_only", "live"} else "warning",
            detail=f"PUBLISH_MODE={publish_mode}.",
            required=False,
            variables=("PUBLISH_MODE",),
            manual_action="Use dry_run para teste, prepare_only para preparar posts e live somente depois de validar OAuth/QA.",
        ),
        GrowthReadinessCheck(
            key="platform_analytics",
            label="Analytics por plataforma",
            status="ready" if (env_map.get("PLATFORM_ANALYTICS_ENABLED") or "true").lower() in {"1", "true", "yes"} else "warning",
            detail="PLATFORM_ANALYTICS_ENABLED controla scopes extras de analytics no OAuth.",
            required=False,
            variables=("PLATFORM_ANALYTICS_ENABLED",),
        ),
    ]

    platforms: list[PlatformReadiness] = []
    for profile in list_growth_platforms():
        checks = _platform_checks(profile.id, env_map)
        status = _platform_status(checks) if profile.oauth_supported else "manual_required"
        platforms.append(
            PlatformReadiness(
                platform=profile.id,
                label=profile.label,
                status=status,
                oauth_supported=profile.oauth_supported,
                analytics_supported=profile.analytics_supported,
                publish_supported=profile.publish_supported,
                checks=checks,
            )
        )

    all_checks = [*global_checks, *(check for platform in platforms for check in platform.checks)]
    totals = {
        "ready": sum(1 for check in all_checks if check.status == "ready"),
        "missing": sum(1 for check in all_checks if check.status == "missing"),
        "manual": sum(1 for check in all_checks if check.status == "manual"),
        "warning": sum(1 for check in all_checks if check.status == "warning"),
        "not_supported": sum(1 for check in all_checks if check.status == "not_supported"),
    }

    required_missing = [check for check in all_checks if check.status == "missing" and check.required]
    report_status: ReportStatus = "blocked" if required_missing else "manual_required"
    if not required_missing and totals["manual"] == 0 and totals["warning"] == 0:
        report_status = "ready"

    next_steps = []
    if required_missing:
        next_steps.append("Preencha as credenciais OAuth faltantes no .env antes de conectar perfis reais.")
    next_steps.append("Cadastre OAUTH_REDIRECT_URI nos consoles Google, TikTok e Meta.")
    next_steps.append("Conecte os canais pela tela de Canais/Publicação e rode /growth/oauth-audit por projeto.")
    next_steps.append("Mantenha PUBLISH_MODE=dry_run até validar um post preparado; depois use prepare_only e por último live.")

    return GrowthReadinessReport(
        status=report_status,
        summary=(
            "Growth bloqueado por credenciais OAuth faltantes."
            if report_status == "blocked"
            else "Growth pronto para a etapa manual de conexão/aprovação das plataformas."
        ),
        generated_at=datetime.now(timezone.utc).isoformat(),
        totals=totals,
        global_checks=global_checks,
        platforms=platforms,
        next_steps=next_steps,
    )
