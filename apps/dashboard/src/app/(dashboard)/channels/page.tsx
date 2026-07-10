"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { api, Channel, Project } from "@/lib/api";

const PLATFORMS = [
  { id: "youtube", label: "YouTube" },
  { id: "tiktok", label: "TikTok" },
  { id: "instagram", label: "Instagram" },
  { id: "facebook", label: "Facebook" },
  { id: "threads", label: "Threads" },
  { id: "pinterest", label: "Pinterest" },
  { id: "linkedin", label: "LinkedIn" },
  { id: "x", label: "X" },
] as const;

function ChannelWorkspacePanel({ channel }: { channel: Channel }) {
  const { data: workspace, isLoading } = useQuery({
    queryKey: ["channel-workspace", channel.id],
    queryFn: () => api.getChannelWorkspace(channel.id),
  });

  if (isLoading) {
    return <p className="mt-4 text-xs text-muted-foreground">Carregando workspace do canal...</p>;
  }
  if (!workspace) return null;

  const healthColor =
    workspace.health_status === "healthy"
      ? "text-emerald-400"
      : workspace.health_status === "attention"
        ? "text-amber-400"
        : "text-destructive";

  return (
    <div className="mt-4 rounded-md border border-border bg-card/30 p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Channel Workspace</p>
      <p className="mt-1 text-xs text-muted-foreground">
        <span className={`font-medium capitalize ${healthColor}`}>{workspace.health_status}</span>
        {" · "}
        {workspace.summary}
      </p>
      <div className="mt-2 grid gap-2 text-[11px] text-muted-foreground md:grid-cols-4">
        <p>Calendário: {workspace.calendar.length}</p>
        <p>Performance: {workspace.performance.length}</p>
        <p>Recomendações: {workspace.recommendations.length}</p>
        <p>Assets: {workspace.assets.length}</p>
      </div>
      {workspace.calendar.length > 0 && (
        <p className="mt-2 text-[11px] text-muted-foreground">
          Próximo: {(workspace.calendar[0] as { title?: string }).title ?? "—"}
        </p>
      )}
    </div>
  );
}

