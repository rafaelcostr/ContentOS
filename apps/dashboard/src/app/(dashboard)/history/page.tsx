"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { GrowthProjectSelector } from "@/components/growth/GrowthProjectSelector";
import { api } from "@/lib/api";

const KIND_LABELS: Record<string, string> = {
  dispatch: "Produção",
  schedule: "Agendamento",
  post: "Post",
  analysis: "Análise",
  report: "Relatório",
};

export default function GrowthHistoryPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [kindFilter, setKindFilter] = useState("");

  const { data: events = [], isLoading } = useQuery({
    queryKey: ["growth-history", projectId],
    queryFn: () => api.getGrowthHistory(projectId!),
    enabled: Boolean(projectId),
  });

  const filtered = kindFilter ? events.filter((event) => event.kind === kindFilter) : events;
  const kinds = [...new Set(events.map((event) => event.kind))];

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Histórico Growth</h1>
        <p className="text-sm text-muted-foreground">
          Timeline de produção, posts, agendamentos e análises (Growth OS Fase 17).
        </p>
      </header>

      <div className="mb-6 flex flex-wrap items-end gap-4">
        <GrowthProjectSelector projectId={projectId} onProjectIdChange={setProjectId} />
        <div>
          <label className="text-xs font-medium text-muted-foreground">Tipo</label>
          <select
            className="mt-1 block min-w-[160px] rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={kindFilter}
            onChange={(e) => setKindFilter(e.target.value)}
          >
            <option value="">Todos</option>
            {kinds.map((kind) => (
              <option key={kind} value={kind}>
                {KIND_LABELS[kind] ?? kind}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando histórico...</p>}

      {!isLoading && filtered.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Nenhum evento registrado. Produza conteúdo pelo{" "}
          <Link href="/calendar" className="text-primary hover:underline">
            calendário
          </Link>
          .
        </p>
      )}

      <ol className="relative space-y-4 border-l border-border pl-6">
        {filtered.map((event) => (
          <li key={event.id} className="relative">
            <span className="absolute -left-[1.6rem] top-1.5 h-2.5 w-2.5 rounded-full bg-primary" />
            <div className="rounded-lg border border-border bg-card p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold">{event.title}</p>
                  <p className="text-xs text-muted-foreground">{event.detail}</p>
                </div>
                <span className="rounded border border-border px-2 py-0.5 text-[10px] uppercase text-muted-foreground">
                  {KIND_LABELS[event.kind] ?? event.kind}
                </span>
              </div>
              <p className="mt-2 text-[11px] text-muted-foreground">
                {event.occurred_at ? new Date(event.occurred_at).toLocaleString() : "—"} · {event.status}
                {event.channel_id ? ` · canal ${event.channel_id.slice(0, 8)}…` : ""}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
