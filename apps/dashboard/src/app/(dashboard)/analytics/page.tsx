"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { MetricBar, StatCard } from "@/components/dashboard/MetricBar";

export default function AnalyticsPage() {
  const queryClient = useQueryClient();
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
        <p className="text-sm text-muted-foreground">Performance, providers e uso de recursos</p>
      </header>

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
