"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, ExecutiveSummary, Project } from "@/lib/api";
import { MetricBar, StatCard } from "@/components/dashboard/MetricBar";

export default function ExecutiveDashboardPage() {
  const [projectId, setProjectId] = useState<string | null>(null);

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) {
      setProjectId(projects[0].id);
    }
  }, [projects, projectId]);

  const { data: summary, isLoading } = useQuery({
    queryKey: ["executive-summary", projectId],
    queryFn: () => api.getExecutiveSummary(projectId!),
    enabled: Boolean(projectId),
    refetchInterval: 60_000,
  });

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Command Center</h1>
        <p className="text-sm text-muted-foreground">
          Visão unificada V4 + V5 — produção, qualidade, OAuth, SLO e comunidade (V5.5.3)
        </p>
      </header>

      <div className="mb-6">
        <label className="text-xs font-medium text-muted-foreground">Projeto</label>
        <select
          className="mt-1 w-full max-w-md rounded-md border border-border bg-background px-3 py-2 text-sm"
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

      {isLoading && <p className="text-sm text-muted-foreground">Carregando Command Center…</p>}

      {summary && (
        <>
          {summary.alerts?.length > 0 && (
            <section className="mb-6 space-y-2">
              {summary.alerts.map((alert) => (
                <p
                  key={alert}
                  className="rounded-md border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm text-amber-800 dark:text-amber-200"
                >
                  {alert}
                </p>
              ))}
            </section>
          )}

          {summary.slo_items?.length > 0 && (
            <section className="mb-8">
              <h2 className="mb-3 text-sm font-semibold">SLO — Plataforma</h2>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {summary.slo_items.map((slo) => (
                  <div
                    key={slo.id}
                    className={`rounded-md border px-3 py-2 text-sm ${
                      slo.state === "critical"
                        ? "border-red-500/40 bg-red-500/10"
                        : slo.state === "warning"
                          ? "border-amber-500/40 bg-amber-500/10"
                          : "border-border bg-card"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{slo.name}</span>
                      <span className="text-xs uppercase text-muted-foreground">{slo.state}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {slo.current} · meta {slo.target}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}

          <div className="mb-4">
            <h2 className="mb-3 text-sm font-semibold">KPIs V5 — Pós-publicação</h2>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6">
              <StatCard label="Lotes" value={summary.factory_batches_total} sub={`${summary.factory_batches_running} ativos`} />
              <StatCard label="OAuth snapshots" value={summary.platform_snapshots} sub={`${summary.oauth_channels_connected} canais`} />
              <StatCard label="Perf. Learning" value={summary.performance_insights} sub="insights" />
              <StatCard label="Comentários" value={summary.comment_insights} sub="análises" />
              <StatCard label="Rascunhos" value={summary.community_drafts_pending} sub="comunidade" />
              <StatCard
                label="Aprovação lote"
                value={summary.factory_pending_approval}
                sub={summary.factory_pending_approval > 0 ? "ação necessária" : "ok"}
              />
            </div>
          </div>

          <div className="mb-8">
            <h2 className="mb-3 text-sm font-semibold">KPIs V4 — Inteligência</h2>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6">
              <StatCard label="Pipelines" value={summary.pipelines_completed} sub={`${summary.pipelines_total} total`} />
              <StatCard label="KB" value={summary.knowledge_entries} sub="entradas" />
              <StatCard label="Learning" value={summary.learning_insights} sub="insights" />
              <StatCard label="Grafo" value={summary.graph_nodes} sub={`${summary.graph_edges} arestas`} />
              <StatCard
                label="Content Score"
                value={summary.avg_content_score != null ? summary.avg_content_score.toFixed(0) : "—"}
              />
              <StatCard
                label="Trend"
                value={summary.latest_trend_score != null ? summary.latest_trend_score.toFixed(0) : "—"}
                sub={summary.latest_trend_growth ?? ""}
              />
            </div>
          </div>

          {summary.dna_preview && (
            <section className="mb-8 rounded-lg border border-border bg-card p-4">
              <h2 className="mb-2 text-sm font-semibold">Project DNA</h2>
              <p className="text-sm text-muted-foreground">{summary.dna_preview}</p>
              {summary.hook_patterns.length > 0 && (
                <p className="mt-2 text-xs text-muted-foreground">
                  Hooks: {summary.hook_patterns.join(" · ")}
                </p>
              )}
            </section>
          )}

          {summary.v5_modules?.length > 0 && (
            <section className="mb-8">
              <h2 className="mb-4 text-sm font-semibold">Módulos V5</h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {summary.v5_modules.map((mod) => (
                  <ModuleCard key={mod.key} module={mod} />
                ))}
              </div>
            </section>
          )}

          <section>
            <h2 className="mb-4 text-sm font-semibold">Módulos V4</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {summary.modules.map((mod) => (
                <ModuleCard key={mod.key} module={mod} />
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function ModuleCard({ module: mod }: { module: ExecutiveSummary["modules"][0] }) {
  const active = mod.status === "active";
  return (
    <Link
      href={mod.href}
      className="block rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/50"
    >
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-medium">{mod.label}</h3>
        <span
          className={`h-2 w-2 rounded-full ${active ? "bg-emerald-500" : "bg-muted-foreground/40"}`}
          title={mod.status}
        />
      </div>
      <p className="text-2xl font-semibold">{mod.metric}</p>
      {mod.detail && <p className="mt-1 text-xs text-muted-foreground">{mod.detail}</p>}
      {mod.key === "content_score" && mod.metric !== "—" && !Number.isNaN(Number(mod.metric)) && (
        <div className="mt-3">
          <MetricBar label="" value={Number(mod.metric)} unit="" warnAt={60} criticalAt={40} />
        </div>
      )}
    </Link>
  );
}
