"use client";

import { cn } from "@/lib/utils";
import { statusLabel } from "@/lib/i18n";

interface MetricBarProps {
  label: string;
  value: number;
  unit?: string;
  detail?: string;
  warnAt?: number;
  criticalAt?: number;
}

export function MetricBar({ label, value, unit = "%", detail, warnAt = 70, criticalAt = 90 }: MetricBarProps) {
  const color =
    value >= criticalAt ? "bg-red-500" : value >= warnAt ? "bg-amber-500" : "bg-primary";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">
          {value}
          {unit}
          {detail && <span className="ml-1 text-xs text-muted-foreground">{detail}</span>}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div className={cn("h-full transition-all duration-500", color)} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
}

export function StatCard({ label, value, sub }: StatCardProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

const STATUS_COLORS: Record<string, string> = {
  online: "bg-emerald-500",
  running: "bg-primary animate-pulse",
  idle: "bg-muted-foreground",
  queued: "bg-amber-500",
  offline: "bg-red-500",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-2 py-0.5 text-xs">
      <span className={`h-1.5 w-1.5 rounded-full ${STATUS_COLORS[status] ?? "bg-muted"}`} />
      {statusLabel(status)}
    </span>
  );
}
