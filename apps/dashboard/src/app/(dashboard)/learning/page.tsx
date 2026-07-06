"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, LearningReport, Project } from "@/lib/api";

export default function LearningPage() {
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

  const { data: insights = [], isLoading } = useQuery({
    queryKey: ["learning-insights", projectId],
    queryFn: () => api.getLearningInsights(projectId!),
    enabled: Boolean(projectId),
  });

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Learning Engine</h1>
        <p className="text-sm text-muted-foreground">
          Insights pós-pipeline — hook, CTA, specialist e prompts → Memory + KB (V4.2.3)
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

      {isLoading && <p className="text-sm text-muted-foreground">Carregando insights…</p>}

      {!isLoading && insights.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Nenhum insight ainda. Complete um pipeline V4 com learning habilitado.
        </p>
      )}

      <div className="grid max-w-4xl gap-4">
        {insights.map((row: LearningReport) => (
          <div key={row.pipeline_id ?? row.topic} className="rounded-lg border border-border bg-card p-4">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold">{row.topic}</h2>
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
    </div>
  );
}
