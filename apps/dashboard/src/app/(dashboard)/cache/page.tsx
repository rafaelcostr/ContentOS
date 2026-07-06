"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, CacheStats } from "@/lib/api";

const AGENTS = ["research", "script", "scene", "publisher"];

export default function CachePage() {
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);

  const { data: stats, isLoading } = useQuery({
    queryKey: ["cache-stats"],
    queryFn: api.getCacheStats,
    refetchInterval: 10000,
  });

  const purgeMutation = useMutation({
    mutationFn: (agent: string) => api.purgeAgentCache(agent),
    onSuccess: (res) => {
      setMessage(`Removidas ${res.deleted} entradas do agente ${res.agent}.`);
      queryClient.invalidateQueries({ queryKey: ["cache-stats"] });
    },
    onError: (err: Error) => setMessage(err.message),
  });

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Cache Manager</h1>
        <p className="text-sm text-muted-foreground">
          Cache Redis para respostas de IA — evita chamadas repetidas (V2.5)
        </p>
      </header>

      {message && (
        <div className="mb-4 rounded-lg border border-border bg-muted/50 px-4 py-3 text-sm">{message}</div>
      )}

      {isLoading && <p className="text-muted-foreground">Carregando...</p>}

      {stats && (
        <div className="space-y-6">
          <div className="rounded-lg border border-border bg-card p-6">
            <div className="flex flex-wrap items-center gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Status</p>
                <p className="text-lg font-semibold">{stats.enabled ? "Ativo" : "Desativado"}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Total de chaves</p>
                <p className="text-lg font-semibold">{stats.total_keys}</p>
              </div>
              {stats.error && (
                <p className="text-sm text-amber-500">Redis: {stats.error}</p>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card p-6">
            <h2 className="mb-4 font-semibold">Por agente</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {AGENTS.map((agent) => (
                <div key={agent} className="rounded-md border border-border p-4">
                  <p className="font-medium capitalize">{agent}</p>
                  <p className="text-2xl font-bold">{stats.by_agent[agent] ?? 0}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    TTL: {formatTtl(stats.ttl_seconds[agent])}
                  </p>
                  <button
                    type="button"
                    disabled={purgeMutation.isPending}
                    onClick={() => purgeMutation.mutate(agent)}
                    className="mt-3 text-xs text-red-400 hover:underline"
                  >
                    Limpar cache
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function formatTtl(seconds: number | undefined): string {
  if (!seconds) return "—";
  if (seconds >= 86400) return `${Math.round(seconds / 86400)}d`;
  if (seconds >= 3600) return `${Math.round(seconds / 3600)}h`;
  return `${seconds}s`;
}
