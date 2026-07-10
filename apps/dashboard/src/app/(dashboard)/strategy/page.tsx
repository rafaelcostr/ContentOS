"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { api, Project } from "@/lib/api";

export default function StrategyPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) setProjectId(projects[0].id);
  }, [projects, projectId]);

  const { data: strategy, isLoading } = useQuery({
    queryKey: ["growth-strategy", projectId],
    queryFn: () => api.getGrowthStrategy(projectId!),
    enabled: Boolean(projectId),
  });

  const { data: calendar = [] } = useQuery({
    queryKey: ["growth-calendar", projectId],
    queryFn: () => api.getGrowthCalendar(projectId!),
    enabled: Boolean(projectId),
  });

  const generateMutation = useMutation({
    mutationFn: () => api.generateGrowthStrategy(projectId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["growth-strategy", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-calendar", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-report", projectId] });
    },
  });

  const produceMutation = useMutation({
    mutationFn: (calendarItemId: string) => api.produceGrowthCalendarItem(calendarItemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["growth-calendar", projectId] });
    },
  });

  const dispatchMutation = useMutation({
    mutationFn: (calendarItemId: string) => api.dispatchGrowthCalendarItem(calendarItemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["growth-calendar", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-posts", projectId] });
    },
  });

  const generatePostMutation = useMutation({
    mutationFn: (calendarItemId: string) => api.generateGrowthCalendarPost(calendarItemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["growth-calendar", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-posts", projectId] });
    },
  });

  const produceBatchMutation = useMutation({
    mutationFn: () => api.producePlannedGrowthCalendar(projectId!, 3),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["growth-calendar", projectId] });
    },
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
    mutationFn: (calendarItemId: string) => api.approveGrowthCalendarSchedule(calendarItemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["growth-calendar", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-schedules", projectId] });
    },
  });

  const syncSchedulesMutation = useMutation({
    mutationFn: () => api.syncGrowthCalendarSchedules(projectId!, "assisted", 5),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["growth-calendar", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-schedules", projectId] });
    },
  });

  const campaigns = (strategy?.cadence?.campaigns as Array<Record<string, unknown>> | undefined) ?? [];
  const channelGoals = (strategy?.cadence?.channel_goals as Record<string, string[]> | undefined) ?? {};

  return (
    <div className="p-8">
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Estratégia de Conteúdo</h1>
          <p className="text-sm text-muted-foreground">
            Plano semanal/mensal gerado pelo Content Strategist AI (Growth OS Fase 9).
          </p>
        </div>
        <Button disabled={!projectId || generateMutation.isPending} onClick={() => generateMutation.mutate()}>
          {generateMutation.isPending ? "Gerando plano..." : "Gerar plano (30 dias)"}
        </Button>
        <Button
          variant="outline"
          disabled={!projectId || syncSchedulesMutation.isPending || !calendar.some((i) => i.status === "planned")}
          onClick={() => syncSchedulesMutation.mutate()}
        >
          {syncSchedulesMutation.isPending ? "Agendando..." : "Agendar planejados (assistido)"}
        </Button>
      </header>

      <div className="mb-6">
        <label className="text-xs font-medium text-muted-foreground">Projeto</label>
        <select
          className="mt-1 block w-full max-w-md rounded-md border border-border bg-background px-3 py-2 text-sm"
          value={projectId ?? ""}
          onChange={(event) => setProjectId(event.target.value)}
        >
          {projects.map((project: Project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
      </div>

      {generateMutation.data?.summary && (
        <p className="mb-4 text-sm text-emerald-400">{generateMutation.data.summary}</p>
      )}

      {isLoading && <p className="text-sm text-muted-foreground">Carregando estratégia...</p>}

      {strategy && (
        <div className="grid gap-6 lg:grid-cols-3">
          <section className="lg:col-span-3">
            <h2 className="mb-3 text-lg font-semibold">Posicionamento</h2>
            <p className="rounded-md border border-border bg-card p-4 text-sm text-muted-foreground">
              {strategy.positioning || "—"}
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-lg font-semibold">Objetivos</h2>
            <div className="grid gap-2">
              {(strategy.goals ?? []).map((goal) => (
                <div key={goal} className="rounded-md border border-border bg-card p-3 text-sm">
                  {goal}
                </div>
              ))}
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-lg font-semibold">Cadência</h2>
            <div className="grid gap-2 text-sm">
              <div className="rounded-md border border-border bg-card p-3">
                Posts/semana: {String(strategy.cadence?.weekly_posts ?? "—")}
              </div>
              <div className="rounded-md border border-border bg-card p-3">
                Horários:{" "}
                {Array.isArray(strategy.cadence?.posting_hours)
                  ? (strategy.cadence.posting_hours as number[]).map((h) => `${h}h`).join(", ")
                  : "—"}
              </div>
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-lg font-semibold">Campanhas</h2>
            <div className="grid gap-2">
              {campaigns.length === 0 && (
                <p className="text-sm text-muted-foreground">Gere um plano para ver campanhas.</p>
              )}
              {campaigns.map((campaign) => (
                <div key={String(campaign.name)} className="rounded-md border border-border bg-card p-3 text-sm">
                  <p className="font-medium">{String(campaign.name)}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{String(campaign.goal ?? "")}</p>
                </div>
              ))}
            </div>
          </section>

          {Object.keys(channelGoals).length > 0 && (
            <section className="lg:col-span-3">
              <h2 className="mb-3 text-lg font-semibold">Objetivos por canal</h2>
              <div className="grid gap-2 md:grid-cols-2">
                {Object.entries(channelGoals).map(([channelId, goals]) => (
                  <div key={channelId} className="rounded-md border border-border bg-card p-3 text-sm">
                    <p className="text-xs text-muted-foreground">{channelId.slice(0, 8)}…</p>
                    <ul className="mt-1 list-inside list-disc text-muted-foreground">
                      {goals.map((goal) => (
                        <li key={goal}>{goal}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="lg:col-span-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 className="text-lg font-semibold">Calendário de conteúdo</h2>
              <Link href="/calendar" className="text-xs text-primary hover:underline">
                Calendário completo
              </Link>
            </div>
            {!calendar.length ? (
              <p className="text-sm text-muted-foreground">Nenhum item planejado. Clique em &quot;Gerar plano&quot;.</p>
            ) : (
              <div className="grid gap-2 md:grid-cols-2">
                {calendar.map((item) => (
                  <div key={item.id ?? item.title} className="rounded-md border border-border bg-card p-3 text-sm">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-medium">{item.title}</p>
                      <span className="shrink-0 rounded bg-muted px-2 py-0.5 text-xs">{item.status}</span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {item.planned_for ? new Date(item.planned_for).toLocaleString() : "Sem data"} ·{" "}
                      {String(item.metadata?.content_type ?? "content")} · {String(item.metadata?.platform ?? "")}
                    </p>
                    {item.metadata?.campaign ? (
                      <p className="mt-1 text-xs text-primary">{String(item.metadata.campaign)}</p>
                    ) : null}
                    {item.metadata?.pipeline_id ? (
                      <p className="mt-1 text-xs text-emerald-400">
                        Pipeline: {String(item.metadata.pipeline_id).slice(0, 8)}…
                      </p>
                    ) : null}
                    {item.metadata?.post_artifacts ? (
                      <p className="mt-1 text-xs text-emerald-400">
                        Post gerado ({Array.isArray(item.metadata.post_artifacts) ? item.metadata.post_artifacts.length : 0}{" "}
                        formato(s))
                      </p>
                    ) : null}
                    {item.metadata?.schedule_id ? (
                      <p className="mt-1 text-xs text-blue-400">
                        Agendado · {String(item.metadata.scheduling_mode ?? "assisted")}
                      </p>
                    ) : null}
                    {item.status === "pending_schedule" && item.id ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        className="mt-2"
                        disabled={approveScheduleMutation.isPending}
                        onClick={() => approveScheduleMutation.mutate(item.id!)}
                      >
                        Aprovar agendamento
                      </Button>
                    ) : null}
                    {item.status === "planned" && item.id ? (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {["post", "pin", "thread"].includes(String(item.metadata?.content_type ?? "")) ? (
                          <>
                            <Button
                              size="sm"
                              disabled={generatePostMutation.isPending}
                              onClick={() => generatePostMutation.mutate(item.id!)}
                            >
                              {generatePostMutation.isPending ? "Gerando..." : "Gerar post"}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={dispatchMutation.isPending}
                              onClick={() => dispatchMutation.mutate(item.id!)}
                            >
                              Dispatch
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button
                              size="sm"
                              disabled={dispatchMutation.isPending}
                              onClick={() => dispatchMutation.mutate(item.id!)}
                            >
                              {dispatchMutation.isPending ? "Enviando..." : "Produzir"}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={scheduleMutation.isPending}
                              onClick={() => scheduleMutation.mutate({ id: item.id!, mode: "assisted" })}
                            >
                              Agendar
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={produceMutation.isPending}
                              onClick={() => produceMutation.mutate(item.id!)}
                            >
                              Só vídeo
                            </Button>
                          </>
                        )}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
