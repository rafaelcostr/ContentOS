"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";

export default function AiGatewayPage() {
  const { data: status } = useQuery({ queryKey: ["providers"], queryFn: api.getProviderStatus });
  const { data: health } = useQuery({
    queryKey: ["ai-gateway-health"],
    queryFn: api.getAiGatewayHealth,
    refetchInterval: 15000,
  });
  const { data: providers } = useQuery({
    queryKey: ["providers-health"],
    queryFn: api.getProviderHealth,
    refetchInterval: 15000,
  });

  const gatewayMode = status?.mode === "ai-gateway";

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">AI Gateway</h1>
        <p className="text-sm text-muted-foreground">
          Roteamento central de IA — text, speech, subtitle (V2.1)
        </p>
      </header>

      <div className="mb-6 flex flex-wrap gap-3">
        <Badge variant={gatewayMode ? "default" : "outline"}>
          Modo: {status?.mode ?? "—"}
        </Badge>
        <Badge variant={health?.healthy ? "default" : "destructive"}>
          Gateway: {health?.healthy ? "online" : "offline"}
        </Badge>
        {status?.ai_gateway_url && (
          <Badge variant="outline" className="font-mono text-xs">
            {status.ai_gateway_url}
          </Badge>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <ProviderModeCard label="Text" active={status?.text} available={status?.available_text} />
        <ProviderModeCard label="Speech" active={status?.speech} available={status?.available_speech} />
        <ProviderModeCard label="Subtitle" active={status?.subtitle} available={status?.available_subtitle} />
      </div>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Health dos providers</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(providers?.providers ?? []).map((p) => (
              <div key={p.name} className="rounded-md border border-border p-4 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium capitalize">{p.name}</span>
                  <span className={p.healthy ? "text-emerald-500" : "text-amber-500"}>
                    {p.healthy ? "ok" : "down"}
                  </span>
                </div>
                <p className="mt-1 truncate font-mono text-xs text-muted-foreground">{p.url}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ProviderModeCard({
  label,
  active,
  available,
}: {
  label: string;
  active?: string;
  available?: string[];
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="font-mono text-lg">{active ?? "—"}</p>
        <div className="mt-3 flex flex-wrap gap-1">
          {(available ?? []).slice(0, 6).map((p) => (
            <span
              key={p}
              className={`rounded px-2 py-0.5 text-xs ${
                p === active ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
              }`}
            >
              {p}
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
