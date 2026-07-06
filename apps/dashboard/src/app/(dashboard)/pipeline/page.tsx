"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useWorkflowSocket } from "@/hooks/useWorkflowSocket";

const STEPS = [
  { key: "research", label: "Pesquisa" },
  { key: "script", label: "Roteiro" },
  { key: "scene", label: "Cenas" },
  { key: "takes", label: "Takes" },
  { key: "voice", label: "Voz" },
  { key: "subtitle", label: "Legendas" },
  { key: "editor", label: "Editor" },
  { key: "quality", label: "Qualidade" },
  { key: "publisher", label: "Publicação" },
];

export default function PipelinePage() {
  const { events, connected } = useWorkflowSocket();
  const { data: analytics } = useQuery({ queryKey: ["analytics"], queryFn: api.getAnalytics });

  const runningStep = events.find((e) => e.status === "running")?.step;

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Fluxo de produção</h1>
        <p className="text-sm text-muted-foreground">
          9 agentes sequenciais · Conexão {connected ? "ativa" : "inativa"}
        </p>
      </header>

      <div className="mb-8 grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Pipelines totais</p>
          <p className="text-xl font-semibold">{analytics?.pipelines_total ?? 0}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Concluídos</p>
          <p className="text-xl font-semibold">{analytics?.pipelines_completed ?? 0}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Fila pendente</p>
          <p className="text-xl font-semibold">{analytics?.queue_pending ?? 0}</p>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-card p-8">
        <div className="mx-auto flex max-w-md flex-col items-center gap-2">
          {STEPS.map((step, i) => {
            const isActive = runningStep === step.key;
            const isDone = events.some((e) => e.step === step.key && e.status === "completed");
            return (
              <div key={step.key} className="flex w-full flex-col items-center">
                <div
                  className={`w-full rounded-md border px-4 py-3 text-center text-sm ${
                    isActive
                      ? "border-primary bg-primary/15 text-primary"
                      : isDone
                        ? "border-emerald-500/50 bg-emerald-500/10"
                        : "border-border"
                  }`}
                >
                  {step.label}
                </div>
                {i < STEPS.length - 1 && <span className="text-muted-foreground">↓</span>}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
