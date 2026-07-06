"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, Project, TrendForecastReport } from "@/lib/api";

const GROWTH_LABELS: Record<string, string> = {
  very_high: "Muito alto",
  high: "Alto",
  moderate: "Moderado",
  low: "Baixo",
};

export default function TrendForecastPage() {
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

  const forecastMutation = useMutation({
    mutationFn: () =>
      api.forecastTrend({
        project_id: projectId!,
        topic,
      }),
  });

  const report: TrendForecastReport | undefined = forecastMutation.data;

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Trend Forecast</h1>
        <p className="text-sm text-muted-foreground">
          Score de tendência, crescimento esperado e recomendação de produção (V4.2.4)
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

      <div className="mb-6 flex max-w-2xl gap-2">
        <input
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
          placeholder="Tópico para previsão"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        />
        <button
          type="button"
          disabled={!topic.trim() || !projectId || forecastMutation.isPending}
          onClick={() => forecastMutation.mutate()}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
        >
          Prever
        </button>
      </div>

      {report && (
        <div className="max-w-2xl rounded-lg border border-border bg-card p-6">
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="text-lg font-semibold">{report.topic}</h2>
            <span className="text-3xl font-bold text-primary">{report.trend_score.toFixed(0)}</span>
          </div>
          <p className="mb-2 text-sm">
            <span className="text-muted-foreground">Crescimento: </span>
            {GROWTH_LABELS[report.expected_growth] ?? report.expected_growth}
          </p>
          <p className="mb-2 text-sm">
            <span className="text-muted-foreground">Ritmo: </span>
            {report.pacing_hint || "—"}
          </p>
          <p className="mb-4 text-sm">
            <span className="text-muted-foreground">Fontes: </span>
            {(report.sources || []).join(", ") || "—"}
          </p>
          <p className="rounded-md bg-muted/50 p-3 text-sm">{report.production_recommendation}</p>
        </div>
      )}
    </div>
  );
}
