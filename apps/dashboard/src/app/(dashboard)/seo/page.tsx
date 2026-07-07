"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, Project, SeoPackage } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const SAMPLE_PAYLOAD = {
  topic: "GTA 6",
  script: {
    title: "GTA 6 — tudo que você precisa saber",
    hook: "Você sabia que GTA 6 vai mudar os jogos para sempre?",
    development: "Neste vídeo mostramos mapas, personagens e datas de lançamento.",
    call_to_action: "Comenta qual cidade você quer explorar primeiro!",
  },
  project_dna: {
    brand_keywords: ["gta6", "rockstar", "games", "openworld"],
  },
};

const PLATFORM_LABELS: Record<string, string> = {
  tiktok: "TikTok",
  youtube_shorts: "YouTube Shorts",
  instagram_reels: "Instagram Reels",
};

export default function SeoPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [topic, setTopic] = useState("GTA 6");

  const { data: projects = [] } = useQuery({
    queryKey: ["projects"],
    queryFn: api.getProjects,
  });

  useEffect(() => {
    if (projects.length && !projectId) setProjectId(projects[0].id);
  }, [projects, projectId]);

  const optimizeMutation = useMutation({
    mutationFn: () =>
      api.optimizeSeo({
        project_id: projectId!,
        topic,
        payload: { ...SAMPLE_PAYLOAD, topic },
      }),
  });

  const pkg: SeoPackage | undefined = optimizeMutation.data;

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">SEO Engine</h1>
        <p className="text-sm text-muted-foreground">
          Títulos, hashtags e descrições otimizados para TikTok, Shorts e Reels (V5.2.3)
        </p>
      </header>

      <div className="mb-6 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-xs text-muted-foreground">Projeto</label>
          <select
            className="mt-1 block rounded-md border border-border bg-background px-3 py-2 text-sm"
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
        <div>
          <label className="text-xs text-muted-foreground">Tema</label>
          <Input className="mt-1 w-64" value={topic} onChange={(e) => setTopic(e.target.value)} />
        </div>
        <Button onClick={() => optimizeMutation.mutate()} disabled={!projectId || optimizeMutation.isPending}>
          {optimizeMutation.isPending ? "Otimizando…" : "Otimizar SEO"}
        </Button>
      </div>

      {pkg && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-border p-4">
              <dt className="text-xs text-muted-foreground">SEO Score</dt>
              <dd className="text-3xl font-bold">{pkg.seo_score.toFixed(0)}</dd>
            </div>
            <div className="rounded-lg border border-border p-4 sm:col-span-2">
              <dt className="text-xs text-muted-foreground">Título principal</dt>
              <dd className="font-medium">{pkg.title}</dd>
            </div>
          </div>

          <section className="rounded-lg border border-border p-4">
            <h2 className="mb-2 font-semibold">Descrição</h2>
            <p className="whitespace-pre-wrap text-sm text-muted-foreground">{pkg.description}</p>
          </section>

          <section className="rounded-lg border border-border p-4">
            <h2 className="mb-2 font-semibold">Hashtags</h2>
            <div className="flex flex-wrap gap-2">
              {pkg.hashtags.map((tag) => (
                <span key={tag} className="rounded-full bg-muted px-2 py-1 text-xs">
                  #{tag}
                </span>
              ))}
            </div>
          </section>

          {pkg.title_variants.length > 0 && (
            <section className="rounded-lg border border-border p-4">
              <h2 className="mb-2 font-semibold">Variações de título</h2>
              <ul className="list-inside list-disc text-sm text-muted-foreground">
                {pkg.title_variants.map((v) => (
                  <li key={v}>{v}</li>
                ))}
              </ul>
            </section>
          )}

          <section className="grid gap-4 lg:grid-cols-3">
            {Object.entries(pkg.platforms).map(([key, meta]) => (
              <div key={key} className="rounded-lg border border-border p-4">
                <h3 className="mb-2 font-semibold">{PLATFORM_LABELS[key] ?? key}</h3>
                <p className="text-sm font-medium">{meta.title}</p>
                <p className="mt-2 text-xs text-muted-foreground line-clamp-4">{meta.description}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {meta.hashtags.slice(0, 6).map((tag) => (
                    <span key={tag} className="text-xs text-muted-foreground">
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </section>

          {pkg.recommendations.length > 0 && (
            <section className="rounded-lg border border-dashed border-border p-4">
              <h2 className="mb-2 font-semibold">Recomendações</h2>
              <ul className="list-inside list-disc text-sm text-muted-foreground">
                {pkg.recommendations.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
