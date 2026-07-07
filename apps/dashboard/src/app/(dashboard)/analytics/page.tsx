"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api, Project } from "@/lib/api";
import { MetricBar, StatCard } from "@/components/dashboard/MetricBar";

const PLATFORM_LABELS: Record<string, string> = {
  youtube: "YouTube",
  tiktok: "TikTok",
  instagram: "Instagram",
};

export default function AnalyticsPage() {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState<string | null>(null);

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) setProjectId(projects[0].id);
  }, [projects, projectId]);

  const { data: overview } = useQuery({ queryKey: ["analytics"], queryFn: api.getAnalytics, refetchInterval: 45_000 });
  const { data: insights } = useQuery({
    queryKey: ["analytics-insights"],
    queryFn: () => api.getAnalyticsInsights(20),
    refetchInterval: 60_000,
  });
  const { data: perf } = useQuery({ queryKey: ["performance"], queryFn: api.getPerformance, refetchInterval: 45_000 });
  const { data: providers } = useQuery({
    queryKey: ["provider-analytics"],
    queryFn: api.getProviderAnalytics,
    refetchInterval: 60_000,
  });
  const { data: platformCaps } = useQuery({
    queryKey: ["platform-analytics-caps", projectId],
    queryFn: () => api.getPlatformAnalyticsCapabilities(projectId!),
    enabled: !!projectId,
  });
  const { data: platformSummary } = useQuery({
    queryKey: ["platform-analytics-summary", projectId],
    queryFn: () => api.getPlatformAnalyticsSummary(projectId!),
    enabled: !!projectId,
    refetchInterval: 120_000,
  });
  const { data: platformSnapshots } = useQuery({
    queryKey: ["platform-analytics-snapshots", projectId],
    queryFn: () => api.getPlatformAnalyticsSnapshots(projectId!, undefined, 20),
    enabled: !!projectId,
  });
  const syncPlatformMutation = useMutation({
    mutationFn: () => api.syncPlatformAnalytics({ project_id: projectId!, persist: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform-analytics-summary", projectId] });
      queryClient.invalidateQueries({ queryKey: ["platform-analytics-snapshots", projectId] });
    },
  });
  const { data: system } = useQuery({
    queryKey: ["metrics-system"],
    queryFn: api.getSystemMetrics,
    enabled: !!overview,
    refetchInterval: 45_000,
  });


  const applyMutation = useMutation({
    mutationFn: api.applyAnalyticsInsight,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["analytics-insights"] }),
  });

  const metrics = [
    { label: "Vídeos criados", value: overview?.videos_created ?? 0 },
    { label: "Pipelines totais", value: overview?.pipelines_total ?? 0 },
    { label: "Concluídos", value: overview?.pipelines_completed ?? 0 },
    { label: "Tempo médio", value: overview?.avg_duration_seconds ? `${overview.avg_duration_seconds}s` : "—" },
    { label: "Taxa de erro", value: overview ? `${(overview.error_rate * 100).toFixed(1)}%` : "—" },
    { label: "Fila pendente", value: overview?.queue_pending ?? 0 },
  ];

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Análises</h1>
        <p className="text-sm text-muted-foreground">Performance, providers, OAuth platforms e uso de recursos</p>
      </header>

      <div className="mb-8 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-xs text-muted-foreground">Projeto (OAuth Analytics)</label>
          <select
            className="mt-1 block rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={projectId ?? ""}
            onChange={(e) => setProjectId(e.target.value)}
          >
            {projects.map((p: Project) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <Button
          onClick={() => syncPlatformMutation.mutate()}
          disabled={!projectId || syncPlatformMutation.isPending}
        >
          {syncPlatformMutation.isPending ? "Sincronizando…" : "Sync OAuth (YT/TikTok/IG)"}
        </Button>
      </div>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle>OAuth Analytics — plataformas (V5.4.1)</CardTitle>
        </CardHeader>
        <CardContent>
          {!platformCaps?.length ? (
            <p className="text-sm text-muted-foreground">Selecione um projeto com canais OAuth em /plugins.</p>
          ) : (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-3">
                {platformCaps.map((cap) => (
                  <div key={cap.platform} className="rounded-md border border-border p-4">
                    <p className="font-medium">{PLATFORM_LABELS[cap.platform] ?? cap.platform}</p>
                    <p className="text-xs text-muted-foreground">
                      {cap.connected_channels} canal(is) · OAuth {cap.oauth_available ? "ok" : "não configurado"}
                    </p>
                    {cap.connected_channels === 0 && cap.oauth_available && (
                      <p className="mt-1 text-xs text-amber-600">Reconecte em /plugins para scopes de analytics</p>
                    )}
                  </div>
                ))}
              </div>
              {platformSummary && platformSummary.snapshot_count > 0 && (
                <div className="grid gap-4 sm:grid-cols-3">
                  {platformSummary.platforms.map((p) => (
                    <div key={p.platform} className="rounded-md border border-border p-3 text-sm">
                      <p className="font-medium capitalize">{p.platform}</p>
                      <p className="text-muted-foreground">{p.media_count} mídias rastreadas</p>
                      <p>{p.total_views.toLocaleString()} views · {p.total_likes.toLocaleString()} likes</p>
                    </div>
                  ))}
                </div>
              )}
              {syncPlatformMutation.data?.reports?.some((r) => r.needs_reconnect) && (
                <p className="text-sm text-amber-600">
                  Alguns canais precisam reconectar OAuth com scopes de analytics (veja /plugins).
                </p>
              )}
              {platformSnapshots && platformSnapshots.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold">Últimas métricas</h3>
                  {platformSnapshots.slice(0, 8).map((snap) => (
                    <div key={snap.id} className="rounded border border-border/60 px-3 py-2 text-sm">
                      <span className="font-medium capitalize">{snap.platform}</span>
                      <span className="text-muted-foreground"> — {snap.title?.slice(0, 50) ?? snap.external_media_id}</span>
                      <span className="ml-2 text-xs">
                        {snap.metrics.views} views · {snap.metrics.likes} likes
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        {metrics.map((m) => (
          <StatCard key={m.label} label={m.label} value={m.value} />
        ))}
      </div>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle>AI Insights (V2.8)</CardTitle>
        </CardHeader>
        <CardContent>
          {!insights?.length ? (
            <p className="text-sm text-muted-foreground">
              Nenhuma análise ainda. Conclua um pipeline com ENABLE_ANALYTICS_AI=true.
            </p>
          ) : (
            <div className="space-y-4">
              {insights.map((insight) => (
                <div key={insight.id} className="rounded-md border border-border p-4">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-xs text-muted-foreground">
                      {insight.pipeline_id.slice(0, 8)}…
                    </span>
                    <span className="text-sm font-semibold">
                      Score: {insight.score ?? insight.analysis?.score ?? "—"}
                    </span>
                  </div>
                  <p className="text-sm">{insight.summary ?? insight.analysis?.summary ?? "—"}</p>
                  {insight.analysis?.suggestions?.length ? (
                    <ul className="mt-2 list-inside list-disc text-xs text-muted-foreground">
                      {insight.analysis.suggestions.slice(0, 3).map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  ) : null}
                  <div className="mt-3 flex items-center gap-3">
                    <button
                      type="button"
                      disabled={insight.applied_to_memory || applyMutation.isPending}
                      onClick={() => applyMutation.mutate(insight.pipeline_id)}
                      className="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground disabled:opacity-50"
                    >
                      {insight.applied_to_memory ? "Aplicado à memória" : "Aplicar à memória"}
                    </button>
                    <span className="text-xs text-muted-foreground">
                      {new Date(insight.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Uso por Provider (IA)</CardTitle></CardHeader>
          <CardContent>
            {!providers?.providers?.length ? (
              <p className="text-muted-foreground">Sem dados</p>
            ) : (
              <div className="space-y-4">
                {providers.providers.map((p) => (
                  <div key={p.provider} className="rounded-md border border-border p-4">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="font-medium capitalize">{p.provider}</span>
                      <span className={p.healthy ? "text-emerald-400 text-xs" : "text-amber-400 text-xs"}>
                        {p.healthy === true ? "online" : p.healthy === false ? "offline" : "local"}
                      </span>
                    </div>
                    <MetricBar
                      label="Taxa de sucesso"
                      value={Math.round(p.success_rate * 100)}
                    />
                    <div className="mt-2 flex gap-3 text-xs text-muted-foreground">
                      <span>{p.jobs_completed} ok</span>
                      <span>{p.jobs_failed} fail</span>
                      <span>{p.jobs_running} running</span>
                      <span>{p.jobs_total} total</span>
                    </div>
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      steps: {p.steps.join(", ")}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Recursos do sistema</CardTitle></CardHeader>
          <CardContent>
            {system ? (
              <div className="space-y-4">
                <MetricBar label="CPU" value={Math.round(system.cpu.percent)} />
                <MetricBar label="RAM" value={Math.round(system.memory.percent)} />
                <MetricBar label="Disco" value={Math.round(system.disk.percent)} />
                {system.gpu?.available && (
                  <MetricBar label="GPU" value={Math.round(system.gpu.utilization)} detail={system.gpu.name} />
                )}
              </div>
            ) : (
              <p className="text-muted-foreground">Carregando...</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Performance por agente</CardTitle></CardHeader>
        <CardContent>
          {!perf?.by_step ? (
            <p className="text-muted-foreground">Sem dados</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(perf.by_step).map(([step, statuses]) => {
                const completed = statuses.completed ?? 0;
                const failed = statuses.failed ?? 0;
                const total = Object.values(statuses).reduce((a, b) => a + b, 0);
                const rate = total > 0 ? Math.round((completed / total) * 100) : 0;
                return (
                  <div key={step} className="rounded-md border border-border p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="capitalize font-medium">{step}</span>
                      <span className="text-xs text-muted-foreground">{total} jobs</span>
                    </div>
                    <MetricBar label="Concluídos" value={rate} />
                    <div className="mt-2 flex flex-wrap gap-2 text-xs">
                      {Object.entries(statuses).map(([st, count]) => (
                        <span key={st} className="rounded bg-muted px-2 py-1 capitalize">{st}: {count}</span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
