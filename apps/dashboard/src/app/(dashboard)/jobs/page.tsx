"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, Pipeline, PipelineDetail } from "@/lib/api";
import { useWorkflowSocket, WorkflowEvent } from "@/hooks/useWorkflowSocket";
import { cn } from "@/lib/utils";
import { statusLabel } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { stepsForPipeline } from "@/lib/pipeline-steps";
const STATUS_STYLE: Record<string, string> = {
  pending: "border-border text-muted-foreground",
  running: "border-primary bg-primary/15 text-primary animate-pulse",
  completed: "border-emerald-500/60 bg-emerald-500/10 text-emerald-400",
  failed: "border-red-500/60 bg-red-500/10 text-red-400",
  retrying: "border-amber-500/60 bg-amber-500/10 text-amber-400",
  cancelled: "border-border text-muted-foreground line-through",
};

function StepIcon({ status }: { status: string }) {
  if (status === "completed") return <span className="text-emerald-400">✓</span>;
  if (status === "failed") return <span className="text-red-400">✗</span>;
  if (status === "running") return <span className="inline-block h-2 w-2 rounded-full bg-primary" />;
  if (status === "retrying") return <span className="text-amber-400">↻</span>;
  return <span className="text-muted-foreground">○</span>;
}

export default function JobsPage() {
  const queryClient = useQueryClient();
  const { events, connected } = useWorkflowSocket();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: pipelines = [], isLoading } = useQuery({
    queryKey: ["pipelines"],
    queryFn: api.getPipelines,
    refetchInterval: connected ? false : 15_000,
  });

  const activeId = selectedId ?? pipelines.find((p) => p.status === "running")?.id ?? pipelines[0]?.id;

  const { data: detail, refetch: refetchDetail } = useQuery({
    queryKey: ["pipeline", activeId],
    queryFn: () => api.getPipelineDetail(activeId!),
    enabled: !!activeId,
    refetchInterval: (q) => {
      if (connected) return false;
      const status = q.state.data?.status;
      return status === "running" || status === "pending" ? 10_000 : false;
    },
  });

  const invalidateTimer = useRef<ReturnType<typeof setTimeout>>();

  const onWsEvent = useCallback(
    (event: WorkflowEvent) => {
      if (!event.pipeline_id) return;
      clearTimeout(invalidateTimer.current);
      invalidateTimer.current = setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["pipelines"] });
        if (event.pipeline_id === activeId || !selectedId) {
          queryClient.invalidateQueries({ queryKey: ["pipeline", event.pipeline_id] });
        }
      }, 750);
    },
    [activeId, selectedId, queryClient]
  );

  useEffect(() => {
    if (events[0]) onWsEvent(events[0]);
  }, [events, onWsEvent]);

  const steps = useMemo(
    () => stepsForPipeline(detail?.jobs ?? [], detail?.workflow_name),
    [detail?.jobs, detail?.workflow_name]
  );

  const jobMap = useMemo(() => {
    const map: Record<string, PipelineDetail["jobs"][0]> = {};
    detail?.jobs.forEach((j) => {
      map[j.step] = j;
    });
    return map;
  }, [detail]);

  const progress = detail
    ? Math.round((detail.jobs.filter((j) => j.status === "completed").length / steps.length) * 100)
    : 0;

  const canStop = detail && (detail.status === "running" || detail.status === "pending");

  const cancelMutation = useMutation({
    mutationFn: (id: string) => api.cancelPipeline(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      queryClient.invalidateQueries({ queryKey: ["pipeline", id] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deletePipeline(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      queryClient.removeQueries({ queryKey: ["pipeline", id] });
      if (selectedId === id) setSelectedId(null);
    },
  });

  const handleDelete = () => {
    if (!detail) return;
    if (!window.confirm(`Excluir o pipeline "${detail.topic}"? Esta ação não pode ser desfeita.`)) return;
    deleteMutation.mutate(detail.id);
  };

  const handleStop = () => {
    if (!detail) return;
    if (!window.confirm(`Parar o pipeline "${detail.topic}"? Os steps em andamento serão cancelados.`)) return;
    cancelMutation.mutate(detail.id);
  };

  return (
    <div className="p-8">
      <header className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Produção</h1>
          <p className="text-sm text-muted-foreground">
            Pipelines em tempo real · Conexão {connected ? "ativa" : "inativa"}
          </p>
        </div>
        {detail && (
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Progresso</p>
            <p className="text-2xl font-semibold">{progress}%</p>
          </div>
        )}
      </header>

      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="rounded-lg border border-border bg-card p-4 lg:col-span-1">
          <h2 className="mb-3 text-sm font-semibold">Pipelines recentes</h2>
          {isLoading && <p className="text-sm text-muted-foreground">Carregando...</p>}
          <div className="max-h-80 space-y-2 overflow-y-auto">
            {pipelines.map((p: Pipeline) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setSelectedId(p.id)}
                className={cn(
                  "w-full rounded-md border px-3 py-2 text-left text-sm transition-colors",
                  activeId === p.id ? "border-primary bg-primary/10" : "border-border hover:bg-muted"
                )}
              >
                <p className="truncate font-medium">{p.topic}</p>
                <p className="text-xs text-muted-foreground">
                  {statusLabel(p.status)} {p.current_step ? `· ${p.current_step}` : ""}
                </p>
              </button>
            ))}
            {!isLoading && pipelines.length === 0 && (
              <p className="text-sm text-muted-foreground">Nenhum pipeline ainda. Crie um em Projetos.</p>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-border bg-card p-6 lg:col-span-2">
          {!detail ? (
            <p className="text-sm text-muted-foreground">Selecione um pipeline</p>
          ) : (
            <>
              <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-semibold">{detail.topic}</h2>
                  <p className="text-xs text-muted-foreground font-mono">{detail.id}</p>
                  {detail.workflow_name && (
                    <p className="text-xs text-muted-foreground">Workflow: {detail.workflow_name}</p>
                  )}
                </div>
                <div className="flex shrink-0 flex-col items-end gap-2">
                  <span className={cn("rounded-full px-3 py-1 text-xs", STATUS_STYLE[detail.status])}>
                    {statusLabel(detail.status)}
                  </span>
                  <div className="flex gap-2">
                    {canStop && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={cancelMutation.isPending}
                        onClick={handleStop}
                      >
                        {cancelMutation.isPending ? "Parando..." : "Parar"}
                      </Button>
                    )}
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={deleteMutation.isPending}
                      className="border-red-500/40 text-red-400 hover:bg-red-500/10"
                      onClick={handleDelete}
                    >
                      {deleteMutation.isPending ? "Excluindo..." : "Excluir"}
                    </Button>
                  </div>
                </div>
              </div>

              <div className="mb-4 h-2 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full bg-primary transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>

              <div className="space-y-2">
                {steps.map((step, i) => {
                  const job = jobMap[step.key];
                  const status = job?.status ?? "pending";
                  const isLive = events.some(
                    (e) => e.pipeline_id === detail.id && e.step === step.key && e.status === "running"
                  );
                  return (
                    <div key={step.key} className="flex items-stretch gap-3">
                      <div className="flex w-6 flex-col items-center pt-3">
                        <StepIcon status={isLive ? "running" : status} />
                        {i < steps.length - 1 && <div className="mt-1 w-px flex-1 bg-border" />}
                      </div>
                      <div
                        className={cn(
                          "flex flex-1 items-center justify-between rounded-md border px-4 py-3 text-sm",
                          STATUS_STYLE[isLive ? "running" : status]
                        )}
                      >
                        <div>
                          <span className="font-medium">{step.label}</span>
                          <span className="ml-2 font-mono text-xs opacity-60">{step.key}</span>
                        </div>
                        <div className="text-right text-xs">
                          <p>{statusLabel(status)}</p>
                          {job?.error_message && (
                            <p className="mt-1 max-w-xs truncate text-red-400">{job.error_message}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {detail.error_message && (
                <div className="mt-4 rounded-md border border-red-500/50 bg-red-500/10 p-3 text-sm text-red-400">
                  {detail.error_message}
                </div>
              )}

              <button
                type="button"
                onClick={() => refetchDetail()}
                className="mt-4 text-xs text-muted-foreground hover:text-foreground"
              >
                Atualizar agora
              </button>
            </>
          )}
        </section>
      </div>

      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="mb-2 text-sm font-semibold">Eventos em tempo real</h2>
        <div className="max-h-32 overflow-y-auto font-mono text-xs text-muted-foreground">
          {events.length === 0 ? (
            <p>Aguardando eventos...</p>
          ) : (
            events.slice(0, 10).map((e, i) => (
              <div key={i}>
                [{e.type}] {e.step ?? "—"} — {e.status}
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
