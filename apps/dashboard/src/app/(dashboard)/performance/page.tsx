"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { GrowthProjectSelector } from "@/components/growth/GrowthProjectSelector";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export default function GrowthPerformancePage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: performance, isLoading } = useQuery({
    queryKey: ["growth-performance", projectId],
    queryFn: () => api.getGrowthPerformance(projectId!),
    enabled: Boolean(projectId),
  });

  const syncMutation = useMutation({
    mutationFn: () => api.syncGrowthPerformance(projectId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["growth-performance", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-report", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-recommendations", projectId] });
    },
  });
  const underperformers = performance?.underperformers ?? [];

  return (
    <div className="p-8">
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Performance Growth</h1>
          <p className="text-sm text-muted-foreground">
            Interpretação pós-publicação — CTR, retenção e hooks vencedores (Fase 14/17).
          </p>
        </div>
        <Button disabled={!projectId || syncMutation.isPending} onClick={() => syncMutation.mutate()}>
          {syncMutation.isPending ? "Sincronizando..." : "Sync Performance Learning"}
        </Button>
      </header>

      <GrowthProjectSelector projectId={projectId} onProjectIdChange={setProjectId} className="mb-8" />

      {isLoading && <p className="text-sm text-muted-foreground">Carregando performance...</p>}

      {performance && (
        <div className="grid gap-6 lg:grid-cols-2">
          <section className="lg:col-span-2 rounded-lg border border-border bg-card p-5">
            <p className="text-sm text-muted-foreground">{performance.summary}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Metric label="Mídias" value={String(performance.total_media)} />
              <Metric label="Alto desempenho" value={String(performance.high_performers)} />
              <Metric label="Baixo desempenho" value={String(performance.low_performers)} />
              <Metric
                label="CTR médio"
                value={performance.avg_ctr != null ? `${(performance.avg_ctr * 100).toFixed(1)}%` : "—"}
              />
            </div>
          </section>

          {performance.opportunities.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold">Oportunidades</h2>
              <ul className="space-y-2 rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
                {performance.opportunities.map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
            </section>
          )}

          {performance.risks.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold">Riscos</h2>
              <ul className="space-y-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-amber-200/90">
                {performance.risks.map((item) => (
                  <li key={item}>• {item}</li>
                ))}
              </ul>
            </section>
          )}

          {performance.top_hooks.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold">Hooks vencedores</h2>
              <div className="space-y-2">
                {performance.top_hooks.map((hook) => (
                  <p key={hook} className="rounded-md border border-border bg-card p-3 text-sm">
                    {hook}
                  </p>
                ))}
              </div>
            </section>
          )}

          {performance.top_assets.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold">Top assets</h2>
              <div className="space-y-2">
                {performance.top_assets.map((asset, index) => (
                  <div key={index} className="rounded-md border border-border bg-card p-3 text-xs text-muted-foreground">
                    <p className="font-medium text-foreground">{String(asset.title ?? "—")}</p>
                    <p className="mt-1">
                      {String(asset.platform ?? "")} · {Number(asset.views ?? 0).toLocaleString()} views
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {underperformers.length > 0 && (
            <section className="lg:col-span-2">
              <h2 className="mb-3 text-lg font-semibold">Underperformers</h2>
              <div className="grid gap-2 md:grid-cols-2">
                {underperformers.map((asset, index) => (
                  <div key={index} className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs">
                    <p className="font-medium">{String(asset.title ?? "—")}</p>
                    <p className="mt-1 text-muted-foreground">{Number(asset.views ?? 0).toLocaleString()} views</p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      <p className="mt-8 text-xs text-muted-foreground">
        Ver também: <Link href="/growth" className="text-primary hover:underline">Growth AI</Link> ·{" "}
        <Link href="/recommendations" className="text-primary hover:underline">Recomendações</Link>
      </p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-muted/20 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value}</p>
    </div>
  );
}
