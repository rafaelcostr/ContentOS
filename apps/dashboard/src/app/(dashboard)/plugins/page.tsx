"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { api } from "@/lib/api";
import { PublishConnections } from "@/components/publish/PublishConnections";
import { StatusBadge } from "@/components/dashboard/MetricBar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const PLATFORM_ICONS: Record<string, string> = {
  tiktok: "TikTok",
  youtube: "YouTube",
  instagram: "Instagram",
  telegram: "Telegram",
  discord: "Discord",
  wordpress: "WordPress",
};

export default function PluginsPage() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["platform-plugins"],
    queryFn: api.getPlatformPlugins,
    refetchInterval: 30000,
  });
  const { data: marketplace } = useQuery({
    queryKey: ["plugin-marketplace"],
    queryFn: api.getPluginMarketplace,
    refetchInterval: 30000,
  });

  const installMutation = useMutation({
    mutationFn: api.installPlugin,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plugin-marketplace"] });
      queryClient.invalidateQueries({ queryKey: ["platform-plugins"] });
    },
  });

  const enableMutation = useMutation({
    mutationFn: ({ name, enabled }: { name: string; enabled: boolean }) => api.enablePlugin(name, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plugin-marketplace"] });
      queryClient.invalidateQueries({ queryKey: ["platform-plugins"] });
    },
  });

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    const oauth = searchParams.get("oauth");
    if (oauth === "success" || oauth === "error") {
      queryClient.invalidateQueries({ queryKey: ["publish-status"] });
      queryClient.invalidateQueries({ queryKey: ["publish-channels"] });
    }
  }, [searchParams, queryClient]);

  const oauthMessage =
    searchParams.get("oauth") === "success"
      ? `Conta ${searchParams.get("platform") ?? ""} conectada com sucesso.`
      : searchParams.get("oauth") === "error"
        ? `Falha OAuth: ${searchParams.get("message") ?? "erro desconhecido"}`
        : null;

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Plugin Marketplace</h1>
        <p className="text-sm text-muted-foreground">
          TikTok · YouTube · Instagram · Telegram · Discord · WordPress — instale sem alterar o núcleo
        </p>
      </header>

      {oauthMessage && (
        <p
          className={`mb-6 rounded-md px-4 py-2 text-sm ${
            searchParams.get("oauth") === "success"
              ? "bg-green-500/10 text-green-700 dark:text-green-400"
              : "bg-destructive/10 text-destructive"
          }`}
        >
          {oauthMessage}
        </p>
      )}

      <PublishConnections projects={projects ?? []} />

      {data && (
        <div className="mb-6 flex flex-wrap gap-3">
          <Badge variant="outline">Modo: {data.publish_mode}</Badge>
          <Badge variant="outline">Ativos: {data.enabled_platforms.join(", ") || "—"}</Badge>
        </div>
      )}

      <h2 className="mb-4 text-lg font-semibold">Plugins ativos</h2>
      {isLoading ? (
        <p className="text-muted-foreground">Carregando...</p>
      ) : (
        <div className="mb-10 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {(data?.plugins ?? []).map((plugin) => (
            <Card key={plugin.name}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{PLATFORM_ICONS[plugin.name] ?? plugin.name}</CardTitle>
                  <StatusBadge status={plugin.enabled ? "online" : "idle"} />
                </div>
                <p className="text-xs text-muted-foreground">
                  v{plugin.version} · {plugin.source ?? "builtin"}
                </p>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p className="text-muted-foreground">{plugin.description}</p>
                <div className="flex flex-wrap gap-1">
                  {plugin.hooks.map((h) => (
                    <span key={h} className="rounded bg-muted px-2 py-0.5 font-mono text-xs">{h}</span>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <h2 className="mb-4 text-lg font-semibold">Marketplace</h2>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {(marketplace ?? []).map((item) => (
          <Card key={item.name} className={item.builtin ? "border-primary/20" : ""}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{PLATFORM_ICONS[item.name] ?? item.name}</CardTitle>
                {item.builtin && <Badge variant="secondary">builtin</Badge>}
              </div>
              <p className="text-xs text-muted-foreground">v{item.version}</p>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p className="text-muted-foreground">{item.description}</p>
              <div className="flex flex-wrap gap-2">
                {!item.installed && !item.builtin && (
                  <button
                    type="button"
                    disabled={installMutation.isPending}
                    onClick={() => installMutation.mutate(item.name)}
                    className="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground disabled:opacity-50"
                  >
                    Instalar
                  </button>
                )}
                {item.installed && (
                  <button
                    type="button"
                    disabled={enableMutation.isPending}
                    onClick={() => enableMutation.mutate({ name: item.name, enabled: !item.enabled })}
                    className="rounded-md border border-border px-3 py-1.5 text-xs disabled:opacity-50"
                  >
                    {item.enabled ? "Desativar" : "Ativar"}
                  </button>
                )}
                <span className="text-xs text-muted-foreground self-center">
                  {item.installed ? (item.enabled ? "ativo" : "instalado") : "não instalado"}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="mt-8">
        <CardHeader><CardTitle>Configuração</CardTitle></CardHeader>
        <CardContent>
          <pre className="overflow-x-auto rounded-md bg-muted p-4 font-mono text-xs">
{`# .env — publicação
PUBLISH_MODE=dry_run
ENABLED_PLATFORMS=tiktok,youtube,instagram
OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/oauth/callback
DASHBOARD_URL=http://localhost:3000

# YouTube (Google OAuth)
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=

# TikTok OAuth
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=

# Instagram (Meta OAuth)
META_APP_ID=
META_APP_SECRET=

# Fallback manual (live mode)
PLATFORM_CREDENTIALS_JSON={"telegram":{"bot_token":"...","chat_id":"..."}}`}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
