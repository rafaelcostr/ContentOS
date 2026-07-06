"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, Project, ProjectMemory } from "@/lib/api";

const emptyForm = {
  tone: "",
  niche: "",
  hook_style: "",
  goal: "",
  cta: "",
  avg_duration: "",
  vocabulary: "",
};

const emptyDnaForm = {
  humor_level: "",
  pace: "medium",
  narrator_persona: "",
  cta_style: "",
  preferred_formats: "",
  hook_patterns: "",
  visual_primary_color: "",
  visual_mood: "",
};

const PACE_OPTIONS = [
  { value: "", label: "(padrão)" },
  { value: "slow", label: "Lento" },
  { value: "medium", label: "Médio" },
  { value: "fast", label: "Rápido" },
];

export default function MemoryPage() {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [dnaForm, setDnaForm] = useState(emptyDnaForm);
  const [message, setMessage] = useState<string | null>(null);

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  const { data: memory, isLoading } = useQuery({
    queryKey: ["memory", projectId],
    queryFn: () => api.getProjectMemory(projectId!),
    enabled: !!projectId,
  });

  const { data: dna } = useQuery({
    queryKey: ["dna", projectId],
    queryFn: () => api.getProjectDna(projectId!),
    enabled: !!projectId,
  });

  useEffect(() => {
    if (projects.length && !projectId) {
      setProjectId(projects[0].id);
    }
  }, [projects, projectId]);

  useEffect(() => {
    if (memory) {
      setForm({
        tone: memory.tone,
        niche: memory.niche,
        hook_style: memory.hook_style,
        goal: memory.goal,
        cta: memory.cta,
        avg_duration: memory.avg_duration != null ? String(memory.avg_duration) : "",
        vocabulary: memory.vocabulary.join(", "),
      });
    }
  }, [memory]);

  useEffect(() => {
    if (dna) {
      setDnaForm({
        humor_level: dna.humor_level != null ? String(dna.humor_level) : "",
        pace: dna.pace || "medium",
        narrator_persona: dna.narrator_persona,
        cta_style: dna.cta_style,
        preferred_formats: (dna.preferred_formats ?? []).join(", "),
        hook_patterns: (dna.hook_patterns ?? []).join(", "),
        visual_primary_color: dna.visual_style?.primary_color ?? "",
        visual_mood: dna.visual_style?.mood ?? "",
      });
    }
  }, [dna]);

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateProjectMemory(projectId!, {
        tone: form.tone,
        niche: form.niche,
        hook_style: form.hook_style,
        goal: form.goal,
        cta: form.cta,
        avg_duration: form.avg_duration ? Number(form.avg_duration) : null,
        vocabulary: form.vocabulary
          .split(",")
          .map((v) => v.trim())
          .filter(Boolean),
        style: memory?.style ?? {},
        history: memory?.history ?? [],
        humor_level: memory?.humor_level ?? null,
        pace: memory?.pace ?? "",
        visual_style: memory?.visual_style ?? {},
        narrator_persona: memory?.narrator_persona ?? "",
        preferred_formats: memory?.preferred_formats ?? [],
        hook_patterns: memory?.hook_patterns ?? [],
        cta_style: memory?.cta_style ?? "",
      }),
    onSuccess: () => {
      setMessage("Memória salva — próximos jobs usarão o novo contexto.");
      queryClient.invalidateQueries({ queryKey: ["memory", projectId] });
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const saveDnaMutation = useMutation({
    mutationFn: () =>
      api.patchProjectDna(projectId!, {
        humor_level: dnaForm.humor_level ? Number(dnaForm.humor_level) : null,
        pace: dnaForm.pace || null,
        narrator_persona: dnaForm.narrator_persona,
        cta_style: dnaForm.cta_style,
        preferred_formats: dnaForm.preferred_formats
          .split(",")
          .map((v) => v.trim())
          .filter(Boolean),
        hook_patterns: dnaForm.hook_patterns
          .split(",")
          .map((v) => v.trim())
          .filter(Boolean),
        visual_style: {
          ...(dna?.visual_style ?? {}),
          ...(dnaForm.visual_primary_color ? { primary_color: dnaForm.visual_primary_color } : {}),
          ...(dnaForm.visual_mood ? { mood: dnaForm.visual_mood } : {}),
        },
      }),
    onSuccess: () => {
      setMessage("DNA do projeto salvo — injetado em memory_context e dna_context.");
      queryClient.invalidateQueries({ queryKey: ["dna", projectId] });
      queryClient.invalidateQueries({ queryKey: ["memory", projectId] });
    },
    onError: (err: Error) => setMessage(err.message),
  });

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Memory Manager</h1>
        <p className="text-sm text-muted-foreground">
          Memória criativa e Project DNA — injetados nos prompts dos agentes (V2.4 + V4)
        </p>
      </header>

      {message && (
        <div className="mb-4 rounded-lg border border-border bg-muted/50 px-4 py-3 text-sm">{message}</div>
      )}

      <div className="mb-6">
        <label className="text-xs font-medium text-muted-foreground">Projeto</label>
        <select
          className="mt-1 w-full max-w-md rounded-md border border-border bg-background px-3 py-2 text-sm"
          value={projectId ?? ""}
          onChange={(e) => {
            setProjectId(e.target.value);
            setMessage(null);
          }}
        >
          {projects.map((p: Project) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      {isLoading && <p className="text-muted-foreground">Carregando...</p>}

      {memory && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="space-y-4 rounded-lg border border-border bg-card p-6">
            <h2 className="font-semibold">Memória criativa</h2>

            {(
              [
                ["niche", "Nicho"],
                ["tone", "Tom de voz"],
                ["hook_style", "Estilo de gancho"],
                ["goal", "Objetivo"],
                ["cta", "CTA padrão"],
                ["avg_duration", "Duração alvo (s)"],
                ["vocabulary", "Vocabulário (vírgulas)"],
              ] as const
            ).map(([key, label]) => (
              <div key={key}>
                <label className="text-xs text-muted-foreground">{label}</label>
                <input
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  value={form[key]}
                  onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                />
              </div>
            ))}

            <button
              type="button"
              disabled={saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
              className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
            >
              {saveMutation.isPending ? "Salvando..." : "Salvar memória"}
            </button>
          </div>

          <div className="space-y-4 rounded-lg border border-border bg-card p-6">
            <h2 className="font-semibold">Project DNA (V4)</h2>
            <p className="text-xs text-muted-foreground">Identidade do projeto — ritmo, humor, visual, formatos</p>

            <div>
              <label className="text-xs text-muted-foreground">Humor (0–1)</label>
              <input
                type="number"
                min={0}
                max={1}
                step={0.1}
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                value={dnaForm.humor_level}
                onChange={(e) => setDnaForm((f) => ({ ...f, humor_level: e.target.value }))}
              />
            </div>

            <div>
              <label className="text-xs text-muted-foreground">Ritmo</label>
              <select
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                value={dnaForm.pace}
                onChange={(e) => setDnaForm((f) => ({ ...f, pace: e.target.value }))}
              >
                {PACE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>

            {(
              [
                ["narrator_persona", "Persona do narrador"],
                ["cta_style", "Estilo de CTA"],
                ["preferred_formats", "Formatos (tiktok, youtube_shorts, …)"],
                ["hook_patterns", "Padrões de hook (vírgulas)"],
                ["visual_primary_color", "Cor primária"],
                ["visual_mood", "Mood visual"],
              ] as const
            ).map(([key, label]) => (
              <div key={key}>
                <label className="text-xs text-muted-foreground">{label}</label>
                <input
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  value={dnaForm[key]}
                  onChange={(e) => setDnaForm((f) => ({ ...f, [key]: e.target.value }))}
                />
              </div>
            ))}

            <button
              type="button"
              disabled={saveDnaMutation.isPending}
              onClick={() => saveDnaMutation.mutate()}
              className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
            >
              {saveDnaMutation.isPending ? "Salvando..." : "Salvar DNA"}
            </button>
          </div>

          <div className="rounded-lg border border-border bg-card p-6 lg:col-span-2">
            <h2 className="font-semibold">Preview dos prompts</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-xs font-medium text-muted-foreground">memory_context</p>
                <pre className="mt-2 min-h-[120px] whitespace-pre-wrap rounded-md bg-muted p-4 text-sm">
                  {memory.memory_context_preview || "(vazio)"}
                </pre>
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground">dna_context</p>
                <pre className="mt-2 min-h-[120px] whitespace-pre-wrap rounded-md bg-muted p-4 text-sm">
                  {dna?.dna_context_preview || memory.dna_context_preview || "(vazio)"}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
