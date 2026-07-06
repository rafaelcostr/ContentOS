"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

export default function AssetCollectorPage() {
  const { data: agents } = useQuery({ queryKey: ["agents"], queryFn: api.getAgents, refetchInterval: 45_000 });
  const { data: collections } = useQuery({
    queryKey: ["pipeline-collections"],
    queryFn: () => api.getPipelineCollections(20),
    refetchInterval: 30_000,
  });
  const { data: indexStats } = useQuery({
    queryKey: ["asset-index-stats"],
    queryFn: api.getAssetIndexStats,
    refetchInterval: 45_000,
  });


  const agent = agents?.find((a) => a.name === "asset_collector");

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Asset Collector</h1>
        <p className="text-sm text-muted-foreground">
          Coleta, deduplicação SHA-256 e registro no Asset Manager (V2.10 / V2.11)
        </p>
      </header>

      {agent && (
        <div className="mb-8 grid gap-4 sm:grid-cols-4">
          <Stat label="Status" value={agent.status} />
          <Stat label="Fila" value={String(agent.queue_depth)} />
          <Stat label="Concluídos" value={String(agent.completed_total)} />
          <Stat label="Falhas" value={String(agent.failed_total)} />
        </div>
      )}

      {indexStats && (
        <div className="mb-8 grid gap-4 sm:grid-cols-3">
          <Stat label="Assets totais" value={String(indexStats.total_assets)} />
          <Stat label="Hashes indexados" value={String(indexStats.indexed_hashes ?? 0)} />
          <Stat label="Armazenamento" value={`${indexStats.total_mb} MB`} />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Coletas recentes</CardTitle>
        </CardHeader>
        <CardContent>
          {!collections?.length ? (
            <p className="text-sm text-muted-foreground">Nenhuma coleta registrada.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="pb-2">Pipeline</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">Assets</th>
                  <th className="pb-2">Cenas pesquisadas</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {collections.map((c) => (
                  <tr key={c.pipeline_id}>
                    <td className="py-2 font-mono text-xs">{c.pipeline_id.slice(0, 8)}…</td>
                    <td className="py-2">{c.status}</td>
                    <td className="py-2 font-semibold">{c.collected_assets}</td>
                    <td className="py-2">{c.candidate_scenes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  );
}
