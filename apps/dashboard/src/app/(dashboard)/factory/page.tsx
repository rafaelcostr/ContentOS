"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, BatchPlan, ContentBatch, Project } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const STATUS_LABELS: Record<string, string> = {
  planned: "Planejado",
  running: "Em produção",
  pending_publish_approval: "Aguardando aprovação",
  completed: "Concluído",
  failed: "Falhou",
  cancelled: "Cancelado",
};

export default function FactoryPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [topic, setTopic] = useState("GTA 6");
  const [quantity, setQuantity] = useState(3);
  const [requireApproval, setRequireApproval] = useState(false);
  const queryClient = useQueryClient();

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) setProjectId(projects[0].id);
  }, [projects, projectId]);

  const { data: batches = [], refetch: refetchBatches } = useQuery({
    queryKey: ["factory-batches", projectId],
    queryFn: () => api.listFactoryBatches(projectId!),
    enabled: !!projectId,
  });

  const planMutation = useMutation({
    mutationFn: () =>
      api.planFactoryBatch({
        topic,
        quantity,
        require_approval: requireApproval,
        workflow_name: "v5-media-autopilot",
      }),
  });

  const estimateMutation = useMutation({
    mutationFn: () =>
      api.estimateFactoryBatch({
        project_id: projectId!,
        quantity,
      }),
  });

  const createMutation = useMutation({
    mutationFn: (autoStart: boolean) =>
      api.createFactoryBatch({
        project_id: projectId!,
        topic,
        quantity,
        require_approval: requireApproval,
        workflow_name: "v5-media-autopilot",
        auto_start: autoStart,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["factory-batches", projectId] });
    },
  });

  const startMutation = useMutation({
    mutationFn: (batchId: string) => api.startFactoryBatch(batchId),
    onSuccess: () => refetchBatches(),
  });

  const approveMutation = useMutation({
    mutationFn: (batchId: string) => api.approveFactoryBatchPublish(batchId),
    onSuccess: () => refetchBatches(),
  });

  const plan: BatchPlan | undefined = planMutation.data;

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Content Factory</h1>
        <p className="text-sm text-muted-foreground">
          N vídeos por tema com variação de ângulo e hook — lote agendado (V5.3)
        </p>
      </header>

      <div className="mb-8 flex flex-wrap items-end gap-3">
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
        <div>
          <label className="text-xs text-muted-foreground">Tema</label>
          <Input className="mt-1 w-64" value={topic} onChange={(e) => setTopic(e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">Quantidade</label>
          <Input
            className="mt-1 w-20"
            type="number"
            min={1}
            max={12}
            value={quantity}
            onChange={(e) => setQuantity(Number(e.target.value) || 1)}
          />
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={requireApproval}
            onChange={(e) => setRequireApproval(e.target.checked)}
          />
          Aprovação antes de publicar
        </label>
        <Button variant="outline" onClick={() => planMutation.mutate()} disabled={!topic}>
          Pré-visualizar
        </Button>
        <Button
          variant="outline"
          onClick={() => estimateMutation.mutate()}
          disabled={!projectId || estimateMutation.isPending}
        >
          Estimar custo
        </Button>
        <Button
          onClick={() => createMutation.mutate(false)}
          disabled={!projectId || createMutation.isPending}
        >
          Criar lote
        </Button>
        <Button
          variant="secondary"
          onClick={() => createMutation.mutate(true)}
          disabled={!projectId || createMutation.isPending}
        >
          Criar e iniciar
        </Button>
      </div>

      {estimateMutation.data && (
        <section className="mb-8 rounded-lg border border-border p-4">
          <h2 className="mb-2 font-semibold">Estimativa de custo / quota</h2>
          <p className="text-sm text-muted-foreground">
            Créditos: {estimateMutation.data.total_credit_cost} ({estimateMutation.data.credit_cost_per_pipeline}{" "}
            × {estimateMutation.data.quantity}) — quota mensal{" "}
            {estimateMutation.data.monthly_used}/{estimateMutation.data.monthly_quota || "∞"}
            {estimateMutation.data.quota_ok && estimateMutation.data.credits_ok ? (
              <span className="ml-2 text-green-600">OK</span>
            ) : (
              <span className="ml-2 text-amber-600">Verificar limites</span>
            )}
          </p>
        </section>
      )}

      {plan && (
        <section className="mb-8 rounded-lg border border-border p-4">
          <h2 className="mb-3 font-semibold">Variações planejadas ({plan.quantity})</h2>
          <div className="space-y-2">
            {plan.variants.map((v) => (
              <div key={v.index} className="rounded border border-border/60 px-3 py-2 text-sm">
                <p className="font-medium">
                  #{v.index + 1} · {v.content_angle} — {v.topic}
                </p>
                <p className="text-muted-foreground">Hook: {v.hook_hint}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="mb-4 font-semibold">Lotes recentes</h2>
        {batches.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum lote neste projeto.</p>
        ) : (
          <div className="space-y-4">
            {batches.map((batch: ContentBatch) => (
              <div key={batch.id} className="rounded-lg border border-border p-4">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium">{batch.topic}</p>
                    <p className="text-xs text-muted-foreground">
                      {STATUS_LABELS[batch.status] ?? batch.status} · {batch.quantity} vídeos ·{" "}
                      {batch.estimated_credit_cost} créditos estimados
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {batch.status === "planned" && (
                      <Button
                        size="sm"
                        onClick={() => startMutation.mutate(batch.id)}
                        disabled={startMutation.isPending}
                      >
                        Iniciar
                      </Button>
                    )}
                    {batch.require_approval && batch.status === "pending_publish_approval" && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => approveMutation.mutate(batch.id)}
                        disabled={approveMutation.isPending}
                      >
                        Aprovar publicação
                      </Button>
                    )}
                  </div>
                </div>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  {batch.variants.map((v) => (
                    <li key={v.index}>
                      {v.content_angle}: {v.topic.slice(0, 60)}
                      {v.pipeline_id ? ` — pipeline ${v.pipeline_status ?? "…"}` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
