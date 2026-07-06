"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, AgentModelConfig } from "@/lib/api";

export default function ModelsPage() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<AgentModelConfig | null>(null);
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const { data: models, isLoading } = useQuery({
    queryKey: ["models"],
    queryFn: api.getAgentModels,
  });

  const { data: catalog } = useQuery({
    queryKey: ["models-catalog"],
    queryFn: api.getModelCatalog,
  });

  useEffect(() => {
    if (editing) {
      setProvider(editing.provider);
      setModel(editing.model);
    }
  }, [editing]);

  const saveMutation = useMutation({
    mutationFn: () => api.updateAgentModel(editing!.agent, provider, model),
    onSuccess: () => {
      setMessage("Configuração salva. Workers aplicam em até 30s (cache).");
      queryClient.invalidateQueries({ queryKey: ["models"] });
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const providerOptions = editing && catalog
    ? catalog[editing.provider_type as keyof typeof catalog] ?? []
    : [];

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Model Manager</h1>
        <p className="text-sm text-muted-foreground">
          Provider e modelo por agente — sem rebuild (V2.3)
        </p>
      </header>

      {message && (
        <div className="mb-4 rounded-lg border border-border bg-muted/50 px-4 py-3 text-sm">{message}</div>
      )}

      {isLoading && <p className="text-muted-foreground">Carregando...</p>}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Agente</th>
                  <th className="px-4 py-3">Tipo</th>
                  <th className="px-4 py-3">Provider</th>
                  <th className="px-4 py-3">Modelo</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border bg-card">
                {models?.map((m) => (
                  <tr key={m.agent} className={editing?.agent === m.agent ? "bg-primary/5" : ""}>
                    <td className="px-4 py-3 font-medium capitalize">{m.agent}</td>
                    <td className="px-4 py-3 text-muted-foreground">{m.provider_type}</td>
                    <td className="px-4 py-3 font-mono text-xs">{m.provider}</td>
                    <td className="max-w-[200px] truncate px-4 py-3 font-mono text-xs">{m.model}</td>
                    <td className="px-4 py-3 text-right">
                      {m.editable ? (
                        <button
                          type="button"
                          onClick={() => {
                            setEditing(m);
                            setMessage(null);
                          }}
                          className="text-xs text-primary hover:underline"
                        >
                          Editar
                        </button>
                      ) : (
                        <span className="text-xs text-muted-foreground">fixo</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <aside className="lg:col-span-5">
          {editing ? (
            <div className="rounded-lg border border-border bg-card p-6">
              <h2 className="text-lg font-semibold capitalize">Editar: {editing.agent}</h2>
              <p className="mt-1 text-sm text-muted-foreground">Tipo: {editing.provider_type}</p>

              <label className="mt-4 block text-xs font-medium text-muted-foreground">Provider</label>
              <select
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              >
                {providerOptions.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>

              <label className="mt-4 block text-xs font-medium text-muted-foreground">Modelo / voz</label>
              <input
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="ex: qwen2.5:7b"
              />

              <div className="mt-6 flex gap-2">
                <button
                  type="button"
                  disabled={saveMutation.isPending || !provider || !model}
                  onClick={() => saveMutation.mutate()}
                  className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
                >
                  {saveMutation.isPending ? "Salvando..." : "Salvar"}
                </button>
                <button
                  type="button"
                  onClick={() => setEditing(null)}
                  className="rounded-md border border-border px-4 py-2 text-sm hover:bg-muted"
                >
                  Cancelar
                </button>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
              Selecione um agente editável para configurar provider e modelo
            </div>
          )}

          <div className="mt-6 rounded-lg border border-border bg-card p-4 text-xs text-muted-foreground">
            <p className="font-medium text-foreground">Dica</p>
            <p className="mt-2">
              Texto: ollama, openai, claude, gemini… Voz: piper, elevenlabs. Legendas: local, openai.
              Requer <code className="text-foreground">USE_AI_GATEWAY=true</code> para providers cloud.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
