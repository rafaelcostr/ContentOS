"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, KnowledgeHit, Project, ReuseSuggestion } from "@/lib/api";

export default function KnowledgePage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) {
      setProjectId(projects[0].id);
    }
  }, [projects, projectId]);

  const { data: history = [], isLoading: historyLoading } = useQuery({
    queryKey: ["knowledge-history", projectId],
    queryFn: () => api.getKnowledgeHistory(projectId!),
    enabled: !!projectId,
  });

  const searchMutation = useMutation({
    mutationFn: () =>
      api.searchKnowledge({
        project_id: projectId!,
        query,
        limit: 15,
        min_similarity: 0.0,
      }),
    onError: (err: Error) => setMessage(err.message),
  });

  const reuseMutation = useMutation({
    mutationFn: () =>
      api.suggestReuse({
        project_id: projectId!,
        topic: query,
      }),
    onError: (err: Error) => setMessage(err.message),
  });

  const hits: KnowledgeHit[] = searchMutation.data ?? [];
  const reuseSuggestions: ReuseSuggestion[] = reuseMutation.data ?? [];

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Knowledge Base</h1>
        <p className="text-sm text-muted-foreground">
          Busca semântica e histórico de roteiros, hooks, vídeos e analytics (V4)
        </p>
      </header>

      {message && (
        <div className="mb-4 rounded-lg border border-border bg-muted/50 px-4 py-3 text-sm">{message}</div>
      )}

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

      <div className="mb-8 flex max-w-2xl flex-wrap gap-2">
        <input
          className="min-w-[200px] flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
          placeholder="Buscar conteúdo similar..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && query.trim()) searchMutation.mutate();
          }}
        />
        <button
          type="button"
          disabled={!query.trim() || searchMutation.isPending}
          onClick={() => searchMutation.mutate()}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
        >
          Buscar
        </button>
        <button
          type="button"
          disabled={!query.trim() || reuseMutation.isPending}
          onClick={() => reuseMutation.mutate()}
          className="rounded-md border border-border bg-card px-4 py-2 text-sm disabled:opacity-50"
        >
          {reuseMutation.isPending ? "..." : "Sugerir reuso"}
        </button>
      </div>

      {reuseSuggestions.length > 0 && (
        <div className="mb-8 rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
          <h2 className="text-sm font-semibold">Smart Reuse — reutilizar?</h2>
          <ul className="mt-2 space-y-2">
            {reuseSuggestions.map((s, i) => (
              <li key={`${s.resource_id}-${i}`} className="text-sm">
                <span className="font-medium">{s.title}</span>
                <span className="ml-2 text-xs text-muted-foreground">
                  {(s.similarity * 100).toFixed(0)}% · {s.resource_type}
                </span>
                <p className="text-xs text-muted-foreground">{s.reason}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-6">
          <h2 className="font-semibold">Resultados da busca</h2>
          {searchMutation.isPending && <p className="mt-4 text-sm text-muted-foreground">Buscando...</p>}
          {!searchMutation.isPending && hits.length === 0 && (
            <p className="mt-4 text-sm text-muted-foreground">
              {searchMutation.isSuccess ? "Nenhum resultado." : "Digite uma query para buscar."}
            </p>
          )}
          <ul className="mt-4 space-y-3">
            {hits.map((hit, i) => (
              <li key={`${hit.resource_id}-${i}`} className="rounded-md border border-border p-3 text-sm">
                <div className="flex justify-between gap-2">
                  <span className="font-medium">{hit.title}</span>
                  <span className="text-xs text-muted-foreground">
                    {(hit.similarity * 100).toFixed(0)}% · {hit.resource_type}
                  </span>
                </div>
                <p className="mt-1 text-muted-foreground">{hit.snippet}</p>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-lg border border-border bg-card p-6">
          <h2 className="font-semibold">Histórico indexado</h2>
          {historyLoading && <p className="mt-4 text-sm text-muted-foreground">Carregando...</p>}
          {!historyLoading && history.length === 0 && (
            <p className="mt-4 text-sm text-muted-foreground">
              Nenhuma entrada. Indexe um pipeline via API POST /knowledge/index/&#123;pipeline_id&#125;.
            </p>
          )}
          <ul className="mt-4 max-h-[480px] space-y-2 overflow-y-auto">
            {history.map((entry) => (
              <li key={entry.id ?? entry.title} className="rounded-md bg-muted/50 px-3 py-2 text-sm">
                <div className="flex justify-between">
                  <span className="font-medium">{entry.title}</span>
                  <span className="text-xs text-muted-foreground">{entry.resource_type}</span>
                </div>
                <p className="text-xs text-muted-foreground line-clamp-2">{entry.snippet}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
