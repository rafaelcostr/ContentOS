"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, AgentStats } from "@/lib/api";
import { MetricBar, StatusBadge } from "@/components/dashboard/MetricBar";
import { cn } from "@/lib/utils";

function AgentCard({ agent, selected, onSelect }: { agent: AgentStats; selected: boolean; onSelect: () => void }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full rounded-lg border bg-card p-5 text-left transition-colors",
        selected ? "border-primary bg-primary/5" : "border-border hover:bg-muted/50"
      )}
    >
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-semibold capitalize">{agent.name}</h3>
        <StatusBadge status={agent.status} />
      </div>
      <p className="mb-3 text-sm text-muted-foreground">{agent.description}</p>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-muted-foreground">Provedor</span>
          <p className="font-mono capitalize">{agent.provider}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Modelo</span>
          <p className="truncate font-mono">{agent.model}</p>
        </div>
        <div>
          <span className="text-muted-foreground">Fila</span>
          <p>{agent.queue_depth} na fila</p>
        </div>
        <div>
          <span className="text-muted-foreground">Tempo médio</span>
          <p>{agent.avg_duration_seconds ? `${agent.avg_duration_seconds.toFixed(1)}s` : "—"}</p>
        </div>
      </div>
      <p className="mt-2 font-mono text-xs text-muted-foreground">{agent.queue}</p>
    </button>
  );
}

export default function AgentsPage() {
  const [selected, setSelected] = useState<string | null>(null);
  const { data: agents, isLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: api.getAgents,
    refetchInterval: 45_000,
  });

  const selectedName = selected ?? agents?.[0]?.name ?? null;
  const { data: detail } = useQuery({
    queryKey: ["agent", selectedName],
    queryFn: () => api.getAgent(selectedName!),
    enabled: !!selectedName,
    refetchInterval: 45_000,
  });

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Agentes</h1>
        <p className="text-sm text-muted-foreground">Status, fila, modelo e logs por agente</p>
      </header>

      {isLoading ? (
        <p className="text-muted-foreground">Carregando...</p>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="grid gap-4 md:grid-cols-2 lg:col-span-2 lg:grid-cols-2 xl:grid-cols-3">
            {(agents ?? []).map((a) => (
              <AgentCard
                key={a.name}
                agent={a}
                selected={detail?.name === a.name}
                onSelect={() => setSelected(a.name)}
              />
            ))}
          </div>

          {detail && (
            <section className="rounded-lg border border-border bg-card p-6 lg:col-span-1">
              <h2 className="mb-1 font-semibold capitalize">{detail.name}</h2>
              <StatusBadge status={detail.status} />

              <div className="mt-6 space-y-4">
                <div>
                  <p className="text-xs text-muted-foreground">Execuções</p>
                  <div className="mt-1 flex gap-4 text-sm">
                    <span className="text-emerald-400">{detail.completed_total} concluídas</span>
                    <span className="text-red-400">{detail.failed_total} falhas</span>
                    <span>{detail.running} executando</span>
                  </div>
                </div>

                {detail.completed_total + detail.failed_total > 0 && (
                  <MetricBar
                    label="Taxa de sucesso"
                    value={Math.round(
                      (detail.completed_total / (detail.completed_total + detail.failed_total)) * 100
                    )}
                  />
                )}

                <div>
                  <p className="text-xs text-muted-foreground">Última execução</p>
                  <p className="text-sm">
                    {detail.last_execution
                      ? new Date(detail.last_execution).toLocaleString("pt-BR")
                      : "Nunca"}
                  </p>
                </div>

                <div>
                  <p className="mb-2 text-xs text-muted-foreground">Logs recentes</p>
                  <div className="max-h-64 space-y-2 overflow-y-auto">
                    {detail.recent_logs.length === 0 ? (
                      <p className="text-sm text-muted-foreground">Sem logs</p>
                    ) : (
                      detail.recent_logs.map((log, i) => (
                        <div key={i} className="rounded-md border border-border px-3 py-2 text-xs">
                          <span className="text-muted-foreground">
                            {new Date(log.created_at).toLocaleTimeString("pt-BR")}
                          </span>
                          <p className="mt-0.5">{log.message}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
