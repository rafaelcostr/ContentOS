"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { WORKFLOW_OPTIONS } from "@/lib/pipeline-steps";
import { formatDate } from "@/lib/utils";

interface ProjectSchedulesProps {
  projectId: string;
}

export function ProjectSchedules({ projectId }: ProjectSchedulesProps) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [topic, setTopic] = useState("");
  const [cron, setCron] = useState("0 9 * * *");
  const [workflowName, setWorkflowName] = useState("v3-quality");
  const [error, setError] = useState("");

  const { data: schedules = [] } = useQuery({
    queryKey: ["schedules", projectId],
    queryFn: () => api.listSchedules(projectId),
  });

  const createSchedule = useMutation({
    mutationFn: () =>
      api.createSchedule(projectId, {
        name: name.trim(),
        topic: topic.trim(),
        cron_expression: cron.trim(),
        workflow_name: workflowName,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["schedules", projectId] });
      setName("");
      setTopic("");
      setError("");
    },
    onError: (err) => setError(err instanceof Error ? err.message : "Erro ao criar agendamento"),
  });

  const deleteSchedule = useMutation({
    mutationFn: (id: string) => api.deleteSchedule(projectId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["schedules", projectId] }),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !topic.trim() || !cron.trim()) return;
    createSchedule.mutate();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agendamentos (cron)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-muted-foreground">
          Use <code className="rounded bg-muted px-1">{"{date}"}</code> no tema para data dinâmica. Ex.:{" "}
          <code className="rounded bg-muted px-1">0 9 * * *</code> = todo dia às 09:00 UTC.
        </p>
        {error && <p className="text-sm text-red-500">{error}</p>}
        <form onSubmit={handleSubmit} className="grid gap-2 sm:grid-cols-2">
          <Input placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} />
          <Input placeholder="Cron (0 9 * * *)" value={cron} onChange={(e) => setCron(e.target.value)} />
          <Input
            className="sm:col-span-2"
            placeholder="Tema (ex: Trends {date})"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
          <select
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-sm sm:col-span-2"
          >
            {WORKFLOW_OPTIONS.map((w) => (
              <option key={w.value} value={w.value}>
                {w.label}
              </option>
            ))}
          </select>
          <Button type="submit" disabled={createSchedule.isPending} className="sm:col-span-2">
            {createSchedule.isPending ? "Salvando..." : "Adicionar agendamento"}
          </Button>
        </form>
        <div className="divide-y divide-border">
          {schedules.length === 0 ? (
            <p className="py-3 text-sm text-muted-foreground">Nenhum agendamento.</p>
          ) : (
            schedules.map((s) => (
              <div key={s.id} className="flex items-start justify-between gap-4 py-3 text-sm">
                <div>
                  <p className="font-medium">{s.name}</p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {s.cron_expression} · {s.topic}
                  </p>
                  {s.next_run_at && (
                    <p className="text-xs text-muted-foreground">Próximo: {formatDate(s.next_run_at)}</p>
                  )}
                  {s.last_error && <p className="text-xs text-red-400">{s.last_error.slice(0, 120)}</p>}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => deleteSchedule.mutate(s.id)}
                  disabled={deleteSchedule.isPending}
                >
                  Remover
                </Button>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
