"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, Project } from "@/lib/api";

export default function ViralPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [topic, setTopic] = useState("");

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) {
      setProjectId(projects[0].id);
    }
  }, [projects, projectId]);

  const analyzeMutation = useMutation({
    mutationFn: () =>
      api.analyzeViral({
        project_id: projectId!,
        topic,
        include_reuse: true,
      }),
  });

  const report = analyzeMutation.data;

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Viral Intelligence</h1>
        <p className="text-sm text-muted-foreground">Score viral e retenção prevista antes da renderização (V4)</p>
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

      <div className="mb-6 flex max-w-2xl gap-2">
        <input
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
          placeholder="Tópico do vídeo"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        />
        <button
          type="button"
          disabled={!topic.trim() || analyzeMutation.isPending}
          onClick={() => analyzeMutation.mutate()}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
        >
          Analisar
        </button>
      </div>

      {report && (
        <div className="grid max-w-3xl gap-4">
          <div className="rounded-lg border border-border bg-card p-6">
            <div className="flex gap-8">
              <div>
                <p className="text-xs text-muted-foreground">Viral Score</p>
                <p className="text-3xl font-bold">{report.viral_score.toFixed(1)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Retenção prevista</p>
                <p className="text-3xl font-bold">{report.retention_prediction.toFixed(1)}</p>
              </div>
            </div>
          </div>
          {report.recommendations.length > 0 && (
            <div className="rounded-lg border border-border bg-card p-6">
              <h2 className="font-semibold">Recomendações</h2>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                {report.recommendations.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
