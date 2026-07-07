"use client";

import { useQuery } from "@tanstack/react-query";
import { api, type PlatformPublicationAttempt } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface PublishAttemptsProps {
  projectId: string;
  embedded?: boolean;
}

function statusVariant(status: string): "default" | "secondary" | "outline" | "destructive" {
  if (status === "published") return "default";
  if (status === "failed" || status === "blocked_qa") return "destructive";
  if (status === "dry_run" || status === "ready") return "secondary";
  return "outline";
}

export function PublishAttempts({ projectId, embedded = false }: PublishAttemptsProps) {
  const { data: attempts = [], isLoading } = useQuery({
    queryKey: ["publish-attempts", projectId],
    queryFn: () => api.getPublishAttempts(projectId),
    enabled: Boolean(projectId),
    refetchInterval: 60_000,
  });

  const body = (
    <>
      {isLoading && <p className="text-sm text-muted-foreground">Carregando tentativas…</p>}
      {!isLoading && attempts.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Nenhuma tentativa registrada. Execute um pipeline até o step publisher.
        </p>
      )}
      {attempts.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="pb-2 pr-3">Data</th>
                <th className="pb-2 pr-3">Plataforma</th>
                <th className="pb-2 pr-3">Modo</th>
                <th className="pb-2 pr-3">Status</th>
                <th className="pb-2 pr-3">Título</th>
                <th className="pb-2 pr-3">ID / URL</th>
              </tr>
            </thead>
            <tbody>
              {attempts.map((row: PlatformPublicationAttempt) => (
                <tr key={row.id} className="border-b border-border/60 align-top">
                  <td className="py-2 pr-3 whitespace-nowrap text-xs text-muted-foreground">
                    {row.created_at ? new Date(row.created_at).toLocaleString() : "—"}
                  </td>
                  <td className="py-2 pr-3 capitalize">{row.platform}</td>
                  <td className="py-2 pr-3">
                    <Badge variant="outline">{row.publish_mode}</Badge>
                  </td>
                  <td className="py-2 pr-3">
                    <Badge variant={statusVariant(row.status)}>{row.status}</Badge>
                  </td>
                  <td className="py-2 pr-3 max-w-[180px] truncate" title={row.title ?? ""}>
                    {row.title ?? "—"}
                  </td>
                  <td className="py-2 pr-3 text-xs">
                    {row.external_id && <div className="font-mono">{row.external_id}</div>}
                    {row.publish_url && (
                      <a
                        href={row.publish_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary hover:underline break-all"
                      >
                        {row.publish_url}
                      </a>
                    )}
                    {row.error && (
                      <p className="mt-1 text-destructive" title={row.error}>
                        {row.error.slice(0, 120)}
                        {row.error.length > 120 ? "…" : ""}
                      </p>
                    )}
                    {!row.external_id && !row.publish_url && !row.error && "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );

  if (embedded) {
    return (
      <section className="mt-6 border-t border-border pt-6 space-y-3">
        <div>
          <h3 className="text-sm font-semibold">Histórico de publicação</h3>
          <p className="text-xs text-muted-foreground">
            Audit log por plataforma — requer migration 022 (`platform_publications`).
          </p>
        </div>
        {body}
      </section>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Histórico de publicação</CardTitle>
        <p className="text-sm text-muted-foreground">
          Audit log por plataforma — dry_run, prepare_only e live.
        </p>
      </CardHeader>
      <CardContent>{body}</CardContent>
    </Card>
  );
}
