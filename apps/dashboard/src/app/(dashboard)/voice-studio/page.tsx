"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Mic, Play, Save, Trash2 } from "lucide-react";
import { api, VoiceLibraryEntry } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

const SAMPLE_TEXT =
  "Este é um preview da narração do ContentOS. Ajuste speed, pitch e pausas até soar perfeito para o seu projeto.";

const BUILTIN_INFO: Record<string, string> = {
  default: "Narração equilibrada para uso geral",
  hype: "Rápido e energético — gaming, trends e hooks",
  calm: "Lento e pausado — wellness e explicações",
  documentary: "Tom neutro e informativo — estilo documentário",
};

type Draft = {
  name: string;
  provider: string;
  voice_id: string;
  speed: number;
  pitch_semitones: number;
  pause_ms: number;
};

function entryToDraft(entry: VoiceLibraryEntry): Draft {
  return {
    name: entry.name,
    provider: entry.provider,
    voice_id: entry.voice_id ?? "",
    speed: entry.speed,
    pitch_semitones: entry.pitch_semitones,
    pause_ms: entry.pause_ms,
  };
}

function pipelinePayload(entry: VoiceLibraryEntry | null, draft: Draft) {
  if (!entry) return {};
  if (entry.is_builtin) {
    return { voice_profile_name: entry.slug };
  }
  return {
    voice_profile_id: entry.id,
    voice_profile: {
      name: draft.name,
      provider: draft.provider,
      voice_id: draft.voice_id || undefined,
      speed: draft.speed,
      pitch_semitones: draft.pitch_semitones,
      pause_ms: draft.pause_ms,
    },
  };
}

