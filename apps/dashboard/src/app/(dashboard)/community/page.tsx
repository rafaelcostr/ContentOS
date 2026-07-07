"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, CommunityDraftRow, Project } from "@/lib/api";
import { Button } from "@/components/ui/button";

const STATUS_LABELS: Record<string, string> = {
  draft: "Rascunho",
  approved: "Aprovado (não publicado)",
  dismissed: "Descartado",
};

const CATEGORY_LABELS: Record<string, string> = {
  question: "Pergunta",
  support: "Suporte",
  thanks: "Agradecimento",
  general: "Geral",
};

export default function CommunityPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) setProjectId(projects[0].id);
  }, [projects, projectId]);

  const { data: drafts = [] } = useQuery({
    queryKey: ["community-drafts", projectId],
    queryFn: () => api.getCommunityDrafts(projectId!),
    enabled: !!projectId,
  });

  const generateMutation = useMutation({
    mutationFn: () => api.generateCommunityDrafts({ project_id: projectId!, persist: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["community-drafts", projectId] }),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "approved" | "dismissed" }) =>
      api.updateCommunityDraftStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["community-drafts", projectId] }),
  });

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Community Agent</h1>
        <p className="text-sm text-muted-foreground">
          Rascunhos de resposta a comentários OAuth — V5.4.4 (sem auto-post)
        </p>
      </header>

      <div className="mb-6 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-xs text-muted-foreground">Projeto</label>
          <select
            className="mt-1 block rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={projectId ?? ""}
            onChange={(e) => setProjectId(e.target.value)}
          >
            {projects.map((p: Project) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <Button onClick={() => generateMutation.mutate()} disabled={!projectId || generateMutation.isPending}>
          {generateMutation.isPending ? "Gerando…" : "Gerar rascunhos"}
        </Button>
      </div>

      {generateMutation.data && (
        <p className="mb-6 rounded-md border border-border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
          {generateMutation.data.summary}
          {generateMutation.data.auto_post === false && (
            <span className="ml-2 text-amber-600">· Publicação automática desativada</span>
          )}
        </p>
      )}

      {drafts.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Nenhum rascunho. Conecte OAuth, sincronize métricas em /analytics e gere rascunhos.
        </p>
      ) : (
        <div className="max-w-3xl space-y-4">
          {drafts.map((row: CommunityDraftRow) => (
            <article key={row.id} className="rounded-lg border border-border p-4">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm font-medium capitalize">
                  {row.platform} · {CATEGORY_LABELS[row.category] ?? row.category}
                </span>
                <span className="text-xs text-muted-foreground">{STATUS_LABELS[row.status] ?? row.status}</span>
              </div>
              <p className="mb-2 text-xs text-muted-foreground">
                {row.comment_author ? `@${row.comment_author}: ` : ""}
                {row.original_comment}
              </p>
              <div className="rounded-md bg-muted/40 p-3 text-sm">{row.draft_reply}</div>
              {row.status === "draft" && (
                <div className="mt-3 flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={statusMutation.isPending}
                    onClick={() => statusMutation.mutate({ id: row.id, status: "approved" })}
                  >
                    Aprovar rascunho
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={statusMutation.isPending}
                    onClick={() => statusMutation.mutate({ id: row.id, status: "dismissed" })}
                  >
                    Descartar
                  </Button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
