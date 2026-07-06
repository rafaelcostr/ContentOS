"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { statusLabel } from "@/lib/i18n";
import { V2PipelineDiagram } from "@/components/workflow/V2PipelineDiagram";
import { WORKFLOW_OPTIONS } from "@/lib/pipeline-steps";
import { cn } from "@/lib/utils";

export default function WorkflowPage() {
  const [variant, setVariant] = useState<"v1" | "v2">("v2");
  const { data: performance } = useQuery({
    queryKey: ["performance"],
    queryFn: api.getPerformance,
  });
  const { data: templates } = useQuery({
    queryKey: ["workflow-templates"],
    queryFn: api.getWorkflows,
  });

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Orquestração</h1>
        <p className="text-sm text-muted-foreground">
          Workflow Engine — templates V1/V2, retry, DLQ e estados dos jobs
        </p>
      </header>

      <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 font-semibold">Estados do Job</h2>
          <div className="flex flex-wrap gap-2 font-mono text-xs">
            {["pending", "running", "completed", "retrying", "failed", "cancelled"].map((s) => (
              <span key={s} className="rounded-md border border-border px-2 py-1 text-xs">
                {statusLabel(s)}
              </span>
            ))}
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            Retry automático com backoff exponencial (max 3). Falhas definitivas vão para Dead Letter Queue.
          </p>
        </section>

        <section className="rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 font-semibold">Regra de Ouro</h2>
          <p className="text-sm text-muted-foreground">
            Nenhum agente conversa com outro. Toda comunicação passa pelo Workflow Engine via Redis/Celery
            e callbacks HTTP. Eventos de domínio fluem pelo Event Bus.
          </p>
          <div className="mt-4 space-y-2 text-xs text-muted-foreground">
            <p>Dashboard → API Gateway → Workflow Engine → Celery → Agente</p>
            <p>Agente → callback → Workflow Engine → Event Bus → Dashboard</p>
          </div>
        </section>
      </div>

      {templates && templates.length > 0 && (
        <section className="mb-8 rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 font-semibold">Templates disponíveis</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            {templates.map((t) => (
              <div key={t.name} className="rounded-md border border-border px-4 py-3 text-sm">
                <p className="font-medium">{t.name}</p>
                <p className="mt-1 text-xs text-muted-foreground">{t.description}</p>
                <p className="mt-2 font-mono text-xs text-muted-foreground">{t.steps.length} steps</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="rounded-lg border border-border bg-card p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-semibold">
            Pipeline {variant === "v2" ? "V2 Dynamic (14 steps)" : "V1 Default (9 steps)"}
          </h2>
          <div className="flex gap-2">
            {(["v2", "v1"] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setVariant(v)}
                className={cn(
                  "rounded-md border px-3 py-1.5 text-xs transition-colors",
                  variant === v
                    ? "border-primary bg-primary/15 text-primary"
                    : "border-border text-muted-foreground hover:bg-muted"
                )}
              >
                {v === "v2" ? "V2 Dynamic" : "V1 Default"}
              </button>
            ))}
          </div>
        </div>
        <p className="mb-4 text-xs text-muted-foreground">
          {WORKFLOW_OPTIONS.find((o) => o.value === (variant === "v2" ? "v2-dynamic" : "v1-default"))?.label}
          {" · "}Steps em violeta são exclusivos do V2/V3 (content sources, hook, thumbnail, analytics).
        </p>
        <V2PipelineDiagram variant={variant} performance={performance?.by_step} />
      </section>
    </div>
  );
}
