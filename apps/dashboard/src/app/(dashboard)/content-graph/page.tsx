"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, Project } from "@/lib/api";

const TYPE_LABELS: Record<string, string> = {
  pipeline: "Pipeline",
  video: "Vídeo",
  script: "Roteiro",
  asset: "Asset",
  specialist: "Specialist",
  prompt: "Prompt",
  knowledge_entry: "KB",
  learning_insight: "Learning",
};

export default function ContentGraphPage() {
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

  const { data: graph, isLoading } = useQuery({
    queryKey: ["content-graph", projectId],
    queryFn: () => api.getProjectGraph(projectId!),
    enabled: Boolean(projectId),
  });

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Content Graph</h1>
        <p className="text-sm text-muted-foreground">
          Relações entre vídeos, roteiros, assets, specialists e KB (V4.3.1)
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

      {isLoading && <p className="text-sm text-muted-foreground">Carregando grafo…</p>}

      {graph && (
        <div className="grid max-w-5xl gap-6 lg:grid-cols-2">
          <div>
            <h2 className="mb-3 text-sm font-semibold">
              Nós ({graph.node_count})
            </h2>
            <div className="max-h-96 space-y-2 overflow-auto rounded-lg border border-border p-3">
              {graph.nodes.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  Sem nós — execute um pipeline V4 ou POST /graph/build
                </p>
              )}
              {graph.nodes.map((n) => (
                <div key={n.id} className="rounded border border-border/60 px-2 py-1.5 text-xs">
                  <span className="font-medium text-primary">{TYPE_LABELS[n.type] ?? n.type}</span>
                  <span className="text-muted-foreground"> · </span>
                  {n.label}
                </div>
              ))}
            </div>
          </div>
          <div>
            <h2 className="mb-3 text-sm font-semibold">
              Arestas ({graph.edge_count})
            </h2>
            <div className="max-h-96 space-y-2 overflow-auto rounded-lg border border-border p-3">
              {graph.edges.length === 0 && (
                <p className="text-xs text-muted-foreground">Sem relações indexadas</p>
              )}
              {graph.edges.map((e, i) => (
                <div key={`${e.source}-${e.target}-${i}`} className="text-xs text-muted-foreground">
                  <span className="text-foreground">{e.source}</span>
                  <span className="mx-1 text-primary">{e.relation}</span>
                  <span className="text-foreground">{e.target}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
