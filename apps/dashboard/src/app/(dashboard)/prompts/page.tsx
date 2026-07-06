"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, PromptDetail } from "@/lib/api";

export default function PromptsPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editorContent, setEditorContent] = useState("");
  const [previewVars, setPreviewVars] = useState('{"topic": "IA no dia a dia", "memory_context": ""}');
  const [previewResult, setPreviewResult] = useState<{ system: string; user: string } | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const { data: prompts, isLoading } = useQuery({
    queryKey: ["prompts"],
    queryFn: api.getPrompts,
  });

  const { data: selected, isFetching } = useQuery({
    queryKey: ["prompt", selectedId],
    queryFn: () => api.getPrompt(selectedId!),
    enabled: !!selectedId,
  });

  useEffect(() => {
    if (selected) {
      setEditorContent(selected.raw_content || buildRawFromDetail(selected));
    }
  }, [selected]);

  const saveMutation = useMutation({
    mutationFn: () => api.updatePrompt(selectedId!, editorContent),
    onSuccess: () => {
      setMessage("Prompt salvo — hot reload ativo para novos jobs.");
      queryClient.invalidateQueries({ queryKey: ["prompts"] });
      queryClient.invalidateQueries({ queryKey: ["prompt", selectedId] });
    },
    onError: (err: Error) => setMessage(err.message),
  });

  function selectPrompt(id: string) {
    setSelectedId(id);
    setPreviewResult(null);
    setMessage(null);
  }

  function loadEditor(detail: PromptDetail) {
    setEditorContent(detail.raw_content || buildRawFromDetail(detail));
  }

  async function handlePreview() {
    if (!selectedId) return;
    try {
      const variables = JSON.parse(previewVars) as Record<string, string>;
      const result = await api.renderPrompt(selectedId, variables);
      setPreviewResult(result);
      setMessage(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao renderizar preview");
    }
  }

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Prompt Manager</h1>
        <p className="text-sm text-muted-foreground">
          Prompts versionados em Markdown — edite sem rebuild (V2.2)
        </p>
      </header>

      {message && (
        <div className="mb-4 rounded-lg border border-border bg-muted/50 px-4 py-3 text-sm">{message}</div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <aside className="lg:col-span-3">
          <div className="rounded-lg border border-border bg-card">
            <div className="border-b border-border px-4 py-3">
              <h2 className="text-sm font-semibold">Agentes</h2>
            </div>
            {isLoading && <p className="p-4 text-sm text-muted-foreground">Carregando...</p>}
            <ul className="divide-y divide-border">
              {prompts?.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => selectPrompt(p.id)}
                    className={`w-full px-4 py-3 text-left text-sm transition-colors hover:bg-muted/50 ${
                      selectedId === p.id ? "bg-primary/10 text-primary" : ""
                    }`}
                  >
                    <span className="font-medium">{p.id}</span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">
                      v{p.version} · {p.source}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </aside>

        <main className="lg:col-span-9 space-y-6">
          {!selectedId && (
            <div className="rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
              Selecione um prompt para editar ou visualizar
            </div>
          )}

          {selectedId && selected && !isFetching && (
            <>
              <div className="rounded-lg border border-border bg-card p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="text-lg font-semibold">{selected.id}</h2>
                    <p className="text-sm text-muted-foreground">{selected.description || selected.agent}</p>
                  </div>
                  <div className="flex gap-2 text-xs">
                    <span className="rounded-full bg-muted px-2 py-1">v{selected.version}</span>
                    <span className="rounded-full bg-muted px-2 py-1">{selected.source}</span>
                  </div>
                </div>
                <p className="mt-3 text-xs text-muted-foreground">
                  Variáveis: {selected.variables.join(", ") || "—"}
                </p>
              </div>

              <div className="rounded-lg border border-border bg-card p-4">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="font-semibold">Editor (.md)</h3>
                  <button
                    type="button"
                    onClick={() => loadEditor(selected)}
                    className="text-xs text-primary hover:underline"
                  >
                    Carregar conteúdo atual
                  </button>
                </div>
                <textarea
                  className="min-h-[280px] w-full rounded-md border border-border bg-background p-3 font-mono text-xs"
                  value={editorContent}
                  onChange={(e) => setEditorContent(e.target.value)}
                  placeholder="Cole ou edite o arquivo .md com frontmatter YAML..."
                />
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    disabled={!editorContent || saveMutation.isPending}
                    onClick={() => saveMutation.mutate()}
                    className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
                  >
                    {saveMutation.isPending ? "Salvando..." : "Salvar (hot reload)"}
                  </button>
                </div>
              </div>

              <div className="rounded-lg border border-border bg-card p-4">
                <h3 className="mb-3 font-semibold">Preview</h3>
                <textarea
                  className="mb-3 w-full rounded-md border border-border bg-background p-3 font-mono text-xs"
                  rows={3}
                  value={previewVars}
                  onChange={(e) => setPreviewVars(e.target.value)}
                />
                <button
                  type="button"
                  onClick={handlePreview}
                  className="rounded-md border border-border px-4 py-2 text-sm hover:bg-muted"
                >
                  Renderizar
                </button>
                {previewResult && (
                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap">
                      <strong>system</strong>
                      {"\n"}
                      {previewResult.system}
                    </pre>
                    <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap">
                      <strong>user</strong>
                      {"\n"}
                      {previewResult.user}
                    </pre>
                  </div>
                )}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

function buildRawFromDetail(detail: PromptDetail): string {
  const vars = detail.variables.map((v) => `  - ${v}`).join("\n");
  return `---
id: ${detail.id}
version: ${detail.version}
agent: ${detail.agent}
description: ${detail.description}
variables:
${vars}
system: |
  ${detail.system_template.replace(/\n/g, "\n  ")}
user: |
  ${detail.user_template.replace(/\n/g, "\n  ")}
---
`;
}
