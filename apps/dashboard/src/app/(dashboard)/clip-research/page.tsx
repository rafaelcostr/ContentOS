"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

export default function ClipResearchPage() {
  const { data: agents } = useQuery({ queryKey: ["agents"], queryFn: api.getAgents, refetchInterval: 45_000 });
  const { data: collections } = useQuery({
    queryKey: ["pipeline-collections"],
    queryFn: () => api.getPipelineCollections(20),
    refetchInterval: 30_000,
  });

  const { data: sources } = useQuery({ queryKey: ["content-sources"], queryFn: api.getContentSources });

  const agent = agents?.find((a) => a.name === "clip_research");

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Clip Research</h1>
        <p className="text-sm text-muted-foreground">
          Pesquisa B-roll por cena via Content Sources (V2.10)
        </p>
      </header>

      {agent && (
        <div className="mb-8 grid gap-4 sm:grid-cols-4">
          <Stat label="Status" value={agent.status} />
          <Stat label="Fila" value={String(agent.queue_depth)} />
          <Stat label="Concluídos" value={String(agent.completed_total)} />
          <Stat label="Provider" value={`${agent.provider}/${agent.model}`} />
        </div>
      )}

      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Fontes habilitadas</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-sm">{(sources?.sources ?? []).join(", ") || "—"}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Pesquisas recentes</CardTitle>
        </CardHeader>
        <CardContent>
          {!collections?.length ? (
            <p className="text-sm text-muted-foreground">
              Nenhuma pesquisa ainda. Ative ENABLE_V2_CLIP_PIPELINE=true e conclua o step scene.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="pb-2">Pipeline</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">Cenas</th>
                  <th className="pb-2">Atualizado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {collections.map((c) => (
                  <tr key={c.pipeline_id}>
                    <td className="py-2 font-mono text-xs">{c.pipeline_id.slice(0, 8)}…</td>
                    <td className="py-2">{c.status}</td>
                    <td className="py-2">{c.candidate_scenes}</td>
                    <td className="py-2 text-xs text-muted-foreground">
                      {new Date(c.updated_at).toLocaleString()}
                    </td>
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
      <p className="mt-1 font-semibold capitalize">{value}</p>
    </div>
  );
}