function ChannelManagerPanel({ channel }: { channel: Channel }) {
  const queryClient = useQueryClient();
  const [schedulingMode, setSchedulingMode] = useState<"assisted" | "automatic">("assisted");

  const { data: plan, isLoading, refetch } = useQuery({
    queryKey: ["channel-manager", channel.id, schedulingMode],
    queryFn: () => api.getChannelManagerPlan(channel.id, schedulingMode),
  });

  const previewMutation = useMutation({
    mutationFn: () =>
      api.runChannelManager(channel.id, { dryRun: true, schedulingMode, maxActions: 5 }),
    onSuccess: () => refetch(),
  });

  const runMutation = useMutation({
    mutationFn: () =>
      api.runChannelManager(channel.id, { dryRun: false, schedulingMode, maxActions: 3 }),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ["growth-report", channel.project_id] });
      queryClient.invalidateQueries({ queryKey: ["growth-calendar", channel.project_id] });
    },
  });

  const healthColor =
    plan?.health_status === "healthy"
      ? "text-emerald-400"
      : plan?.health_status === "attention"
        ? "text-amber-400"
        : "text-destructive";

  return (
    <div className="mt-4 rounded-md border border-dashed border-border bg-muted/10 p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Channel Manager AI
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="rounded-md border border-border bg-background px-2 py-1 text-[11px]"
            value={schedulingMode}
            onChange={(e) => setSchedulingMode(e.target.value as "assisted" | "automatic")}
          >
            <option value="assisted">Assistido</option>
            <option value="automatic">Automático</option>
          </select>
          <Button size="sm" variant="outline" disabled={previewMutation.isPending} onClick={() => previewMutation.mutate()}>
            {previewMutation.isPending ? "Planejando..." : "Plano diário"}
          </Button>
          <Button size="sm" disabled={runMutation.isPending} onClick={() => runMutation.mutate()}>
            {runMutation.isPending ? "Executando..." : "Executar plano"}
          </Button>
        </div>
      </div>

      {isLoading && <p className="text-xs text-muted-foreground">Carregando plano do gerente...</p>}

      {plan && (
        <div className="space-y-2 text-xs">
          <p className="text-muted-foreground">
            <span className={`font-medium capitalize ${healthColor}`}>{plan.health_status}</span>
            {" · "}
            {plan.summary}
          </p>
          {plan.focus_topics.length > 0 && (
            <p className="text-muted-foreground">Foco: {plan.focus_topics.slice(0, 3).join(" · ")}</p>
          )}
          {plan.actions.length > 0 && (
            <ul className="space-y-1">
              {plan.actions.slice(0, 4).map((action, index) => (
                <li key={`${action.action}-${index}`} className="rounded border border-border bg-card/40 px-2 py-1.5">
                  <span className="font-medium text-foreground">{action.title}</span>
                  <span className="ml-2 text-[10px] uppercase text-muted-foreground">{action.action}</span>
                  <p className="text-[11px] text-muted-foreground">{action.detail}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {runMutation.data && runMutation.data.executed.length > 0 && (
        <div className="mt-2 space-y-1 text-[11px] text-emerald-400">
          {runMutation.data.executed.map((result, index) => (
            <p key={index}>
              {result.action}: {result.status} — {result.detail}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function ChannelMemoryPanel({ channel }: { channel: Channel }) {
  const queryClient = useQueryClient();
  const [notes, setNotes] = useState("");

  const { data: memory, isLoading } = useQuery({
    queryKey: ["channel-memory", channel.id],
    queryFn: () => api.getChannelMemory(channel.id),
  });

  useEffect(() => {
    if (memory) setNotes(memory.notes ?? "");
  }, [memory]);

  const saveMutation = useMutation({
    mutationFn: () => api.patchChannelMemory(channel.id, { notes }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["channel-memory", channel.id] }),
  });

  const seedMutation = useMutation({
    mutationFn: () => api.seedChannelMemory(channel.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["channel-memory", channel.id] }),
  });

  return (
    <div className="mt-4 rounded-md border border-dashed border-border bg-muted/10 p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Channel Memory</p>
        <Button size="sm" variant="outline" disabled={seedMutation.isPending} onClick={() => seedMutation.mutate()}>
          {seedMutation.isPending ? "Atualizando..." : "Atualizar da sync"}
        </Button>
      </div>

      {isLoading && <p className="text-xs text-muted-foreground">Carregando memória do canal...</p>}

      {memory && (
        <div className="space-y-2 text-xs text-muted-foreground">
          {memory.top_hooks.length > 0 && <p>Hooks: {memory.top_hooks.slice(0, 4).join(" · ")}</p>}
          {memory.top_hashtags.length > 0 && <p>Hashtags: {memory.top_hashtags.slice(0, 8).join(" ")}</p>}
          {memory.best_posting_hours.length > 0 && (
            <p>Horários: {memory.best_posting_hours.map((h) => `${h}h`).join(", ")}</p>
          )}
          {memory.channel_context_preview && (
            <p className="rounded border border-border bg-card/40 p-2 text-[11px]">{memory.channel_context_preview}</p>
          )}
          <label className="block pt-1">
            <span className="text-[11px] font-medium">Notas manuais</span>
            <textarea
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </label>
          <Button size="sm" variant="secondary" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate()}>
            Salvar notas
          </Button>
        </div>
      )}
    </div>
  );
}

function PlatformIntegrationPanel({ channel }: { channel: Channel }) {
  const queryClient = useQueryClient();
  const oauthPlatforms = new Set(["youtube", "tiktok", "instagram"]);
  const supported = oauthPlatforms.has(channel.platform);

  const { data: status, isLoading } = useQuery({
    queryKey: ["platform-status", channel.id],
    queryFn: () => api.getPlatformChannelStatus(channel.id),
    enabled: supported,
  });

  const { data: analysis } = useQuery({
    queryKey: ["channel-analysis", channel.id],
    queryFn: () => api.getChannelAnalysis(channel.id),
    enabled: supported,
  });

  const syncMutation = useMutation({
    mutationFn: () =>
      channel.platform === "youtube"
        ? api.syncYouTubeChannel(channel.id)
        : api.syncPlatformChannel(channel.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform-status", channel.id] });
      queryClient.invalidateQueries({ queryKey: ["youtube-status", channel.id] });
      queryClient.invalidateQueries({ queryKey: ["youtube-data", channel.id] });
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: () => api.analyzeChannel(channel.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channel-analysis", channel.id] });
      queryClient.invalidateQueries({ queryKey: ["channel-memory", channel.id] });
      queryClient.invalidateQueries({ queryKey: ["growth-channels", channel.project_id] });
      queryClient.invalidateQueries({ queryKey: ["growth-report", channel.project_id] });
    },
  });

  if (!supported) return null;

  const totals = status?.channel_totals ?? {};
  const followerCount =
    (totals.subscriber_count as number | undefined) ??
    (totals.followers_count as number | undefined) ??
    (totals.follower_count as number | undefined);

  return (
    <div className="mt-4 rounded-md border border-dashed border-border bg-muted/20 p-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {status?.platform_label ?? channel.platform} Integration
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="secondary"
            disabled={!status?.oauth_connected || syncMutation.isPending}
            onClick={() => syncMutation.mutate()}
          >
            {syncMutation.isPending ? "Sincronizando..." : "Sincronizar"}
          </Button>
          <Button
            size="sm"
            disabled={!status?.last_synced_at || analyzeMutation.isPending}
            onClick={() => analyzeMutation.mutate()}
          >
            {analyzeMutation.isPending ? "Analisando..." : "Analisar canal"}
          </Button>
        </div>
      </div>

      {analysis && (
        <div className="mb-3 rounded-md border border-border bg-card/50 p-3">
          <p className="text-sm font-semibold">Growth Score: {analysis.score.toFixed(0)}/100</p>
          <p className="mt-1 text-xs text-muted-foreground">{analysis.summary}</p>
          {Boolean(analysis.report.dimensions) && typeof analysis.report.dimensions === "object" && (
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(analysis.report.dimensions as Record<string, number>).map(([key, value]) => (
                <span key={key} className="rounded-md border border-border px-2 py-0.5 text-[11px] capitalize text-muted-foreground">
                  {key}: {Number(value).toFixed(0)}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {isLoading && <p className="text-xs text-muted-foreground">Carregando status...</p>}

      {status && (
        <div className="grid gap-2 text-xs text-muted-foreground md:grid-cols-3">
          <p>Seguidores: {formatCount(followerCount)}</p>
          {channel.platform === "youtube" && (
            <>
              <p>Views totais: {formatCount(totals.view_count as number | undefined)}</p>
              <p>Vídeos: {formatCount(totals.video_count as number | undefined)}</p>
              <p>Shorts: {formatCount(totals.shorts_count as number | undefined)}</p>
            </>
          )}
          {channel.platform === "tiktok" && (
            <>
              <p>Vídeos: {formatCount(totals.video_count as number | undefined)}</p>
              <p>Likes totais: {formatCount(totals.likes_count as number | undefined)}</p>
            </>
          )}
          {channel.platform === "instagram" && (
            <p>Posts: {formatCount(totals.media_count as number | undefined)}</p>
          )}
          <p>Última sync: {status.last_synced_at ? new Date(status.last_synced_at).toLocaleString() : "nunca"}</p>
        </div>
      )}

      {status && !status.oauth_connected && (
        <p className="mt-2 text-xs text-amber-400">
          Conecte OAuth em{" "}
          <Link href="/plugins" className="underline">
            Publicação
          </Link>{" "}
          para sincronizar dados reais.
        </p>
      )}

      {syncMutation.data?.error && <p className="mt-2 text-xs text-destructive">{syncMutation.data.error}</p>}
      {analyzeMutation.data && (
        <p className="mt-2 text-xs text-emerald-400">
          Análise concluída — {analyzeMutation.data.recommendations.length} recomendação(ões).
        </p>
      )}
    </div>
  );
}

function formatCount(value: number | null | undefined) {
  if (value == null) return "—";
  return value.toLocaleString();
}

export default function ChannelsPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [platform, setPlatform] = useState("youtube");
  const [name, setName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const queryClient = useQueryClient();

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) setProjectId(projects[0].id);
  }, [projects, projectId]);

  const { data: channels = [], isLoading } = useQuery({
    queryKey: ["channels", projectId],
    queryFn: () => api.getChannels(projectId!),
    enabled: Boolean(projectId),
  });

  const { data: channelsOverview = [] } = useQuery({
    queryKey: ["growth-channels-overview", projectId],
    queryFn: () => api.getGrowthChannelsOverview(projectId!),
    enabled: Boolean(projectId),
  });

  const createMutation = useMutation({
    mutationFn: () => api.createChannel(projectId!, platform, name.trim()),
    onSuccess: () => {
      setName("");
      queryClient.invalidateQueries({ queryKey: ["channels", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-channels", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-report", projectId] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ channelId, body }: { channelId: string; body: { name?: string; is_active?: boolean } }) =>
      api.updateChannel(channelId, body),
    onSuccess: () => {
      setEditingId(null);
      queryClient.invalidateQueries({ queryKey: ["channels", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-channels", projectId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (channelId: string) => api.deleteChannel(channelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-channels", projectId] });
      queryClient.invalidateQueries({ queryKey: ["growth-report", projectId] });
    },
  });

  function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!projectId || !name.trim()) return;
    createMutation.mutate();
  }

  function startEdit(channel: Channel) {
    setEditingId(channel.id);
    setEditName(channel.name);
  }

  function saveEdit(channelId: string) {
    if (!editName.trim()) return;
    updateMutation.mutate({ channelId, body: { name: editName.trim() } });
  }

  function toggleActive(channel: Channel) {
    updateMutation.mutate({
      channelId: channel.id,
      body: { is_active: !channel.is_active },
    });
  }

  function removeChannel(channel: Channel) {
    if (!window.confirm(`Remover o canal "${channel.name}"?`)) return;
    deleteMutation.mutate(channel.id);
  }

  return (
    <div className="p-8">
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Canais</h1>
          <p className="text-sm text-muted-foreground">
            Cadastro central de canais sociais. Conecte OAuth em{" "}
            <Link href="/plugins" className="text-primary hover:underline">
              Publicação
            </Link>
            .
          </p>
        </div>
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

      {channelsOverview.length > 0 && (
        <div className="mb-8 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {channelsOverview.map((item) => (
            <div key={item.channel_id} className="rounded-lg border border-border bg-card/40 p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold">{item.name}</p>
                  <p className="text-xs capitalize text-muted-foreground">{item.platform}</p>
                </div>
                <span
                  className={`text-xs font-medium capitalize ${
                    item.health_status === "healthy"
                      ? "text-emerald-400"
                      : item.health_status === "attention"
                        ? "text-amber-400"
                        : "text-destructive"
                  }`}
                >
                  {item.health_status}
                </span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-muted-foreground">
                <p>Score: {item.score.toFixed(0)}</p>
                <p>Planejados: {item.calendar_planned}</p>
                <p>Agendados: {item.calendar_scheduled}</p>
                <p>Recs abertas: {item.recommendations_open}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      <form
        onSubmit={submitCreate}
        className="mb-8 grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-[160px_1fr_auto]"
      >
        <select
          className="rounded-md border border-border bg-background px-3 py-2 text-sm"
          value={platform}
          onChange={(event) => setPlatform(event.target.value)}
        >
          {PLATFORMS.map((item) => (
            <option key={item.id} value={item.id}>
              {item.label}
            </option>
          ))}
        </select>
        <input
          className="rounded-md border border-border bg-background px-3 py-2 text-sm"
          placeholder="Nome do canal"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <Button type="submit" disabled={!projectId || !name.trim() || createMutation.isPending}>
          {createMutation.isPending ? "Criando..." : "Criar canal"}
        </Button>
      </form>

      {(createMutation.error || updateMutation.error || deleteMutation.error) && (
        <p className="mb-4 text-sm text-destructive">
          {String(createMutation.error ?? updateMutation.error ?? deleteMutation.error)}
        </p>
      )}

      {isLoading && <p className="text-sm text-muted-foreground">Carregando canais...</p>}

      {!isLoading && channels.length === 0 && (
        <p className="text-sm text-muted-foreground">Nenhum canal cadastrado para este projeto.</p>
      )}

      <div className="grid gap-3">
        {channels.map((channel) => (
          <div key={channel.id} className="rounded-md border border-border bg-card p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0 flex-1">
                {editingId === channel.id ? (
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      className="rounded-md border border-border bg-background px-3 py-1.5 text-sm"
                      value={editName}
                      onChange={(event) => setEditName(event.target.value)}
                    />
                    <Button size="sm" onClick={() => saveEdit(channel.id)} disabled={updateMutation.isPending}>
                      Salvar
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
                      Cancelar
                    </Button>
                  </div>
                ) : (
                  <>
                    <p className="text-sm font-semibold">{channel.name}</p>
                    <p className="text-xs capitalize text-muted-foreground">{channel.platform}</p>
                  </>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`rounded-md border px-2 py-1 text-xs ${
                    channel.has_credentials ? "border-emerald-500/40 text-emerald-400" : "border-border text-muted-foreground"
                  }`}
                >
                  {channel.has_credentials ? "OAuth conectado" : "Sem OAuth"}
                </span>
                <span className="rounded-md border border-border px-2 py-1 text-xs">
                  {channel.is_active ? "Ativo" : "Inativo"}
                </span>
              </div>
            </div>

            {editingId !== channel.id && (
              <div className="mt-3 flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => startEdit(channel)}>
                  Editar
                </Button>
                <Button size="sm" variant="outline" onClick={() => toggleActive(channel)} disabled={updateMutation.isPending}>
                  {channel.is_active ? "Desativar" : "Ativar"}
                </Button>
                <Button size="sm" variant="destructive" onClick={() => removeChannel(channel)} disabled={deleteMutation.isPending}>
                  Remover
                </Button>
                {!channel.has_credentials && (
                  <Button size="sm" variant="secondary" asChild>
                    <Link href="/plugins">Conectar OAuth</Link>
                  </Button>
                )}
              </div>
            )}

            <PlatformIntegrationPanel channel={channel} />
            <ChannelManagerPanel channel={channel} />
            <ChannelWorkspacePanel channel={channel} />
            <ChannelMemoryPanel channel={channel} />
          </div>
        ))}
      </div>
    </div>
  );
}
