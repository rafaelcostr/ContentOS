"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { api, Project } from "@/lib/api";

function formatCount(value: unknown) {
  if (value == null || value === "") return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  return num.toLocaleString();
}

export default function CompetitorsPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [platform, setPlatform] = useState("youtube");
  const [handle, setHandle] = useState("");
  const [displayName, setDisplayName] = useState("");
  const queryClient = useQueryClient();

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) setProjectId(projects[0].id);
  }, [projects, projectId]);

  const { data: competitors = [], isLoading } = useQuery({
    queryKey: ["growth-competitors", projectId],
    queryFn: () => api.getGrowthCompetitors(projectId!),
    enabled: Boolean(projectId),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.createGrowthCompetitor({
        project_id: projectId!,
        platform,
        handle,
        display_name: displayName || undefined,
      }),
    onSuccess: () => {
      setHandle("");
      setDisplayName("");
      queryClient.invalidateQueries({ queryKey: ["growth-competitors", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-report", projectId] });
    },
  });

  const syncAllMutation = useMutation({
    mutationFn: () => api.syncAllGrowthCompetitors(projectId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["growth-competitors", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-recommendations", projectId] });
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!projectId || !handle.trim()) return;
    createMutation.mutate();
  }

  return (
    <div className="p-8">
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Concorrentes</h1>
          <p className="text-sm text-muted-foreground">
            Benchmarking competitivo — sincronize métricas públicas e analise padrões (Growth OS Fase 7).
          </p>
        </div>
        <Button
          variant="secondary"
          disabled={!projectId || !competitors.length || syncAllMutation.isPending}
          onClick={() => syncAllMutation.mutate()}
        >
          {syncAllMutation.isPending ? "Sincronizando..." : "Sincronizar todos"}
        </Button>
      </header>

      <div className="mb-6">
        <label className="text-xs font-medium text-muted-foreground">Projeto</label>
        <select
          className="mt-1 block w-full max-w-md rounded-md border border-border bg-background px-3 py-2 text-sm"
          value={projectId ?? ""}
          onChange={(event) => setProjectId(event.target.value)}
        >
          {projects.map((project: Project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
      </div>

      <form onSubmit={submit} className="mb-8 grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-[160px_1fr_1fr_auto]">
        <select
          className="rounded-md border border-border bg-background px-3 py-2 text-sm"
          value={platform}
          onChange={(event) => setPlatform(event.target.value)}
        >
          <option value="youtube">YouTube</option>
          <option value="tiktok">TikTok</option>
          <option value="instagram">Instagram</option>
        </select>
        <input
          className="rounded-md border border-border bg-background px-3 py-2 text-sm"
          placeholder="@canal ou URL"
          value={handle}
          onChange={(event) => setHandle(event.target.value)}
        />
        <input
          className="rounded-md border border-border bg-background px-3 py-2 text-sm"
          placeholder="Nome público"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
        />
        <Button type="submit" disabled={!projectId || !handle.trim() || createMutation.isPending}>
          {createMutation.isPending ? "Salvando..." : "Adicionar"}
        </Button>
      </form>

      {createMutation.error && <p className="mb-4 text-sm text-destructive">{String(createMutation.error)}</p>}
      {isLoading && <p className="text-sm text-muted-foreground">Carregando concorrentes...</p>}
      {!isLoading && competitors.length === 0 && (
        <p className="text-sm text-muted-foreground">Nenhum concorrente cadastrado para este projeto.</p>
      )}

      <div className="grid gap-3">
        {competitors.map((competitor) => (
          <CompetitorCard key={competitor.id} competitor={competitor} projectId={projectId} />
        ))}
      </div>
    </div>
  );
}

function CompetitorCard({
  competitor,
  projectId,
}: {
  competitor: import("@/lib/api").GrowthCompetitor;
  projectId: string | null;
}) {
  const queryClient = useQueryClient();
  const totals = (competitor.metrics?.channel_totals as Record<string, unknown> | undefined) ?? {};
  const patterns = (competitor.metrics?.patterns as Record<string, unknown> | undefined) ?? {};

  const syncMutation = useMutation({
    mutationFn: () => api.syncGrowthCompetitor(competitor.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["growth-competitors", projectId] });
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: () => api.analyzeGrowthCompetitor(competitor.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["growth-competitors", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-recommendations", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-report", projectId] });
    },
  });

  return (
    <div className="rounded-md border border-border bg-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">{competitor.display_name ?? competitor.handle}</p>
          <p className="text-xs text-muted-foreground">
            {competitor.platform} · {competitor.handle}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" disabled={syncMutation.isPending} onClick={() => syncMutation.mutate()}>
            {syncMutation.isPending ? "Sync..." : "Sincronizar"}
          </Button>
          <Button
            size="sm"
            disabled={!competitor.last_synced_at || analyzeMutation.isPending}
            onClick={() => analyzeMutation.mutate()}
          >
            {analyzeMutation.isPending ? "Analisando..." : "Analisar"}
          </Button>
          {competitor.url && (
            <a className="self-center text-xs text-primary hover:underline" href={competitor.url} rel="noreferrer" target="_blank">
              Abrir
            </a>
          )}
        </div>
      </div>

      {competitor.analysis_score != null && (
        <div className="mt-3 rounded-md border border-border bg-muted/20 p-3">
          <p className="text-sm font-semibold">Score competitivo: {competitor.analysis_score.toFixed(0)}/100</p>
          {competitor.analysis_summary && (
            <p className="mt-1 text-xs text-muted-foreground">{competitor.analysis_summary}</p>
          )}
        </div>
      )}

      {(totals.subscriber_count != null || totals.view_count != null) && (
        <div className="mt-3 grid gap-2 text-xs text-muted-foreground md:grid-cols-4">
          <p>Inscritos: {formatCount(totals.subscriber_count)}</p>
          <p>Views: {formatCount(totals.view_count)}</p>
          <p>Shorts: {formatCount(totals.shorts_count)}</p>
          <p>Última sync: {competitor.last_synced_at ? new Date(competitor.last_synced_at).toLocaleString() : "nunca"}</p>
        </div>
      )}

      {Array.isArray(patterns.top_hooks) && patterns.top_hooks.length > 0 && (
        <p className="mt-2 text-xs text-muted-foreground">
          Hooks: {(patterns.top_hooks as string[]).slice(0, 3).join(" · ")}
        </p>
      )}

      {Boolean(competitor.metrics?.sync_error) && (
        <p className="mt-2 text-xs text-amber-400">Sync: {String(competitor.metrics.sync_error)}</p>
      )}
      {competitor.notes && <p className="mt-2 text-xs text-muted-foreground">{competitor.notes}</p>}
      {analyzeMutation.data && (
        <p className="mt-2 text-xs text-emerald-400">
          Análise concluída — {analyzeMutation.data.recommendations.length} recomendação(ões).
        </p>
      )}
    </div>
  );
}
