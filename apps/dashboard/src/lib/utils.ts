import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR");
}

export function statusColor(status: string): string {
  const map: Record<string, string> = {
    completed: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    running: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    failed: "bg-red-500/15 text-red-400 border-red-500/30",
    pending: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
    retrying: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  };
  return map[status] || "bg-muted text-muted-foreground border-border";
}
