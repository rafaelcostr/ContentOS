"use client";

import { useQuery } from "@tanstack/react-query";
import { api, DomainEvent, EventStreamInfo } from "@/lib/api";

export default function EventsPage() {
  const { data: events, isLoading } = useQuery({
    queryKey: ["events-recent"],
    queryFn: () => api.getRecentEvents(100),
    refetchInterval: 15_000,
  });

  const { data: streamInfo } = useQuery({
    queryKey: ["events-stream-info"],
    queryFn: api.getEventStreamInfo,
    refetchInterval: 30_000,
  });


  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Event Bus</h1>
        <p className="text-sm text-muted-foreground">
          Eventos de pipeline, agentes e stream Redis em tempo real (V2.7)
        </p>
      </header>

      {streamInfo && <StreamInfoCard info={streamInfo} />}

      {isLoading && <p className="text-muted-foreground">Carregando eventos...</p>}

      {events && (
        <div className="mt-6 rounded-lg border border-border bg-card">
          <div className="border-b border-border px-6 py-4">
            <h2 className="font-semibold">Eventos recentes</h2>
            <p className="text-xs text-muted-foreground">{events.length} registros</p>
          </div>
          {events.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">Nenhum evento ainda. Inicie um pipeline.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-muted-foreground">
                    <th className="px-6 py-3">Timestamp</th>
                    <th className="px-6 py-3">Tipo</th>
                    <th className="px-6 py-3">Step</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3">Pipeline</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {events.map((ev, i) => (
                    <tr key={ev.id ?? ev.stream_id ?? i}>
                      <td className="px-6 py-2 font-mono text-xs text-muted-foreground">
                        {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : "—"}
                      </td>
                      <td className="px-6 py-2 font-mono">{ev.type}</td>
                      <td className="px-6 py-2 capitalize">{ev.step ?? ev.agent ?? "—"}</td>
                      <td className="px-6 py-2">
                        <StatusBadge status={ev.status} />
                      </td>
                      <td className="px-6 py-2 font-mono text-xs text-muted-foreground">
                        {ev.pipeline_id ? ev.pipeline_id.slice(0, 8) + "…" : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <p className="mt-4 text-xs text-muted-foreground">
        O WebSocket em <code className="rounded bg-muted px-1">/ws</code> continua recebendo eventos via pub/sub legado.
      </p>
    </div>
  );
}

function StreamInfoCard({ info }: { info: EventStreamInfo }) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <div className="rounded-lg border border-border bg-card p-5">
        <p className="text-xs text-muted-foreground">Stream key</p>
        <p className="mt-1 font-mono text-sm">{info.stream_key}</p>
      </div>
      <div className="rounded-lg border border-border bg-card p-5">
        <p className="text-xs text-muted-foreground">Entradas no stream</p>
        <p className="mt-1 text-2xl font-bold">{info.length ?? 0}</p>
      </div>
      <div className="rounded-lg border border-border bg-card p-5">
        <p className="text-xs text-muted-foreground">Estado</p>
        <p className="mt-1 text-sm">{info.error ? `Erro: ${info.error}` : "OK"}</p>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status?: string | null }) {
  if (!status) return <span className="text-muted-foreground">—</span>;
  const colors: Record<string, string> = {
    completed: "text-green-600",
    running: "text-blue-600",
    failed: "text-red-600",
    retrying: "text-yellow-600",
    pending: "text-muted-foreground",
  };
  return <span className={colors[status] ?? ""}>{status}</span>;
}
