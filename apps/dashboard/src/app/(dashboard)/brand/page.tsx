"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const emptyForm = {
  mission: "",
  objectives: "",
  values: "",
  target_audience: "",
  editorial_rules: "",
  tone: "",
  niche: "",
  goal: "",
  vocabulary: "",
  narrator_persona: "",
  color_primary: "",
  color_secondary: "",
  color_accent: "",
  color_background: "",
  color_text: "",
};

export default function BrandPage() {
  const queryClient = useQueryClient();
  const [projectId, setProjectId] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [message, setMessage] = useState<string | null>(null);

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  const { data: brand, isLoading } = useQuery({
    queryKey: ["brand", projectId],
    queryFn: () => api.getProjectBrand(projectId!),
    enabled: !!projectId,
  });

  useEffect(() => {
    if (projects.length && !projectId) {
      setProjectId(projects[0].id);
    }
  }, [projects, projectId]);

  useEffect(() => {
    if (brand) {
      setForm({
        mission: brand.mission,
        objectives: (brand.objectives ?? []).join(", "),
        values: (brand.values ?? []).join(", "),
        target_audience: brand.target_audience,
        editorial_rules: (brand.editorial_rules ?? []).join("\n"),
        tone: brand.tone,
        niche: brand.niche,
        goal: brand.goal,
        vocabulary: (brand.vocabulary ?? []).join(", "),
        narrator_persona: brand.narrator_persona,
        color_primary: brand.color_palette?.primary ?? "",
        color_secondary: brand.color_palette?.secondary ?? "",
        color_accent: brand.color_palette?.accent ?? "",
        color_background: brand.color_palette?.background ?? "",
        color_text: brand.color_palette?.text ?? "",
      });
    }
  }, [brand]);

  const saveMutation = useMutation({
    mutationFn: () => {
      const color_palette: Record<string, string> = {};
      if (form.color_primary) color_palette.primary = form.color_primary;
      if (form.color_secondary) color_palette.secondary = form.color_secondary;
      if (form.color_accent) color_palette.accent = form.color_accent;
      if (form.color_background) color_palette.background = form.color_background;
      if (form.color_text) color_palette.text = form.color_text;

      return api.patchProjectBrand(projectId!, {
        mission: form.mission,
        objectives: form.objectives
          .split(",")
          .map((v) => v.trim())
          .filter(Boolean),
        values: form.values
          .split(",")
          .map((v) => v.trim())
          .filter(Boolean),
        target_audience: form.target_audience,
        editorial_rules: form.editorial_rules
          .split("\n")
          .map((v) => v.trim())
          .filter(Boolean),
        tone: form.tone,
        niche: form.niche,
        goal: form.goal,
        vocabulary: form.vocabulary
          .split(",")
          .map((v) => v.trim())
          .filter(Boolean),
        narrator_persona: form.narrator_persona,
        color_palette,
      });
    },
    onSuccess: () => {
      setMessage("Identidade de marca salva — injetada em {{brand_context}} nos agentes.");
      queryClient.invalidateQueries({ queryKey: ["brand", projectId] });
      queryClient.invalidateQueries({ queryKey: ["memory", projectId] });
    },
    onError: (err: Error) => setMessage(err.message),
  });

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Brand Intelligence</h1>
        <p className="text-sm text-muted-foreground">
          Missão, valores, público e regras editoriais — estende o Project DNA em project_memory (Growth OS Fase 5).
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
          onChange={(e) => setProjectId(e.target.value)}
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Carregando identidade de marca…</p>
      ) : (
        <div className="grid max-w-3xl gap-6">
          <section className="space-y-4 rounded-lg border border-border p-5">
            <h2 className="text-sm font-semibold">Estratégia de marca</h2>
            <label className="block text-xs text-muted-foreground">
              Missão
              <textarea
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                rows={2}
                value={form.mission}
                onChange={(e) => setForm({ ...form, mission: e.target.value })}
              />
            </label>
            <label className="block text-xs text-muted-foreground">
              Objetivos (vírgula)
              <input
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                value={form.objectives}
                onChange={(e) => setForm({ ...form, objectives: e.target.value })}
              />
            </label>
            <label className="block text-xs text-muted-foreground">
              Valores (vírgula)
              <input
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                value={form.values}
                onChange={(e) => setForm({ ...form, values: e.target.value })}
              />
            </label>
            <label className="block text-xs text-muted-foreground">
              Público-alvo
              <textarea
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                rows={2}
                value={form.target_audience}
                onChange={(e) => setForm({ ...form, target_audience: e.target.value })}
              />
            </label>
            <label className="block text-xs text-muted-foreground">
              Regras editoriais (uma por linha)
              <textarea
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                rows={4}
                value={form.editorial_rules}
                onChange={(e) => setForm({ ...form, editorial_rules: e.target.value })}
              />
            </label>
          </section>

          <section className="space-y-4 rounded-lg border border-border p-5">
            <h2 className="text-sm font-semibold">Voz e posicionamento</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-xs text-muted-foreground">
                Tom
                <input
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  value={form.tone}
                  onChange={(e) => setForm({ ...form, tone: e.target.value })}
                />
              </label>
              <label className="block text-xs text-muted-foreground">
                Nicho
                <input
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  value={form.niche}
                  onChange={(e) => setForm({ ...form, niche: e.target.value })}
                />
              </label>
              <label className="block text-xs text-muted-foreground sm:col-span-2">
                Objetivo de conteúdo
                <input
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  value={form.goal}
                  onChange={(e) => setForm({ ...form, goal: e.target.value })}
                />
              </label>
              <label className="block text-xs text-muted-foreground sm:col-span-2">
                Vocabulário (vírgula)
                <input
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  value={form.vocabulary}
                  onChange={(e) => setForm({ ...form, vocabulary: e.target.value })}
                />
              </label>
              <label className="block text-xs text-muted-foreground sm:col-span-2">
                Persona do narrador
                <input
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  value={form.narrator_persona}
                  onChange={(e) => setForm({ ...form, narrator_persona: e.target.value })}
                />
              </label>
            </div>
          </section>

          <section className="space-y-4 rounded-lg border border-border p-5">
            <h2 className="text-sm font-semibold">Paleta de cores</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {(
                [
                  ["color_primary", "Primária"],
                  ["color_secondary", "Secundária"],
                  ["color_accent", "Destaque"],
                  ["color_background", "Fundo"],
                  ["color_text", "Texto"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="block text-xs text-muted-foreground">
                  {label}
                  <div className="mt-1 flex gap-2">
                    <input
                      type="color"
                      className="h-9 w-12 cursor-pointer rounded border border-border bg-background"
                      value={form[key].startsWith("#") ? form[key] : "#000000"}
                      onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                    />
                    <input
                      className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
                      placeholder="#RRGGBB"
                      value={form[key]}
                      onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                    />
                  </div>
                </label>
              ))}
            </div>
          </section>

          {brand?.brand_context_preview ? (
            <section className="rounded-lg border border-dashed border-border bg-muted/30 p-5">
              <h2 className="mb-2 text-sm font-semibold">Preview — brand_context</h2>
              <p className="text-sm text-muted-foreground">{brand.brand_context_preview}</p>
            </section>
          ) : null}

          <button
            type="button"
            className="w-fit rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
            disabled={!projectId || saveMutation.isPending}
            onClick={() => saveMutation.mutate()}
          >
            {saveMutation.isPending ? "Salvando…" : "Salvar identidade de marca"}
          </button>
        </div>
      )}
    </div>
  );
}
