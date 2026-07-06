"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, Project, SpecialistProfile, SpecialistSelection } from "@/lib/api";

export default function SpecialistsPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [topic, setTopic] = useState("");

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  const { data: specialists = [] } = useQuery({
    queryKey: ["specialists"],
    queryFn: () => api.listSpecialists(true),
  });

  useEffect(() => {
    if (projects.length && !projectId) {
      setProjectId(projects[0].id);
    }
  }, [projects, projectId]);

  const selectMutation = useMutation({
    mutationFn: () =>
      api.selectSpecialist({
        project_id: projectId!,
        topic,
      }),
  });

  const selection: SpecialistSelection | undefined = selectMutation.data;

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Specialists</h1>
        <p className="text-sm text-muted-foreground">
          Seleção automática de especialista por nicho — piloto Gaming, Tech, Business (V4)
        </p>
      </header>

      <div className="mb-8 grid max-w-3xl gap-3">
        <h2 className="text-sm font-semibold">Catálogo</h2>
        <div className="grid gap-2 sm:grid-cols-2">
          {specialists.map((s: SpecialistProfile) => (
            <div
              key={s.specialist_id}
              className={`rounded-lg border p-3 text-sm ${
                s.coming_soon ? "border-dashed opacity-60" : "border-border bg-card"
              }`}
            >
              <p className="font-medium">{s.name}</p>
              <p className="text-xs text-muted-foreground">{s.niche}</p>
              {s.pilot && <span className="mt-1 inline-block text-xs text-primary">Piloto V4.1.3</span>}
              {s.coming_soon && <span className="mt-1 inline-block text-xs text-muted-foreground">Em breve</span>}
            </div>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <label className="text-xs font-medium text-muted-foreground">Projeto</label>
        <select
          className="mt-1 w-full max-w-md rounded-md border border-border bg-background px-3 py-2 text-sm"
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

      <div className="mb-6 flex max-w-2xl gap-2">
        <input
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
          placeholder="Tópico para selecionar especialista"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        />
        <button
          type="button"
          disabled={!topic.trim() || !projectId || selectMutation.isPending}
          onClick={() => selectMutation.mutate()}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
        >
          Selecionar
        </button>
      </div>

      {selection && (
        <div className="max-w-2xl rounded-lg border border-border bg-card p-6 text-sm">
          <p className="text-lg font-semibold">{selection.specialist.name}</p>
          <p className="text-muted-foreground">
            Confiança: {(selection.confidence * 100).toFixed(0)}% — {selection.reason}
          </p>
          <p className="mt-4 whitespace-pre-wrap text-muted-foreground">{selection.specialist_context}</p>
        </div>
      )}
    </div>
  );
}
