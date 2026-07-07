"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Project } from "@/lib/api";
import { PublishAttempts } from "@/components/publish/PublishAttempts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const PLATFORMS = [
  { id: "youtube", label: "YouTube" },
  { id: "tiktok", label: "TikTok" },
  { id: "instagram", label: "Instagram" },
] as const;

interface PublishConnectionsProps {
  projects: Project[];
}

export function PublishConnections({ projects }: PublishConnectionsProps) {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState(projects[0]?.id ?? "");

  const { data: status } = useQuery({
    queryKey: ["publish-status", projectId],
    queryFn: () => api.getPublishStatus(projectId || undefined),
    enabled: Boolean(projectId),
  });

  const { data: channels } = useQuery({
    queryKey: ["publish-channels", projectId],
    queryFn: () => api.getPublishChannels(projectId),
    enabled: Boolean(projectId),
  });

  const startOAuth = useMutation({
    mutationFn: ({ platform }: { platform: string }) =>
      api.startOAuth(platform, projectId),
    onSuccess: (data) => {
      window.location.href = data.authorize_url;
    },
  });

  const disconnect = useMutation({
    mutationFn: (channelId: string) => api.disconnectPublishChannel(channelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["publish-channels", projectId] });
      queryClient.invalidateQueries({ queryKey: ["publish-status", projectId] });
      queryClient.invalidateQueries({ queryKey: ["publish-attempts", projectId] });
    },
  });

  if (!projects.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Conectar plataformas (OAuth)</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Crie um projeto para conectar YouTube, TikTok ou Instagram.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Conectar plataformas (OAuth)</CardTitle>
        <p className="text-sm text-muted-foreground">
          Tokens OAuth são salvos no canal do projeto e usados pelo agente publisher em modo live.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm text-muted-foreground" htmlFor="publish-project">
            Projeto
          </label>
          <select
            id="publish-project"
            className="rounded-md border border-border bg-background px-3 py-1.5 text-sm"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          {status && (
            <>
              <Badge variant={status.live_enabled ? "default" : "outline"}>
                Modo: {status.publish_mode}
              </Badge>
              {status.prepare_only_enabled && <Badge variant="secondary">prepare_only</Badge>}
              {status.dry_run_enabled && <Badge variant="outline">dry_run</Badge>}
              {status.publish_require_qa && <Badge variant="outline">QA gate</Badge>}
              {!status.live_enabled && (
                <span className="text-xs text-muted-foreground">
                  Promova PUBLISH_MODE: dry_run → prepare_only → live no servidor.
                </span>
              )}
            </>
          )}
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          {PLATFORMS.map(({ id, label }) => {
            const platformStatus = status?.platforms.find((p) => p.platform === id);
            const channel = channels?.find((c) => c.platform === id && c.oauth_connected);
            const oauthAvailable = platformStatus?.oauth_available ?? false;

            return (
              <div key={id} className="rounded-lg border border-border p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{label}</span>
                  <Badge variant={channel ? "default" : "secondary"}>
                    {channel ? "Conectado" : "Desconectado"}
                  </Badge>
                </div>
                {!oauthAvailable && (
                  <p className="text-xs text-muted-foreground">
                    OAuth não configurado no servidor (client id/secret).
                  </p>
                )}
                {channel ? (
                  <div className="space-y-2">
                    <p className="text-xs text-muted-foreground truncate">{channel.name}</p>
                    <button
                      type="button"
                      disabled={disconnect.isPending}
                      onClick={() => disconnect.mutate(channel.id)}
                      className="rounded-md border border-border px-3 py-1.5 text-xs disabled:opacity-50"
                    >
                      Desconectar
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    disabled={!oauthAvailable || !projectId || startOAuth.isPending}
                    onClick={() => startOAuth.mutate({ platform: id })}
                    className="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground disabled:opacity-50"
                  >
                    Conectar via OAuth
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
      {projectId && (
        <div className="px-6 pb-6">
          <PublishAttempts projectId={projectId} embedded />
        </div>
      )}
    </Card>
  );
}
