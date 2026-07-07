"""Command Center alert builder — V5.5.1."""



from __future__ import annotations


def build_command_center_alerts(

    *,

    factory_pending_approval: int,

    community_drafts_pending: int,

    oauth_channels_connected: int,

    platform_snapshots: int,

    pipelines_running: int = 0,

) -> list[str]:

    alerts: list[str] = []

    if factory_pending_approval > 0:

        alerts.append(

            f"{factory_pending_approval} lote(s) aguardando aprovação de publicação — veja /factory"

        )

    if community_drafts_pending > 0:

        alerts.append(

            f"{community_drafts_pending} rascunho(s) de resposta na comunidade — veja /community"

        )

    if platform_snapshots == 0 and oauth_channels_connected > 0:

        alerts.append("OAuth conectado mas sem métricas — execute sync em /analytics")

    elif oauth_channels_connected == 0 and pipelines_running > 0:

        alerts.append("Pipelines em execução sem canais OAuth — conecte em /plugins")

    return alerts


def merge_command_center_alerts(operational: list[str], slo_alerts: list[str]) -> list[str]:
    """Merge operational + SLO alerts without duplicates."""
    seen: set[str] = set()
    merged: list[str] = []
    for msg in [*operational, *slo_alerts]:
        if msg not in seen:
            seen.add(msg)
            merged.append(msg)
    return merged

