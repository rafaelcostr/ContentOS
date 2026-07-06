"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type UnifiedMarketplaceItem } from "@/lib/api";

const TYPE_LABELS: Record<string, string> = {
  plugin: "Plugin",
  agent: "Agente",
  workflow: "Workflow",
  all: "Todos",
};

export default function MarketplacePage() {
  const [filter, setFilter] = useState<string>("all");

  const { data, isLoading } = useQuery({
    queryKey: ["unified-marketplace", filter],
    queryFn: () => api.getUnifiedMarketplace(filter === "all" ? undefined : filter),
    refetchInterval: 60000,
  });

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Marketplace</h1>
        <p className="text-sm text-muted-foreground">
          Plugins · Agentes · Workflows — catálogo local + remoto
        </p>
      </header>

      {data && (
        <div className="mb-6 flex flex-wrap gap-2">
          <Badge variant="outline">Total: {data.summary.total}</Badge>
          <Badge variant="outline">Plugins: {data.summary.plugin}</Badge>
          <Badge variant="outline">Agentes: {data.summary.agent}</Badge>
          <Badge variant="outline">Workflows: {data.summary.workflow}</Badge>
          {data.remote_configured && <Badge variant="secondary">Remote URL ativo</Badge>}
        </div>
      )}

      <div className="mb-6 flex flex-wrap gap-2">
        {["all", "plugin", "agent", "workflow"].map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setFilter(t)}
            className={`rounded-md px-3 py-1.5 text-sm ${
              filter === t ? "bg-primary text-primary-foreground" : "border border-border"
            }`}
          >
            {TYPE_LABELS[t]}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Carregando catálogo...</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {(data?.items ?? []).map((item: UnifiedMarketplaceItem) => (
            <Card key={item.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between gap-2">
                  <CardTitle className="text-base">{item.name}</CardTitle>
                  <Badge variant="outline">{TYPE_LABELS[item.type] ?? item.type}</Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  v{item.version} · {item.source} · {item.author}
                </p>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p className="text-muted-foreground">{item.description}</p>
                {item.type === "workflow" && item.step_count != null && (
                  <p className="text-xs text-muted-foreground">{item.step_count} steps</p>
                )}
                {item.type === "agent" && item.queue && (
                  <p className="font-mono text-xs text-muted-foreground">{item.queue}</p>
                )}
                {item.type === "plugin" && item.installed != null && (
                  <p className="text-xs">
                    {item.installed ? (item.enabled ? "ativo" : "instalado") : "disponível"}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
