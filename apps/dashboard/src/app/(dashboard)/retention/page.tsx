"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { api, Project, RetentionReport } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const SAMPLE_PAYLOAD = {
  duration_seconds: 30,
  emotion: { curiosity: 8, retention: 7, overall: 7 },
  scenes: [
    { label: "hook", start_seconds: 0, end_seconds: 5 },
    { label: "body", start_seconds: 5, end_seconds: 22 },
    { label: "cta", start_seconds: 22, end_seconds: 30 },
  ],
  director_plan: {
    segments: [
      { movement: "speed-ramp-up", transition: "cut" },
      { movement: "ken-burns", transition: "fade" },
      { movement: "zoom-in", transition: "fade" },
    ],
  },
  segments: [
    { start: 0, end: 3, text: "Você sabia que GTA 6 vai mudar tudo?" },
    { start: 3, end: 8, text: "Neste vídeo mostramos as cenas mais insanas." },
  ],
};

export default function RetentionPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [topic, setTopic] = useState("GTA 6");

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) setProjectId(projects[0].id);
  }, [projects, projectId]);

  const analyzeMutation = useMutation({
    mutationFn: () =>
      api.analyzeRetention({
        project_id: projectId!,
        topic,
        payload: { ...SAMPLE_PAYLOAD, topic },
      }),
  });

  const report: RetentionReport | undefined = analyzeMutation.data;
  const maxRetention = useMemo(
    () => Math.max(100, ...(report?.timeline.map((t) => t.retention_pct) ?? [100])),
    [report]
  );

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Retention Engine</h1>
        <p className="text-sm text-muted-foreground">
          Análise segundo a segundo — curva de retenção, quedas e segmentos fracos (V5.2.1)
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
        <div className="min-w-[220px] flex-1">
          <label className="text-xs text-muted-foreground">Tópico</label>
          <Input className="mt-1" value={topic} onChange={(e) => setTopic(e.target.value)} />
        </div>
        <Button
          type="button"
          disabled={!projectId || !topic.trim() || analyzeMutation.isPending}
          onClick={() => analyzeMutation.mutate()}
        >
          {analyzeMutation.isPending ? "Analisando..." : "Analisar retenção"}
        </Button>
      </div>

      {report && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="rounded-lg border border-border bg-card p-5 lg:col-span-1">
            <h2 className="mb-4 font-semibold">Resumo</h2>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-muted-foreground">Score geral</dt>
                <dd className="text-2xl font-bold">{report.overall_score.toFixed(1)}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Hook @ 3s</dt>
                <dd>{report.hook_retention_pct.toFixed(1)}%</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Conclusão</dt>
                <dd>{report.completion_pct.toFixed(1)}%</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Média</dt>
                <dd>{report.avg_retention_pct.toFixed(1)}%</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Quedas bruscas</dt>
                <dd>{report.drop_seconds.length ? report.drop_seconds.join("s, ") + "s" : "nenhuma"}</dd>
              </div>
            </dl>
            <ul className="mt-4 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
              {report.recommendations.map((tip) => (
                <li key={tip}>{tip}</li>
              ))}
            </ul>
          </div>

          <div className="rounded-lg border border-border bg-card p-5 lg:col-span-2">
            <h2 className="mb-4 font-semibold">Curva segundo a segundo</h2>
            <div className="flex h-48 items-end gap-px overflow-x-auto rounded-md bg-muted/30 p-2">
              {report.timeline.map((point) => (
                <div
                  key={point.second}
                  className="group relative min-w-[6px] flex-1"
                  title={`${point.second}s — ${point.retention_pct.toFixed(0)}% (${point.scene_label})`}
                >
                  <div
                    className="w-full rounded-t bg-primary/80 transition-colors group-hover:bg-primary"
                    style={{ height: `${(point.retention_pct / maxRetention) * 100}%` }}
                  />
                </div>
              ))}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Duração: {report.duration_seconds.toFixed(0)}s · passe o mouse para ver cada segundo
            </p>

            {report.weak_segments.length > 0 && (
              <div className="mt-6">
                <h3 className="mb-2 text-sm font-medium">Segmentos fracos</h3>
                <div className="space-y-2">
                  {report.weak_segments.map((seg) => (
                    <div key={seg.label} className="rounded-md border border-border px-3 py-2 text-sm">
                      <span className="font-medium">{seg.label}</span>
                      <span className="text-muted-foreground">
                        {" "}
                        · {seg.start_second.toFixed(0)}–{seg.end_second.toFixed(0)}s · média{" "}
                        {seg.avg_retention_pct.toFixed(0)}%
                      </span>
                      {seg.reason && (
                        <p className="text-xs text-muted-foreground">{seg.reason}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
