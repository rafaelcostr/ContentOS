"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, MultiContentReport, Project, VideoVariantsReport } from "@/lib/api";

const FORMAT_LABELS: Record<string, string> = {
  thread_x: "Thread X",
  linkedin_post: "LinkedIn",
  newsletter: "Newsletter",
  seo_article: "Artigo SEO",
  email_marketing: "Email Marketing",
};

const PLATFORM_LABELS: Record<string, string> = {
  tiktok: "TikTok",
  youtube_shorts: "YouTube Shorts",
  instagram_reels: "Instagram Reels",
};

type Tab = "text" | "video";

export default function MultiContentPage() {
  const [tab, setTab] = useState<Tab>("text");
  const [projectId, setProjectId] = useState<string | null>(null);
  const [topic, setTopic] = useState("");

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) {
      setProjectId(projects[0].id);
    }
  }, [projects, projectId]);

  const textMutation = useMutation({
    mutationFn: () =>
      api.generateMultiContent({
        project_id: projectId!,
        topic,
        payload: {
          script: {
            title: topic,
            full_text: `Conteúdo sobre ${topic}. Insight principal que o público precisa saber agora.`,
            call_to_action: "Comenta o que achou!",
          },
        },
      }),
  });

  const videoMutation = useMutation({
    mutationFn: () =>
      api.generateVideoVariants({
        project_id: projectId!,
        topic,
        payload: {
          script: {
            title: topic,
            full_text: `Conteúdo sobre ${topic}. Insight principal que o público precisa saber agora.`,
          },
          publication: {
            title: topic,
            description: `Vídeo sobre ${topic}.`,
            hashtags: ["viral", "shorts"],
          },
          render_ref: { id: "demo-render", url: "s3://demo/render.mp4" },
          duration_seconds: 42,
        },
      }),
  });

  const textReport: MultiContentReport | undefined = textMutation.data;
  const videoReport: VideoVariantsReport | undefined = videoMutation.data;
  const isPending = tab === "text" ? textMutation.isPending : videoMutation.isPending;

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Multi Content</h1>
        <p className="text-sm text-muted-foreground">
          Um roteiro → texto (V4.2.1) e variantes de vídeo TikTok, Shorts, Reels (V4.2.2)
        </p>
      </header>

      <div className="mb-6 flex gap-2">
        <button
          type="button"
          onClick={() => setTab("text")}
          className={`rounded-md px-3 py-1.5 text-sm ${tab === "text" ? "bg-primary text-primary-foreground" : "border border-border"}`}
        >
          Texto
        </button>
        <button
          type="button"
          onClick={() => setTab("video")}
          className={`rounded-md px-3 py-1.5 text-sm ${tab === "video" ? "bg-primary text-primary-foreground" : "border border-border"}`}
        >
          Vídeo
        </button>
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
          placeholder="Tópico / título do roteiro"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        />
        <button
          type="button"
          disabled={!topic.trim() || !projectId || isPending}
          onClick={() => (tab === "text" ? textMutation.mutate() : videoMutation.mutate())}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
        >
          Gerar
        </button>
      </div>

      {tab === "text" && textReport && (
        <div className="grid max-w-4xl gap-4">
          <p className="text-sm text-muted-foreground">{textReport.artifact_count} artefatos gerados</p>
          {textReport.artifacts.map((a) => (
            <div key={a.format} className="rounded-lg border border-border bg-card p-4">
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-sm font-semibold">{FORMAT_LABELS[a.format] ?? a.format}</h2>
                <span className="text-xs text-muted-foreground">{a.source}</span>
              </div>
              <p className="mb-2 text-xs font-medium">{a.title}</p>
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap text-xs text-muted-foreground">
                {a.content}
              </pre>
            </div>
          ))}
        </div>
      )}

      {tab === "video" && videoReport && (
        <div className="grid max-w-4xl gap-4">
          <p className="text-sm text-muted-foreground">{videoReport.variant_count} variantes geradas</p>
          {videoReport.variants.map((v) => (
            <div key={v.platform} className="rounded-lg border border-border bg-card p-4">
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-sm font-semibold">{PLATFORM_LABELS[v.platform] ?? v.platform}</h2>
                <span className="text-xs text-muted-foreground">{v.source}</span>
              </div>
              <p className="mb-1 text-xs font-medium">{v.title}</p>
              <p className="mb-2 text-xs text-muted-foreground">{v.description}</p>
              <p className="mb-2 text-xs">
                <span className="text-muted-foreground">Hashtags: </span>
                {(v.hashtags || []).map((h) => `#${h}`).join(" ")}
              </p>
              <p className="text-xs text-muted-foreground">
                Crop {v.crop_spec.width}×{v.crop_spec.height} · max {v.crop_spec.max_duration_seconds}s ·{" "}
                {v.crop_spec.safe_zone}
              </p>
              {v.data?.ready_to_publish === true && (
                <p className="mt-1 text-xs text-green-600">Pronto para publicar (render_ref presente)</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
