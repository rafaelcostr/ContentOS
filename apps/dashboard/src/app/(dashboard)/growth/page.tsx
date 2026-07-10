"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { api, Project, type Video } from "@/lib/api";
import {
  CalendarDays,
  Hash,
  LineChart,
  Palette,
  ScrollText,
  Share2,
  Target,
  Users,
} from "lucide-react";

const GROWTH_NAV = [
  { href: "/channels", label: "Canais", icon: Share2 },
  { href: "/brand", label: "Brand", icon: Palette },
  { href: "/competitors", label: "Concorrentes", icon: Users },
  { href: "/strategy", label: "Estratégia", icon: CalendarDays },
  { href: "/calendar", label: "Calendário", icon: CalendarDays },
  { href: "/performance", label: "Performance", icon: LineChart },
  { href: "/recommendations", label: "Recomendações", icon: Hash },
  { href: "/history", label: "Histórico", icon: ScrollText },
] as const;

export default function GrowthPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: projects = [], error: projectsError } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });
  const { data: videos = [] } = useQuery({
    queryKey: ["videos"],
    queryFn: api.getVideos,
  });

  const projectOptions = useMemo(() => {
    if (projects.length) return projects;
    const seen = new Set<string>();
    return videos.reduce<Project[]>((options, video: Video) => {
      if (!video.project_id || seen.has(video.project_id)) return options;
      seen.add(video.project_id);
      options.push({
        id: video.project_id,
        name: video.title ? `Projeto de ${video.title}` : `Projeto ${video.project_id.slice(0, 8)}`,
        description: null,
        created_at: video.created_at,
      });
      return options;
    }, []);
  }, [projects, videos]);

  useEffect(() => {
    if (projectOptions.length && !projectId) setProjectId(projectOptions[0].id);
  }, [projectOptions, projectId]);

  const { data: report, isLoading } = useQuery({
    queryKey: ["growth-report", projectId],
    queryFn: () => api.getGrowthReport(projectId!),
    enabled: Boolean(projectId),
    refetchInterval: 60_000,
  });

  const { data: performance, isLoading: perfLoading } = useQuery({
    queryKey: ["growth-performance", projectId],
    queryFn: () => api.getGrowthPerformance(projectId!),
    enabled: Boolean(projectId),
  });

  const { data: health } = useQuery({
    queryKey: ["growth-health", projectId],
    queryFn: () => api.getGrowthHealth(projectId!),
    enabled: Boolean(projectId),
    refetchInterval: 120_000,
  });

  const { data: oauthAudit } = useQuery({
    queryKey: ["growth-oauth-audit", projectId],
    queryFn: () => api.getGrowthOAuthAudit(projectId!),
    enabled: Boolean(projectId),
  });

  const syncPerformanceMutation = useMutation({
    mutationFn: () => api.syncGrowthPerformance(projectId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["growth-performance", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-report", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-recommendations", projectId] });
    },
  });

  const metrics = [
    { label: "Growth Score", value: report ? `${report.score}/100` : "-" },
    { label: "Canais", value: report?.channels.length ?? 0 },
    { label: "Concorrentes", value: report?.competitors.length ?? 0 },
    { label: "Recomendações", value: report?.recommendations.length ?? 0 },
    { label: "Oportunidades", value: report?.opportunities?.length ?? 0 },
    { label: "Riscos", value: report?.risks?.length ?? 0 },
  ];

  return (
    <div className="p-8">
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Growth AI</h1>
          <p className="text-sm text-muted-foreground">
            Visão de canais, concorrentes, estratégia e recomendações de crescimento.
          </p>
        </div>
        <Button
          variant="outline"
          disabled={!projectId || syncPerformanceMutation.isPending}
          onClick={() => syncPerformanceMutation.mutate()}
        >
          {syncPerformanceMutation.isPending ? "Sincronizando..." : "Sync Performance Learning"}
        </Button>
      </header>

      <div className="mb-6">
        <label className="text-xs font-medium text-muted-foreground">Projeto</label>
        <select
          className="mt-1 block w-full max-w-md rounded-md border border-border bg-background px-3 py-2 text-sm"
          value={projectId ?? ""}
          onChange={(event) => setProjectId(event.target.value)}
        >
          {projectOptions.map((project: Project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
        {!projectOptions.length ? (
          <p className="mt-2 text-xs text-muted-foreground">Nenhum projeto encontrado para Growth AI.</p>
        ) : null}
        {projectsError ? (
          <p className="mt-2 text-xs text-amber-400">Projetos indisponíveis; usando vídeos gerados como fallback.</p>
        ) : null}
      </div>

      {health && (
        <div className="mb-6 rounded-lg border border-border bg-card/40 p-4 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p>
              Sistema:{" "}
              <span
                className={
                  health.status === "healthy"
                    ? "text-emerald-400"
                    : health.status === "degraded"
                      ? "text-amber-400"
                      : "text-destructive"
                }
              >
                {health.status}
              </span>
              {" · "}
              {health.summary}
            </p>
            {oauthAudit && oauthAudit.needs_reconnect > 0 && (
              <span className="text-xs text-amber-400">
                {oauthAudit.needs_reconnect} canal(is) precisam reconectar OAuth
              </span>
            )}
          </div>
        </div>
      )}

      <div className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Link
          href="/growth"
          className="flex items-center gap-3 rounded-lg border border-primary/40 bg-primary/10 p-4 text-sm font-medium text-primary"
        >
          <Target className="h-5 w-5 shrink-0" />
          Growth AI
        </Link>
        {GROWTH_NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className="flex items-center gap-3 rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground"
          >
            <Icon className="h-5 w-5 shrink-0" />
            {label}
          </Link>
        ))}
      </div>

      <div className="mb-8 grid gap-4 md:grid-cols-3 lg:grid-cols-6">
        {metrics.map((metric) => (
          <div key={metric.label} className="rounded-md border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground">{metric.label}</p>
            <p className="mt-1 text-2xl font-semibold">{metric.value}</p>
          </div>
        ))}
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando Growth AI...</p>}

      {report && (
        <div className="grid gap-8 lg:grid-cols-[1fr_1fr]">
          <section>
            <h2 className="mb-3 text-lg font-semibold">Resumo</h2>
            <p className="rounded-md border border-border bg-card p-4 text-sm text-muted-foreground">
              {report.summary}
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-lg font-semibold">Estratégia ativa</h2>
            <div className="rounded-md border border-border bg-card p-4">
              <p className="text-sm font-medium">{report.strategy?.positioning ?? "—"}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {(report.strategy?.goals ?? []).map((goal) => (
                  <span key={goal} className="rounded-md border border-border px-2 py-1 text-xs text-muted-foreground">
                    {goal}
                  </span>
                ))}
              </div>
            </div>
          </section>

          {!!report.channel_health?.length && (
            <section>
              <h2 className="mb-3 text-lg font-semibold">Saúde dos canais</h2>
              <div className="grid gap-2">
                {report.channel_health.map((item) => (
                  <div key={String(item.channel_id)} className="rounded-md border border-border bg-card p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{String(item.name)}</span>
                      <span className="text-xs text-muted-foreground">{String(item.status)}</span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Score {String(item.score)} · {String(item.platform)}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {!!report.opportunities?.length && (
            <section>
              <h2 className="mb-3 text-lg font-semibold">Oportunidades</h2>
              <ul className="space-y-2 rounded-md border border-border bg-card p-4 text-sm text-muted-foreground">
                {report.opportunities.map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
            </section>
          )}

          {!!report.risks?.length && (
            <section>
              <h2 className="mb-3 text-lg font-semibold">Riscos</h2>
              <ul className="space-y-2 rounded-md border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-amber-200/90">
                {report.risks.map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
            </section>
          )}

          {!!report.asset_ranking?.length && (
            <section className="lg:col-span-2">
              <h2 className="mb-3 text-lg font-semibold">Top assets (performance)</h2>
              <div className="grid gap-2 md:grid-cols-2">
                {report.asset_ranking.map((asset, index) => (
                  <div key={`${asset.title}-${index}`} className="rounded-md border border-border bg-card p-3 text-xs text-muted-foreground">
                    <p className="font-medium text-foreground">{String(asset.title ?? "—")}</p>
                    <p className="mt-1">
                      {String(asset.platform ?? "")} · {Number(asset.views ?? 0).toLocaleString()} views
                      {asset.ctr != null ? ` · CTR ${(Number(asset.ctr) * 100).toFixed(1)}%` : ""}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {(performance || perfLoading) && (
            <section className="lg:col-span-2">
              <h2 className="mb-3 text-lg font-semibold">Performance Learning (Growth)</h2>
              {perfLoading && <p className="text-sm text-muted-foreground">Carregando insights...</p>}
              {performance && (
                <div className="rounded-md border border-border bg-card p-4 text-sm">
                  <p className="text-muted-foreground">{performance.summary}</p>
                  <div className="mt-3 grid gap-2 text-xs text-muted-foreground md:grid-cols-4">
                    <p>Alto: {performance.high_performers}</p>
                    <p>Baixo: {performance.low_performers}</p>
                    <p>CTR médio: {performance.avg_ctr != null ? `${(performance.avg_ctr * 100).toFixed(1)}%` : "—"}</p>
                    <p>Retenção: {performance.avg_retention != null ? `${performance.avg_retention}%` : "—"}</p>
                  </div>
                  {performance.top_hooks.length > 0 && (
                    <p className="mt-2 text-xs text-emerald-400">Hooks: {performance.top_hooks.slice(0, 2).join(" · ")}</p>
                  )}
                </div>
              )}
            </section>
          )}

          <section className="lg:col-span-2">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 className="text-lg font-semibold">Próximas ações</h2>
              <Link href="/recommendations" className="text-xs text-primary hover:underline">
                Ver todas
              </Link>
            </div>
            {!report.recommendations.length ? (
              <p className="text-sm text-muted-foreground">Nenhuma recomendação pendente.</p>
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {report.recommendations.map((recommendation, index) => (
                  <div key={recommendation.id ?? `${recommendation.kind}-${index}`} className="rounded-md border border-border bg-card p-4">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold">{recommendation.title}</p>
                      <span className="text-xs text-muted-foreground">P{recommendation.priority}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{recommendation.detail}</p>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