export default function VoiceStudioPage() {
  const qc = useQueryClient();
  const [projectId, setProjectId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>({
    name: "",
    provider: "piper",
    voice_id: "",
    speed: 1,
    pitch_semitones: 0,
    pause_ms: 300,
  });
  const [newProfileName, setNewProfileName] = useState("");
  const [previewText, setPreviewText] = useState(SAMPLE_TEXT);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  const { data: library, isLoading } = useQuery({
    queryKey: ["voice-library", projectId],
    queryFn: () => api.getProjectVoiceLibrary(projectId!),
    enabled: !!projectId,
  });

  const entries = useMemo(() => library?.entries ?? [], [library]);
  const selected = useMemo(
    () => entries.find((e) => e.id === selectedId) ?? null,
    [entries, selectedId]
  );

  useEffect(() => {
    if (projects.length && !projectId) setProjectId(projects[0].id);
  }, [projects, projectId]);

  useEffect(() => {
    if (entries.length && !selectedId) setSelectedId(entries[0]?.id ?? null);
  }, [entries, selectedId]);

  useEffect(() => {
    if (selected) setDraft(entryToDraft(selected));
  }, [selected]);

  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  const invalidate = useCallback(() => {
    qc.invalidateQueries({ queryKey: ["voice-library", projectId] });
  }, [qc, projectId]);

  const setDefaultMutation = useMutation({
    mutationFn: (entry: VoiceLibraryEntry) => {
      if (!projectId) throw new Error("Projeto não selecionado");
      if (entry.is_builtin) {
        return api.setProjectVoiceDefault(projectId, { builtin_name: entry.slug });
      }
      return api.setProjectVoiceDefault(projectId, { profile_id: entry.id });
    },
    onSuccess: () => {
      invalidate();
      setMessage("Perfil padrão do projeto atualizado.");
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!selected || selected.is_builtin) throw new Error("Selecione um perfil custom para salvar");
      return api.patchVoiceProfile(selected.id, {
        name: draft.name,
        provider: draft.provider,
        voice_id: draft.voice_id || undefined,
        speed: draft.speed,
        pitch_semitones: draft.pitch_semitones,
        pause_ms: draft.pause_ms,
      });
    },
    onSuccess: () => {
      invalidate();
      setMessage("Perfil salvo.");
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!projectId) throw new Error("Projeto não selecionado");
      const name = newProfileName.trim() || `${draft.name} custom`;
      return api.createVoiceProfile({
        name,
        project_id: projectId,
        provider: draft.provider,
        voice_id: draft.voice_id || undefined,
        speed: draft.speed,
        pitch_semitones: draft.pitch_semitones,
        pause_ms: draft.pause_ms,
      });
    },
    onSuccess: (profile) => {
      invalidate();
      setNewProfileName("");
      setSelectedId(profile.id);
      setMessage("Novo perfil criado.");
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const cloneMutation = useMutation({
    mutationFn: (builtinName: string) => {
      if (!projectId) throw new Error("Projeto não selecionado");
      return api.cloneBuiltinVoiceProfile(projectId, {
        builtin_name: builtinName,
        name: newProfileName.trim() || undefined,
        make_default: false,
      });
    },
    onSuccess: (profile) => {
      invalidate();
      setSelectedId(profile.id);
      setMessage("Built-in clonado como perfil custom.");
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (profileId: string) => api.deleteVoiceProfile(profileId),
    onSuccess: () => {
      invalidate();
      setSelectedId(null);
      setMessage("Perfil removido.");
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const previewMutation = useMutation({
    mutationFn: async () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      const body: Parameters<typeof api.previewVoiceProfile>[0] = {
        text: previewText,
        provider: draft.provider,
        voice_id: draft.voice_id || undefined,
        speed: draft.speed,
        pitch_semitones: draft.pitch_semitones,
        pause_ms: draft.pause_ms,
      };
      if (selected?.is_builtin) {
        body.builtin_name = selected.slug;
      } else if (selected) {
        body.profile_id = selected.id;
      } else {
        body.builtin_name = "default";
      }
      return api.previewVoiceProfile(body);
    },
    onSuccess: (url) => {
      setAudioUrl(url);
      setMessage("Preview gerado.");
    },
    onError: (err: Error) => setMessage(err.message),
  });

  const payloadPreview = useMemo(
    () => JSON.stringify(pipelinePayload(selected, draft), null, 2),
    [selected, draft]
  );

  return (
    <div className="p-8">
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <Mic className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">Voice Studio</h1>
          </div>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Estúdio completo de narração — edite perfis, ouça preview e configure o padrão injetado no step{" "}
            <code>voice</code>. Integrado com{" "}
            <Link href="/memory" className="text-primary hover:underline">
              Project DNA
            </Link>
            .
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-muted-foreground">Projeto</label>
          <select
            value={projectId ?? ""}
            onChange={(e) => {
              setProjectId(e.target.value);
              setSelectedId(null);
            }}
            className="rounded-md border border-border bg-background px-3 py-2 text-sm"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </header>

      {message && (
        <div className="mb-4 rounded-lg border border-border bg-muted/50 px-4 py-3 text-sm">{message}</div>
      )}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Carregando estúdio...</p>
      ) : library ? (
        <div className="grid gap-6 xl:grid-cols-12">
          <section className="space-y-3 rounded-lg border border-border bg-card p-5 xl:col-span-3">
            <h2 className="font-semibold">Biblioteca</h2>
            <p className="text-xs text-muted-foreground">
              Padrão:{" "}
              {library.default_id
                ? library.custom.find((e) => e.id === library.default_id)?.name
                : library.default_builtin ?? "default"}
            </p>
            <div className="max-h-[520px] space-y-2 overflow-y-auto">
              {entries.map((entry) => (
                <button
                  key={entry.id}
                  type="button"
                  onClick={() => setSelectedId(entry.id)}
                  className={`w-full rounded-md border px-3 py-2 text-left transition-colors ${
                    selectedId === entry.id
                      ? "border-primary bg-primary/10"
                      : "border-border hover:bg-muted/50"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{entry.name}</span>
                    {entry.is_default && <Badge>padrão</Badge>}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {entry.is_builtin ? "built-in" : "custom"} · {entry.speed}x · pitch {entry.pitch_semitones}
                  </p>
                </button>
              ))}
            </div>
          </section>

          <section className="space-y-4 rounded-lg border border-border bg-card p-5 xl:col-span-5">
            <h2 className="font-semibold">Editor</h2>
            {selected ? (
              <>
                {selected.is_builtin && (
                  <p className="text-sm text-muted-foreground">
                    {BUILTIN_INFO[selected.slug] ?? "Perfil built-in do sistema."}
                  </p>
                )}

                {!selected.is_builtin && (
                  <div>
                    <label className="text-xs text-muted-foreground">Nome</label>
                    <Input
                      className="mt-1"
                      value={draft.name}
                      onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                    />
                  </div>
                )}

                <SliderField
                  label="Speed"
                  min={0.5}
                  max={2}
                  step={0.05}
                  value={draft.speed}
                  display={`${draft.speed.toFixed(2)}x`}
                  onChange={(speed) => setDraft({ ...draft, speed })}
                />
                <SliderField
                  label="Pitch (semitons)"
                  min={-12}
                  max={12}
                  step={0.5}
                  value={draft.pitch_semitones}
                  display={`${draft.pitch_semitones}`}
                  onChange={(pitch_semitones) => setDraft({ ...draft, pitch_semitones })}
                />
                <SliderField
                  label="Pausa entre frases (ms)"
                  min={0}
                  max={2000}
                  step={50}
                  value={draft.pause_ms}
                  display={`${draft.pause_ms}ms`}
                  onChange={(pause_ms) => setDraft({ ...draft, pause_ms })}
                />

                <div>
                  <label className="text-xs text-muted-foreground">Voice ID (opcional)</label>
                  <Input
                    className="mt-1"
                    placeholder="piper voice id"
                    value={draft.voice_id}
                    onChange={(e) => setDraft({ ...draft, voice_id: e.target.value })}
                  />
                </div>

                <div className="flex flex-wrap gap-2 pt-2">
                  {!selected.is_default && (
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      disabled={setDefaultMutation.isPending}
                      onClick={() => setDefaultMutation.mutate(selected)}
                    >
                      Definir padrão
                    </Button>
                  )}
                  {selected.is_builtin ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={cloneMutation.isPending}
                      onClick={() => cloneMutation.mutate(selected.slug)}
                    >
                      Clonar como custom
                    </Button>
                  ) : (
                    <>
                      <Button
                        type="button"
                        size="sm"
                        disabled={saveMutation.isPending}
                        onClick={() => saveMutation.mutate()}
                      >
                        <Save className="mr-1 h-4 w-4" />
                        Salvar
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="destructive"
                        disabled={deleteMutation.isPending}
                        onClick={() => deleteMutation.mutate(selected.id)}
                      >
                        <Trash2 className="mr-1 h-4 w-4" />
                        Excluir
                      </Button>
                    </>
                  )}
                </div>

                <div className="border-t border-border pt-4">
                  <label className="text-xs text-muted-foreground">Salvar sliders como novo perfil</label>
                  <div className="mt-2 flex gap-2">
                    <Input
                      placeholder="Nome do novo perfil"
                      value={newProfileName}
                      onChange={(e) => setNewProfileName(e.target.value)}
                    />
                    <Button
                      type="button"
                      size="sm"
                      disabled={createMutation.isPending}
                      onClick={() => createMutation.mutate()}
                    >
                      Criar
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Selecione um perfil na biblioteca.</p>
            )}
          </section>

          <section className="space-y-4 rounded-lg border border-border bg-card p-5 xl:col-span-4">
            <h2 className="font-semibold">Preview & Pipeline</h2>

            <div>
              <label className="text-xs text-muted-foreground">Texto de preview</label>
              <textarea
                className="mt-1 min-h-[100px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                value={previewText}
                onChange={(e) => setPreviewText(e.target.value)}
              />
            </div>

            <Button
              type="button"
              disabled={previewMutation.isPending || !previewText.trim()}
              onClick={() => previewMutation.mutate()}
            >
              <Play className="mr-2 h-4 w-4" />
              {previewMutation.isPending ? "Gerando áudio..." : "Ouvir preview"}
            </Button>

            {audioUrl && (
              <audio controls className="w-full" src={audioUrl}>
                <track kind="captions" />
              </audio>
            )}

            <div>
              <p className="text-xs font-medium text-muted-foreground">Payload injetado no step voice</p>
              <pre className="mt-2 max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs">{payloadPreview}</pre>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}

function SliderField({
  label,
  min,
  max,
  step,
  value,
  display,
  onChange,
}: {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  display: string;
  onChange: (value: number) => void;
}) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono">{display}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-primary"
      />
    </div>
  );
}
