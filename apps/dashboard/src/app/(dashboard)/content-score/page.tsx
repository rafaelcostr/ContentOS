"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, ContentScoreReport, Project } from "@/lib/api";

export default function ContentScorePage() {
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

  const scoreMutation = useMutation({
    mutationFn: () =>
      api.scoreContent({
        project_id: projectId!,
        topic,
        full_pipeline: true,
      }),
  });

  const report: ContentScoreReport | undefined = scoreMutation.data;

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Content Score</h1>
        <p className="text-sm text-muted-foreground">Nota unificada 0–100 — hook, retenção, emoção, CTA e mais (V4)</p>
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
          disabled={!topic.trim() || !projectId || scoreMutation.isPending}
          onClick={() => scoreMutation.mutate()}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
        >
          Calcular
        </button>
      </div>

      {report && (
        <div className="grid max-w-3xl gap-4">
          <div className="rounded-lg border border-border bg-card p-6">
            <div className="flex gap-8">
              <div>
                <p className="text-xs text-muted-foreground">Nota total</p>
                <p className="text-3xl font-bold">{report.total_score.toFixed(1)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Grade</p>
                <p className="text-xl font-semibold capitalize">{report.grade}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Modo</p>
                <p className="text-sm">{report.mode}</p>
              </div>
            </div>
            <p className="mt-4 text-sm text-muted-foreground">{report.summary}</p>
          </div>

          <div className="rounded-lg border border-border bg-card p-4">
            <h2 className="mb-3 text-sm font-semibold">Dimensões</h2>
            <ul className="space-y-2 text-sm">
              {report.dimensions.map((d) => (
                <li key={d.name} className="flex justify-between gap-4">
                  <span className="capitalize">{d.name}</span>
                  <span className="text-muted-foreground">
                    {d.score.toFixed(1)} <span className="text-xs">({(d.weight * 100).toFixed(0)}%)</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
