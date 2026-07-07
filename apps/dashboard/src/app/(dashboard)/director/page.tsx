"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, DirectorDecision, Project } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const SAMPLE_PAYLOAD = {
  topic: "GTA 6",
  content_score: 58,
  content_score_report: {
    total_score: 58,
    dimensions: [
      { name: "hook", score: 72, weight: 0.15, source: "viral_report.hook_score" },
      { name: "retention", score: 48, weight: 0.15, source: "retention_report.overall_score" },
      { name: "cta", score: 55, weight: 0.1, source: "viral_report.cta_score" },
      { name: "seo", score: 80, weight: 0.1, source: "seo_package.seo_score" },
      { name: "technical", score: 70, weight: 0.1, source: "quality_score" },
    ],
  },
  retention_report: {
    overall_score: 48,
    hook_retention_pct: 62,
    completion_pct: 35,
    weak_segments: [{ label: "body", retention_pct: 30 }],
    drop_seconds: [8],
  },
  quality_score: 7,
};

export default function DirectorPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [topic, setTopic] = useState("GTA 6");

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) setProjectId(projects[0].id);
  }, [projects, projectId]);

  const planMutation = useMutation({
    mutationFn: () =>
      api.planDirector({
        project_id: projectId!,
        topic,
        payload: { ...SAMPLE_PAYLOAD, topic },
      }),
  });

  const decision: DirectorDecision | undefined = planMutation.data;

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">AI Director</h1>
        <p className="text-sm text-muted-foreground">
          Re-run parcial do pipeline pela dimensão mais fraca (V5.2.4)
        </p>
      </header>

      <div className="mb-6 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-xs text-muted-foreground">Projeto</label>
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
        <div>
          <label className="text-xs text-muted-foreground">Tema</label>
          <Input className="mt-1 w-64" value={topic} onChange={(e) => setTopic(e.target.value)} />
        </div>
        <Button onClick={() => planMutation.mutate()} disabled={!projectId || planMutation.isPending}>
          {planMutation.isPending ? "Analisando…" : "Planejar re-run"}
        </Button>
      </div>

      {decision && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-4">
            <div className="rounded-lg border border-border p-4">
              <dt className="text-xs text-muted-foreground">Score geral</dt>
              <dd className="text-3xl font-bold">{decision.overall_score.toFixed(0)}</dd>
            </div>
            <div className="rounded-lg border border-border p-4">
              <dt className="text-xs text-muted-foreground">Ação</dt>
              <dd className="text-lg font-semibold uppercase">{decision.action}</dd>
            </div>
            <div className="rounded-lg border border-border p-4">
              <dt className="text-xs text-muted-foreground">Re-run from</dt>
              <dd className="font-mono text-sm">{decision.retry_from || "—"}</dd>
            </div>
            <div className="rounded-lg border border-border p-4">
              <dt className="text-xs text-muted-foreground">Target</dt>
              <dd className="font-mono text-sm">{decision.target || "—"}</dd>
            </div>
          </div>

          <section className="rounded-lg border border-border p-4">
            <h2 className="mb-2 font-semibold">Decisão</h2>
            <p className="text-sm text-muted-foreground">{decision.reason}</p>
            <p className="mt-2 text-sm">
              Status:{" "}
              <span className={decision.passed ? "text-green-600" : "text-amber-600"}>
                {decision.passed ? "Aprovado" : "Re-run recomendado"}
              </span>
            </p>
          </section>

          <section className="rounded-lg border border-border p-4">
            <h2 className="mb-3 font-semibold">Sinais fracos</h2>
            <div className="space-y-2">
              {decision.weak_signals.map((sig) => (
                <div key={sig.name} className="flex items-center justify-between text-sm">
                  <span className="font-medium">{sig.name}</span>
                  <span className="text-muted-foreground">
                    {sig.score.toFixed(0)} — {sig.source}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
