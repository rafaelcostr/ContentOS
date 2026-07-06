"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";

export default function ContentSourcesPage() {
  const { data: sources } = useQuery({ queryKey: ["content-sources"], queryFn: api.getContentSources });
  const { data: health } = useQuery({
    queryKey: ["content-sources-health"],
    queryFn: api.getContentSourcesHealth,
    refetchInterval: 30000,
  });

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Content Sources</h1>
        <p className="text-sm text-muted-foreground">
          Fontes de mídia plugáveis para Clip Research e Asset Collector (V2.10)
        </p>
      </header>

      <div className="mb-6 flex flex-wrap gap-2">
        {(sources?.sources ?? []).map((s) => (
          <Badge key={s} variant="outline" className="font-mono">
            {s}
          </Badge>
        ))}
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {(health?.sources ?? []).map((src) => (
          <Card key={src.source_id}>
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-mono">{src.source_id}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm">
              <p className={src.healthy ? "text-emerald-600" : "text-amber-600"}>
                {src.healthy ? "online" : "offline"}
              </p>
              <p className="mt-2 text-muted-foreground">{src.message}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Pipeline V2 (Clip Research)</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="overflow-x-auto rounded-md bg-muted p-4 font-mono text-xs">
{`# Ativar após step scene (não bloqueia pipeline V1)
ENABLE_V2_CLIP_PIPELINE=true
CONTENT_SOURCES_ENABLED=local_library,own_library,rss

# Fluxo async:
scene → clip_research → asset_collector → takes usa assets coletados`}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
