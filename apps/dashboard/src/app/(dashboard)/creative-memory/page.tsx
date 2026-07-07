"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, CreativeMemoryReport, Project } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const SAMPLE_PAYLOAD = {
  topic: "GTA 6",
  learning_report: {
    topic: "GTA 6",
    hook_text: "Você não vai acreditar no mapa de GTA 6",
    cta_text: "Comenta qual cidade você quer explorar",
    content_score: 72,
    memory_applied: true,
    memory_updates: ["hook_patterns"],
    kb_indexed_count: 2,
    signals: [{ signal_type: "hook", value: "Hook forte", score: 80, source: "pipeline" }],
  },
  knowledge_base_report: { knowledge_indexed_count: 3 },
};

export default function CreativeMemoryPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [topic, setTopic] = useState("GTA 6");

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) setProjectId(projects[0].id);
  }, [projects, projectId]);

  const mergeMutation = useMutation({
    mutationFn: () =>
      api.mergeCreativeMemory({
        project_id: projectId!,
        topic,
        payload: { ...SAMPLE_PAYLOAD, topic },
      }),
  });

  const report: CreativeMemoryReport | undefined = mergeMutation.data;

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Creative Memory</h1>
        <p className="text-sm text-muted-foreground">
          Merge KB + Learning — contexto unificado para o próximo vídeo (V5.2.5)
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
        <Button onClick={() => mergeMutation.mutate()} disabled={!projectId || mergeMutation.isPending}>
          {mergeMutation.isPending ? "Mesclando…" : "Merge KB + Learning"}
        </Button>
      </div>

      {report && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-border p-4">
              <dt className="text-xs text-muted-foreground">Memória aplicada</dt>
              <dd className="text-lg font-semibold">{report.memory_applied ? "Sim" : "Não"}</dd>
            </div>
            <div className="rounded-lg border border-border p-4">
              <dt className="text-xs text-muted-foreground">KB hits</dt>
              <dd className="text-3xl font-bold">{report.knowledge_hits.length}</dd>
            </div>
            <div className="rounded-lg border border-border p-4">
              <dt className="text-xs text-muted-foreground">Indexados</dt>
              <dd className="text-lg font-semibold">{report.knowledge_indexed_count}</dd>
            </div>
          </div>

          <section className="rounded-lg border border-border p-4">
            <h2 className="mb-2 font-semibold">creative_memory_context</h2>
            <pre className="whitespace-pre-wrap text-sm text-muted-foreground">
              {report.creative_memory_context}
            </pre>
          </section>

          {report.memory_updates.length > 0 && (
            <section className="rounded-lg border border-border p-4">
              <h2 className="mb-2 font-semibold">Atualizações de memória</h2>
              <ul className="list-inside list-disc text-sm text-muted-foreground">
                {report.memory_updates.map((u) => (
                  <li key={u}>{u}</li>
                ))}
              </ul>
            </section>
          )}

          {report.knowledge_hits.length > 0 && (
            <section className="rounded-lg border border-border p-4">
              <h2 className="mb-3 font-semibold">Knowledge hits</h2>
              <div className="space-y-3">
                {report.knowledge_hits.map((hit, i) => (
                  <div key={`${hit.title}-${i}`} className="text-sm">
                    <p className="font-medium">
                      [{hit.resource_type}] {hit.title}{" "}
                      <span className="text-muted-foreground">({(hit.similarity * 100).toFixed(0)}%)</span>
                    </p>
                    <p className="text-muted-foreground">{hit.snippet}</p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
