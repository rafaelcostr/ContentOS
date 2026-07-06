"use client";

import { V1_PIPELINE_STEPS, V2_PIPELINE_STEPS } from "@/lib/pipeline-steps";
import { cn } from "@/lib/utils";

type StepStats = Record<string, Record<string, number>> | undefined;

export function V2PipelineDiagram({
  variant = "v2",
  performance,
}: {
  variant?: "v1" | "v2";
  performance?: StepStats;
}) {
  const steps = variant === "v2" ? V2_PIPELINE_STEPS : V1_PIPELINE_STEPS;

  return (
    <div className="space-y-2">
      {steps.map((step, i) => {
        const stats = performance?.[step.key];
        const isV2Only = !V1_PIPELINE_STEPS.some((s) => s.key === step.key);
        return (
          <div key={step.key} className="flex items-stretch gap-3">
            <div className="flex w-8 flex-col items-center pt-3">
              <span
                className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium",
                  isV2Only ? "bg-violet-500/20 text-violet-300" : "bg-primary/20 text-primary"
                )}
              >
                {i + 1}
              </span>
              {i < steps.length - 1 && <div className="mt-1 w-px flex-1 bg-border" />}
            </div>
            <div
              className={cn(
                "mb-1 flex flex-1 items-center justify-between rounded-md border px-4 py-3 text-sm",
                isV2Only ? "border-violet-500/30 bg-violet-500/5" : "border-border bg-card"
              )}
            >
              <div>
                <span className="font-medium">{step.label}</span>
                <span className="ml-2 font-mono text-xs text-muted-foreground">{step.key}</span>
                {isV2Only && (
                  <span className="ml-2 rounded bg-violet-500/20 px-1.5 py-0.5 text-[10px] text-violet-300">
                    V2
                  </span>
                )}
              </div>
              {stats && (
                <span className="text-xs text-muted-foreground">
                  {stats.completed ?? 0} ok · {stats.failed ?? 0} fail
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
