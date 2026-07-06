"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useWorkflowSocket } from "@/hooks/useWorkflowSocket";
import { MetricBar, StatCard } from "@/components/dashboard/MetricBar";

export default function DashboardPage() {
  const { data: analytics } = useQuery({
    queryKey: ["analytics"],
    queryFn: api.getAnalytics,
    refetchInterval: 30_000,
  });
  const { data: agents } = useQuery({
    queryKey: ["agents"],
    queryFn: api.getAgents,
    refetchInterval: 30_000,
  });
  const { data: system } = useQuery({
    queryKey: ["metrics-system"],
    queryFn: api.getSystemMetrics,
    enabled: !!analytics,
    refetchInterval: 30_000,
  });
  const { data: infra } = useQuery({
    queryKey: ["metrics-infra"],
    queryFn: api.getInfrastructureMetrics,
    enabled: !!analytics,
    refetchInterval: 30_000,
  });
  const { data: storage } = useQuery({
    queryKey: ["storage"],
    queryFn: api.getStorageStats,
    enabled: !!analytics,
    refetchInterval: 60_000,
  });
  const { events, connected } = useWorkflowSocket();

  const runningAgents = agents?.filter((a) => a.status === "running").length ?? 0;
  const onlineAgents = agents?.filter((a) => ["online", "running"].includes(a.status)).length ?? 0;

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Painel</h1>
        <p className="text-sm text-muted-foreground">
          ContentOS — observabilidade em tempo real · Conexão {connected ? "ativa" : "inativa"}
        </p>
      </header>

      <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Vídeos criados" value={analytics?.videos_created ?? 0} />
        <StatCard label="Agentes ativos" value={onlineAgents} sub={`${runningAgents} executando`} />
        <StatCard label="Fila Celery" value={infra?.celery.total_pending ?? analytics?.queue_pending ?? 0} sub={`${infra?.celery.workers ?? 0} workers`} />
        <StatCard label="Tempo médio" value={analytics?.avg_duration_seconds ? `${analytics.avg_duration_seconds}s` : "—"} />
        <StatCard label="Taxa de erro" value={analytics ? `${(analytics.error_rate * 100).toFixed(1)}%` : "—"} />
        <StatCard label="Armazenamento" value={storage ? `${storage.total_mb.toFixed(0)} MB` : "—"} sub={`${storage?.total_assets ?? 0} arquivos`} />
      </div>

      <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="rounded-lg border border-border bg-card p-5 lg:col-span-1">
          <h2 className="mb-4 font-semibold">Sistema</h2>
          {system ? (
            <div className="space-y-4">
              <MetricBar label="CPU" value={Math.round(system.cpu.percent)} detail={`${system.cpu.cores} cores`} />
              <MetricBar label="RAM" value={Math.round(system.memory.percent)} detail={`${system.memory.used_mb} / ${system.memory.total_mb} MB`} />
              <MetricBar label="Disco" value={Math.round(system.disk.percent)} detail={`${system.disk.used_gb} / ${system.disk.total_gb} GB`} />
              {system.gpu?.available && (
                <>
                  <MetricBar label="GPU" value={Math.round(system.gpu.utilization)} detail={system.gpu.name} />
                  <MetricBar
                    label="VRAM"
                    value={Math.round((system.gpu.memory_used_mb / system.gpu.memory_total_mb) * 100)}
                    detail={`${system.gpu.memory_used_mb} / ${system.gpu.memory_total_mb} MB`}
                  />
                </>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Carregando métricas...</p>
          )}
        </section>

        <section className="rounded-lg border border-border bg-card p-5 lg:col-span-1">
          <h2 className="mb-4 font-semibold">Infraestrutura</h2>
          {infra ? (
            <div className="space-y-3 text-sm">
              {[
                { name: "PostgreSQL", data: infra.postgres },
                { name: "Redis", data: infra.redis },
                { name: "Celery", data: { status: infra.celery.workers > 0 ? "healthy" : "idle", latency_ms: undefined } },
              ].map(({ name, data }) => (
                <div key={name} className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                  <span>{name}</span>
                  <span className={data.status === "healthy" ? "text-emerald-400" : "text-amber-400"}>
                    {data.status}
                    {"latency_ms" in data && data.latency_ms != null && ` · ${data.latency_ms}ms`}
                    {name === "Redis" && infra.redis.memory_mb != null && ` · ${infra.redis.memory_mb} MB`}
                    {name === "Celery" && ` · ${infra.celery.workers} workers`}
                  </span>
                </div>
              ))}
              <div className="mt-2 max-h-32 overflow-y-auto font-mono text-xs text-muted-foreground">
                {Object.entries(infra.celery.queues).map(([q, depth]) => (
                  depth > 0 && <div key={q}>{q}: {depth}</div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Carregando...</p>
          )}
        </section>

        <section className="rounded-lg border border-border bg-card p-5 lg:col-span-1">
          <h2 className="mb-4 font-semibold">Agentes</h2>
          <div className="max-h-64 space-y-2 overflow-y-auto">
            {(agents ?? []).map((a) => (
              <div key={a.name} className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm">
                <span className="capitalize">{a.name}</span>
                <span className="text-xs text-muted-foreground capitalize">{a.status}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-lg border border-border bg-card p-5">
        <h2 className="mb-4 font-semibold">Workflow em tempo real</h2>
        <div className="max-h-48 overflow-y-auto font-mono text-xs">
          {events.length === 0 ? (
            <p className="text-muted-foreground">Aguardando eventos...</p>
          ) : (
            events.map((e, i) => (
              <div key={i} className="mb-1 text-muted-foreground">
                [{e.type}] {e.step ?? "—"} — {e.status}
                {e.pipeline_id && <span className="opacity-50"> · {e.pipeline_id.slice(0, 8)}</span>}
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
