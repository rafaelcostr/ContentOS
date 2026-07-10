"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { GrowthProjectSelector } from "@/components/growth/GrowthProjectSelector";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  planned: "border-border text-muted-foreground",
  dispatched: "border-emerald-500/40 text-emerald-400",
  scheduled: "border-blue-500/40 text-blue-400",
  pending_schedule: "border-amber-500/40 text-amber-400",
  post_ready: "border-violet-500/40 text-violet-400",
};

export default function GrowthCalendarPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [channelId, setChannelId] = useState<string>("");
  const queryClient = useQueryClient();

  const { data: channels = [] } = useQuery({
    queryKey: ["growth-channels", projectId],
    queryFn: () => api.getGrowthChannels(projectId!),
    enabled: Boolean(projectId),
  });

  const { data: calendar = [], isLoading } = useQuery({
    queryKey: ["growth-calendar", projectId, channelId],
    queryFn: () => api.getGrowthCalendar(projectId!, 30, channelId || undefined),
    enabled: Boolean(projectId),
  });

  const produceMutation = useMutation({
    mutationFn: (id: string) => api.produceGrowthCalendarItem(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["growth-calendar", projectId] }),
  });

  const dispatchMutation = useMutation({
    mutationFn: (id: string) => api.dispatchGrowthCalendarItem(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["growth-calendar", projectId] }),
  });

  const generatePostMutation = useMutation({
    mutationFn: (id: string) => api.generateGrowthCalendarPost(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["growth-calendar", projectId] }),
  });

  const scheduleMutation = useMutation({
    mutationFn: ({ id, mode }: { id: string; mode: "assisted" | "automatic" }) =>
      api.scheduleGrowthCalendarItem(id, mode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["growth-calendar", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-schedules", projectId] });
    },
  });

  const approveScheduleMutation = useMutation({
    mutationFn: (id: string) => api.approveGrowthCalendarSchedule(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["growth-calendar", projectId] }),
  });

  const syncSchedulesMutation = useMutation({
    mutationFn: () => api.syncGrowthCalendarSchedules(projectId!, "assisted", 5),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["growth-calendar", projectId] }),
  });

  const plannedCount = calendar.filter((item) => item.status === "planned").length;

  return (
    <div className="p-8">
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Calendário Growth</h1>
          <p className="text-sm text-muted-foreground">
            Conteúdo planejado por canal — produção, posts e agendamento (Growth OS Fase 17).
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" asChild>
            <Link href="/strategy">Estratégia</Link>
          </Button>
          <Button
            variant="outline"
            disabled={!projectId || syncSchedulesMutation.isPending || plannedCount === 0}
            onClick={() => syncSchedulesMutation.mutate()}
          >
            Agendar planejados
          </Button>
        </div>
      </header>

      <div className="mb-6 flex flex-wrap gap-4">
        <GrowthProjectSelector projectId={projectId} onProjectIdChange={setProjectId} />
        <div>
          <label className="text-xs font-medium text-muted-foreground">Canal</label>
          <select
            className="mt-1 block w-full min-w-[200px] rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={channelId}
            onChange={(e) => setChannelId(e.target.value)}
          >
            <option value="">Todos os canais</option>
            {channels.map((channel) => (
              <option key={channel.channel_id} value={channel.channel_id}>
                {channel.name} ({channel.platform})
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Carregando calendário...</p>}

      {!isLoading && calendar.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Nenhum item no calendário. Gere um plano em{" "}
          <Link href="/strategy" className="text-primary hover:underline">
            Estratégia
          </Link>
          .
        </p>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {calendar.map((item) => (
          <div key={item.id ?? item.title} className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-start justify-between gap-2">
              <p className="font-medium">{item.title}</p>
              <span className={`shrink-0 rounded border px-2 py-0.5 text-xs ${STATUS_COLORS[item.status] ?? ""}`}>
                {item.status}
              </span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              {item.planned_for ? new Date(item.planned_for).toLocaleString() : "Sem data"}
            </p>
            <p className="text-xs text-muted-foreground">
              {String(item.metadata?.platform ?? "")} · {String(item.metadata?.content_type ?? "content")}
            </p>
            {item.channel_id && (
              <p className="mt-1 text-[11px] text-muted-foreground">Canal: {item.channel_id.slice(0, 8)}…</p>
            )}

            {item.id && item.status === "planned" && (
              <div className="mt-3 flex flex-wrap gap-2">
                <Button size="sm" variant="secondary" disabled={produceMutation.isPending} onClick={() => produceMutation.mutate(item.id!)}>
                  Produzir
                </Button>
                <Button size="sm" variant="outline" disabled={generatePostMutation.isPending} onClick={() => generatePostMutation.mutate(item.id!)}>
                  Gerar post
                </Button>
                <Button size="sm" variant="outline" disabled={scheduleMutation.isPending} onClick={() => scheduleMutation.mutate({ id: item.id!, mode: "assisted" })}>
                  Agendar
                </Button>
                <Button size="sm" disabled={dispatchMutation.isPending} onClick={() => dispatchMutation.mutate(item.id!)}>
                  Dispatch
                </Button>
              </div>
            )}
            {item.id && item.status === "pending_schedule" && (
              <Button size="sm" className="mt-3" disabled={approveScheduleMutation.isPending} onClick={() => approveScheduleMutation.mutate(item.id!)}>
                Aprovar agendamento
              </Button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
