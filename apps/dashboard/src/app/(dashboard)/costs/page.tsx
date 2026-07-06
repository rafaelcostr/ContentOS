"use client";

import { useQuery } from "@tanstack/react-query";
import { api, CostOverview } from "@/lib/api";

export default function CostsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["costs-overview"],
    queryFn: api.getCostsOverview,
    refetchInterval: 15000,
  });

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Cost Manager</h1>
        <p className="text-sm text-muted-foreground">
          Uso de IA e custo estimado por projeto, pipeline e provider (V2.6)
        </p>
      </header>

      {isLoading && <p className="text-muted-foreground">Carregando...</p>}

      {data && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Custo total (USD)" value={`$${data.total_cost_usd.toFixed(4)}`} />
            <StatCard label="Operações" value={String(data.total_operations)} />
            <StatCard label="Tokens entrada" value={data.total_tokens_input.toLocaleString()} />
            <StatCard label="Tokens saída" value={data.total_tokens_output.toLocaleString()} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <BreakdownTable title="Por provider" rows={data.by_provider} />
            <BreakdownTable title="Por agente" rows={data.by_agent} />
          </div>

          <p className="text-xs text-muted-foreground">
            Providers locais (Ollama, Piper, Whisper) registram $0.00. Cache hits também custam $0.
          </p>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}

function BreakdownTable({ title, rows }: { title: string; rows: CostOverview["by_provider"] }) {
  const entries = Object.entries(rows);
  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <h2 className="mb-4 font-semibold">{title}</h2>
      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum registro ainda</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted-foreground">
              <th className="pb-2">Nome</th>
              <th className="pb-2">Ops</th>
              <th className="pb-2 text-right">USD</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {entries.map(([name, stats]) => (
              <tr key={name}>
                <td className="py-2 font-mono capitalize">{name}</td>
                <td className="py-2">{stats.operations}</td>
                <td className="py-2 text-right font-mono">${stats.cost_usd.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
