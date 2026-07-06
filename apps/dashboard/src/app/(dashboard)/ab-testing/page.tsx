"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, AbTestReport, Pipeline, Project } from "@/lib/api";

export default function AbTestingPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [pipelineId, setPipelineId] = useState<string | null>(null);
  const [topic, setTopic] = useState("");

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  const { data: pipelines = [] } = useQuery({
    queryKey: ["pipelines", projectId],
    queryFn: () => api.getPipelinesByProject(projectId!),
    enabled: !!projectId,
  });

  useEffect(() => {
    if (projects.length && !projectId) {
      setProjectId(projects[0].id);
    }
  }, [projects, projectId]);

  useEffect(() => {
    if (pipelines.length && !pipelineId) {
      setPipelineId(pipelines[0].id);
    }
  }, [pipelines, pipelineId]);

  const generateMutation = useMutation({
    mutationFn: () =>
      api.generateAbVariants({
        project_id: projectId!,
        pipeline_id: pipelineId || undefined,
        topic,
        persist: !!pipelineId,
      }),
  });

  const listMutation = useMutation({
    mutationFn: () => api.getAbVariantsByPipeline(pipelineId!),
  });

  const report: AbTestReport | undefined = generateMutation.data;

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">A/B Testing</h1>
        <p className="text-sm text-muted-foreground">
          Variantes automáticas de hook, título, CTA, thumbnail e opener (V4.1.1)
        </p>
      </header>

      <div className="mb-6 grid max-w-2xl gap-4">
        <div>
          <label className="text-xs font-medium text-muted-foreground">Projeto</label>
          <select
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={projectId ?? ""}
            onChange={(e) => {
              setProjectId(e.target.value);
              setPipelineId(null);
            }}
          >
            {projects.map((p: Project) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground">Pipeline (opcional — persiste variantes)</label>
          <select
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={pipelineId ?? ""}
            onChange={(e) => setPipelineId(e.target.value || null)}
          >
            <option value="">— sem pipeline —</option>
            {pipelines.map((p: Pipeline) => (
              <option key={p.id} value={p.id}>
                {p.topic || p.id}
              </option>
            ))}
          </select>
        </div>
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
          disabled={!topic.trim() || !projectId || generateMutation.isPending}
          onClick={() => generateMutation.mutate()}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
        >
          Gerar A/B
        </button>
        {pipelineId && (
          <button
            type="button"
            disabled={listMutation.isPending}
            onClick={() => listMutation.mutate()}
            className="rounded-md border border-border px-4 py-2 text-sm disabled:opacity-50"
          >
            Carregar pipeline
          </button>
        )}
      </div>

      {report && (
        <div className="grid max-w-4xl gap-4">
          {report.dimensions.map((dim) => (
            <div key={dim.dimension} className="rounded-lg border border-border bg-card p-4">
              <h2 className="mb-2 text-sm font-semibold capitalize">{dim.dimension}</h2>
              <ul className="space-y-2 text-sm">
                {dim.variants.map((v, i) => (
                  <li
                    key={v.variant_id}
                    className={i === dim.winner_index ? "font-medium text-primary" : "text-muted-foreground"}
                  >
                    {v.value}
                    <span className="ml-2 text-xs">({v.score.toFixed(1)})</span>
                    {i === dim.winner_index && <span className="ml-2 text-xs">← vencedor</span>}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {listMutation.data && listMutation.data.length > 0 && (
        <div className="mt-8 max-w-4xl">
          <h2 className="mb-4 text-lg font-semibold">Persistido no pipeline</h2>
          <div className="grid gap-3">
            {listMutation.data.map((row) => (
              <div key={row.id} className="rounded border border-border p-3 text-sm">
                <span className="font-medium capitalize">{row.dimension}</span>
                <span className="ml-2 text-muted-foreground">winner: {row.winner?.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
