"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, CommentInsightRow, ContentRecommendation, LearningReport, PerformanceInsightRow, Project } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function LearningPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) {
      setProjectId(projects[0].id);
    }
  }, [projects, projectId]);

  const { data: insights = [], isLoading } = useQuery({
    queryKey: ["learning-insights", projectId],
    queryFn: () => api.getLearningInsights(projectId!),
    enabled: Boolean(projectId),
  });

  const { data: perfInsights = [] } = useQuery({
    queryKey: ["performance-learning", projectId],
    queryFn: () => api.getPerformanceLearningInsights(projectId!),
    enabled: Boolean(projectId),
  });

  const processPerfMutation = useMutation({
    mutationFn: () => api.processPerformanceLearning({ project_id: projectId!, persist: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["performance-learning", projectId] });
    },
  });

  const { data: commentInsights = [] } = useQuery({
    queryKey: ["comment-insights", projectId],
    queryFn: () => api.getCommentInsights(projectId!),
    enabled: Boolean(projectId),
  });

  const { data: recommendations } = useQuery({
    queryKey: ["content-recommendations", projectId],
    queryFn: () => api.getProjectRecommendations(projectId!),
    enabled: Boolean(projectId),
  });

  const analyzeCommentsMutation = useMutation({
    mutationFn: () => api.analyzeComments({ project_id: projectId!, persist: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["comment-insights", projectId] });
    },
  });

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Learning Engine</h1>
        <p className="text-sm text-muted-foreground">
          Pipeline learning + Performance Learning + Comment Analyzer — V4 + V5.4.2 + V5.4.3
        </p>
      </header>

      <div className="mb-6 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-xs font-medium text-muted-foreground">Projeto</label>
          <select
            className="mt-1 block w-full max-w-md rounded-md border border-border bg-background px-3 py-2 text-sm"
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
          variant="secondary"
          onClick={() => processPerfMutation.mutate()}
          disabled={!projectId || processPerfMutation.isPending}
        >
          {processPerfMutation.isPending ? "Processando…" : "Performance Learning → KB"}
        </Button>
        <Button
          variant="outline"
          onClick={() => analyzeCommentsMutation.mutate()}
          disabled={!projectId || analyzeCommentsMutation.isPending}
        >
          {analyzeCommentsMutation.isPending ? "Analisando…" : "Comment Analyzer"}
        </Button>
      </div>

      {analyzeCommentsMutation.data && (
        <p className="mb-6 text-sm text-muted-foreground">{analyzeCommentsMutation.data.summary}</p>
      )}

      {processPerfMutation.data && (
        <p className="mb-6 text-sm text-muted-foreground">{processPerfMutation.data.summary}</p>
      )}

      {recommendations && (
        <section className="mb-10 max-w-4xl">
          <h2 className="mb-2 text-lg font-semibold">Próximo vídeo (recomendações)</h2>
          <p className="mb-4 text-sm text-muted-foreground">{recommendations.summary}</p>
          {recommendations.recommendations.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Execute Performance Learning ou Comment Analyzer para gerar sugestões.
            </p>
          ) : (
            <div className="grid gap-3">
              {recommendations.recommendations.map((rec: ContentRecommendation, index: number) => (
                <div key={`${rec.kind}-${index}`} className="rounded-lg border border-border bg-card p-4">
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">{rec.title}</span>
                    <span className="shrink-0 text-xs capitalize text-muted-foreground">
                      {rec.confidence} · {rec.source}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">{rec.detail}</p>
                  {rec.action_href && (
                    <a href={rec.action_href} className="mt-2 inline-block text-xs text-primary hover:underline">
                      Abrir fábrica →
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {perfInsights.length > 0 && (
        <section className="mb-10 max-w-4xl">
          <h2 className="mb-4 text-lg font-semibold">Performance Learning (OAuth)</h2>
          <div className="grid gap-3">
            {perfInsights.slice(0, 8).map((row: PerformanceInsightRow) => (
              <div key={row.id} className="rounded-lg border border-border bg-card p-4">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-sm font-medium capitalize">
                    {row.platform} · {row.performance_tier}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    CTR {((row.ctr ?? 0) * 100).toFixed(1)}% · {row.views} views
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">{row.title ?? row.topic}</p>
                {row.retention_pct != null && (
                  <p className="mt-1 text-xs">
                    Retenção {row.retention_pct.toFixed(1)}%
                    {row.retention_delta != null && ` (Δ ${row.retention_delta >= 0 ? "+" : ""}${row.retention_delta.toFixed(1)} p.p.)`}
                  </p>
                )}
                {row.learnings.length > 0 && (
                  <ul className="mt-2 list-inside list-disc text-xs text-muted-foreground">
                    {row.learnings.map((l) => (
                      <li key={l}>{l}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {commentInsights.length > 0 && (
        <section className="mb-10 max-w-4xl">
          <h2 className="mb-4 text-lg font-semibold">Comment Analyzer (OAuth)</h2>
          <div className="grid gap-3">
            {commentInsights.slice(0, 6).map((row: CommentInsightRow) => (
              <div key={row.id} className="rounded-lg border border-border bg-card p-4">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-sm font-medium capitalize">{row.platform}</span>
                  <span className="text-xs text-muted-foreground">{row.comment_count} comentários</span>
                </div>
                <p className="text-xs text-muted-foreground">{row.title ?? row.external_media_id}</p>
                {row.error ? (
                  <p className="mt-1 text-xs text-amber-600">{row.error}</p>
                ) : (
                  <p className="mt-1 text-xs">
                    +{row.positive_pct}% / -{row.negative_pct}% / neutro {row.neutral_pct}%
                    {row.question_count > 0 && ` · ${row.question_count} perguntas`}
                  </p>
                )}
                {row.themes.length > 0 && (
                  <p className="mt-1 text-xs text-muted-foreground">Temas: {row.themes.join(", ")}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="max-w-4xl">
        <h2 className="mb-4 text-lg font-semibold">Pipeline Learning</h2>
        {isLoading && <p className="text-sm text-muted-foreground">Carregando insights…</p>}

        {!isLoading && insights.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Nenhum insight ainda. Complete um pipeline V4 com learning habilitado.
          </p>
        )}

        <div className="grid gap-4">
          {insights.map((row: LearningReport) => (
            <div key={row.pipeline_id ?? row.topic} className="rounded-lg border border-border bg-card p-4">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-semibold">{row.topic}</h3>
                <span className="text-xs text-muted-foreground">
                  score {row.content_score ?? "—"} · viral {row.viral_score ?? "—"}
                </span>
              </div>
              {row.hook_text && (
                <p className="mb-1 text-xs">
                  <span className="text-muted-foreground">Hook: </span>
                  {row.hook_text}
                </p>
              )}
              {row.cta_text && (
                <p className="mb-1 text-xs">
                  <span className="text-muted-foreground">CTA: </span>
                  {row.cta_text}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                {row.signal_count} sinais · KB {row.kb_indexed_count} · memory{" "}
                {row.memory_applied ? row.memory_updates.join(", ") : "não aplicado"}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
