"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { GrowthProjectSelector } from "@/components/growth/GrowthProjectSelector";
import { api } from "@/lib/api";

const PRIORITY_COLORS: Record<string, string> = {
  high: "text-destructive",
  medium: "text-amber-400",
  low: "text-muted-foreground",
};

export default function GrowthRecommendationsPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [channelId, setChannelId] = useState("");

  const { data: channels = [] } = useQuery({
    queryKey: ["growth-channels", projectId],
    queryFn: () => api.getGrowthChannels(projectId!),
    enabled: Boolean(projectId),
  });

  const { data: recommendations = [], isLoading } = useQuery({
    queryKey: ["growth-recommendations", projectId, channelId],
    queryFn: () => api.getGrowthRecommendations(projectId!, channelId || undefined),
    enabled: Boolean(projectId),
  });

  const bySource = recommendations.reduce<Record<string, number>>((acc, rec) => {
    acc[rec.source] = (acc[rec.source] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Recomendações Growth</h1>
        <p className="text-sm text-muted-foreground">
          Ações sugeridas por canal, performance, concorrentes e análise (Growth OS Fase 17).
        </p>
      </header>

      <div className="mb-6 flex flex-wrap gap-4">
        <GrowthProjectSelector projectId={projectId} onProjectIdChange={setProjectId} />
        <div>
          <label className="text-xs font-medium text-muted-foreground">Canal</label>
          <select
            className="mt-1 block min-w-[200px] rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={channelId}
            onChange={(e) => setChannelId(e.target.value)}
          >
            <option value="">Projeto + todos os canais</option>
            {channels.map((channel) => (
              <option key={channel.channel_id} value={channel.channel_id}>
                {channel.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {Object.keys(bySource).length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2">
          {Object.entries(bySource).map(([source, count]) => (
            <span key={source} className="rounded-md border border-border px-2 py-1 text-xs text-muted-foreground">
              {source}: {count}
            </span>
          ))}
        </div>
      )}

      {isLoading && <p className="text-sm text-muted-foreground">Carregando recomendações...</p>}

      {!isLoading && recommendations.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Nenhuma recomendação. Execute análise de canais ou{" "}
          <Link href="/performance" className="text-primary hover:underline">
            sync de performance
          </Link>
          .
        </p>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {recommendations.map((rec, index) => (
          <div key={rec.id ?? `${rec.kind}-${index}`} className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-semibold">{rec.title}</p>
              <span className={`text-xs capitalize ${PRIORITY_COLORS[String(rec.priority)] ?? ""}`}>
                {String(rec.priority)}
              </span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">{rec.detail}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-[10px] uppercase text-muted-foreground">
              <span>{rec.kind}</span>
              <span>·</span>
              <span>{rec.source}</span>
              <span>·</span>
              <span>{rec.status ?? "open"}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
