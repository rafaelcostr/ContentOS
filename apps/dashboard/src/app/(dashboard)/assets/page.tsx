"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, Asset } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatBytes, formatDate } from "@/lib/utils";

const CATEGORIES = ["", "takes", "assets", "audio", "captions", "renders", "thumbs"];

export default function AssetsPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [tag, setTag] = useState("");
  const [theme, setTheme] = useState("");
  const [game, setGame] = useState("");
  const [character, setCharacter] = useState("");
  const [motion, setMotion] = useState("");
  const [color, setColor] = useState("");
  const [objects, setObjects] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [newTag, setNewTag] = useState("");

  const filters = useMemo(
    () => ({
      q: q || undefined,
      category: category || undefined,
      tag: tag || undefined,
      theme: theme || undefined,
      game: game || undefined,
      character: character || undefined,
      motion: motion || undefined,
      color: color || undefined,
      objects: objects || undefined,
      limit: 100,
    }),
    [q, category, tag, theme, game, character, motion, color, objects]
  );

  const { data: stats } = useQuery({
    queryKey: ["storage-stats"],
    queryFn: api.getAssetIndexStats,
  });

  const { data: assets = [], isLoading, isFetching } = useQuery({
    queryKey: ["assets-search", filters],
    queryFn: () => api.searchAssets(filters),
  });

  const selected = useMemo(
    () => assets.find((a) => a.id === selectedId) ?? assets[0] ?? null,
    [assets, selectedId]
  );

  const tagMutation = useMutation({
    mutationFn: ({ id, tags }: { id: string; tags: string[] }) => api.tagAsset(id, tags),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets-search"] });
      qc.invalidateQueries({ queryKey: ["storage-stats"] });
      setNewTag("");
    },
  });

  function handleAddTag() {
    if (!selected || !newTag.trim()) return;
    const tags = [...(selected.tags ?? [])];
    if (!tags.includes(newTag.trim())) tags.push(newTag.trim());
    tagMutation.mutate({ id: selected.id, tags });
  }

  function clearFilters() {
    setQ("");
    setCategory("");
    setTag("");
    setTheme("");
    setGame("");
    setCharacter("");
    setMotion("");
    setColor("");
    setObjects("");
  }

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Assets</h1>
        <p className="text-sm text-muted-foreground">
          Biblioteca indexada — busca por tema, tags, jogo, personagem, movimento e cor
        </p>
      </header>

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Total" value={stats?.total_assets ?? 0} />
        <Stat label="Indexados (hash)" value={stats?.indexed_hashes ?? 0} />
        <Stat label="Espaço" value={`${stats?.total_mb ?? 0} MB`} />
        <Stat label="Resultados" value={assets.length} />
      </div>

      <div className="mb-6 space-y-3 rounded-lg border border-border bg-card p-4">
        <div className="flex flex-wrap gap-3">
          <Input
            placeholder="Busca livre (key, tema, jogo…)"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="max-w-xs"
          />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-sm"
          >
            {CATEGORIES.map((c) => (
              <option key={c || "all"} value={c}>
                {c || "Todas categorias"}
              </option>
            ))}
          </select>
          <Input placeholder="Tag" value={tag} onChange={(e) => setTag(e.target.value)} className="max-w-[140px]" />
        </div>
        <div className="flex flex-wrap gap-3">
          <Input placeholder="Tema" value={theme} onChange={(e) => setTheme(e.target.value)} className="max-w-[140px]" />
          <Input placeholder="Jogo" value={game} onChange={(e) => setGame(e.target.value)} className="max-w-[140px]" />
          <Input
            placeholder="Personagem"
            value={character}
            onChange={(e) => setCharacter(e.target.value)}
            className="max-w-[140px]"
          />
          <Input
            placeholder="Movimento"
            value={motion}
            onChange={(e) => setMotion(e.target.value)}
            className="max-w-[140px]"
          />
          <Input placeholder="Cor" value={color} onChange={(e) => setColor(e.target.value)} className="max-w-[120px]" />
          <Input
            placeholder="Objetos"
            value={objects}
            onChange={(e) => setObjects(e.target.value)}
            className="max-w-[140px]"
          />
          <Button type="button" variant="outline" size="sm" onClick={clearFilters}>
            Limpar
          </Button>
          {isFetching && <span className="self-center text-xs text-muted-foreground">Atualizando...</span>}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="rounded-lg border border-border bg-card lg:col-span-2">
          <div className="border-b border-border px-4 py-3 text-sm font-semibold">Biblioteca</div>
          {isLoading ? (
            <p className="p-4 text-sm text-muted-foreground">Carregando...</p>
          ) : assets.length === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">Nenhum asset encontrado.</p>
          ) : (
            <div className="max-h-[28rem] space-y-0 overflow-y-auto divide-y divide-border">
              {assets.map((asset) => (
                <button
                  key={asset.id}
                  type="button"
                  onClick={() => setSelectedId(asset.id)}
                  className={`flex w-full items-start justify-between gap-3 px-4 py-3 text-left text-sm hover:bg-muted/50 ${
                    selected?.id === asset.id ? "bg-primary/10" : ""
                  }`}
                >
                  <div className="min-w-0">
                    <p className="truncate font-mono text-xs">{asset.object_key}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {asset.category} · {metaSummary(asset)} · v{asset.version ?? 1}
                    </p>
                    {asset.tags && asset.tags.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {asset.tags.slice(0, 4).map((t) => (
                          <span key={t} className="rounded bg-muted px-1.5 py-0.5 text-[10px]">
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground">{formatBytes(asset.size_bytes)}</span>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-lg border border-border bg-card p-5">
          <h2 className="mb-4 font-semibold">Detalhe</h2>
          {!selected ? (
            <p className="text-sm text-muted-foreground">Selecione um asset</p>
          ) : (
            <AssetDetail
              asset={selected}
              newTag={newTag}
              setNewTag={setNewTag}
              onAddTag={handleAddTag}
              tagging={tagMutation.isPending}
            />
          )}
        </section>
      </div>
    </div>
  );
}

function metaSummary(asset: Asset): string {
  const m = asset.metadata_ || {};
  const parts = [m.theme, m.game, m.character, m.motion].filter(Boolean);
  return parts.length ? parts.join(" · ") : asset.content_type;
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </div>
  );
}

function AssetDetail({
  asset,
  newTag,
  setNewTag,
  onAddTag,
  tagging,
}: {
  asset: Asset;
  newTag: string;
  setNewTag: (v: string) => void;
  onAddTag: () => void;
  tagging: boolean;
}) {
  const isImage = asset.content_type.startsWith("image/");
  const isVideo = asset.content_type.startsWith("video/");
  const isAudio = asset.content_type.startsWith("audio/");
  const meta = asset.metadata_ || {};
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [presignedUrl, setPresignedUrl] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    setPreviewUrl(null);
    setPresignedUrl(null);
    setPreviewError("");
    setPreviewLoading(true);

    (async () => {
      try {
        const [content, preview] = await Promise.all([
          api.getAssetContentObjectUrl(asset.id),
          api.getAssetPreview(asset.id).catch(() => null),
        ]);
        if (!active) {
          URL.revokeObjectURL(content.url);
          return;
        }
        objectUrl = content.url;
        setPreviewUrl(content.url);
        if (preview?.available && preview.url) setPresignedUrl(preview.url);
      } catch (err) {
        if (active) setPreviewError(err instanceof Error ? err.message : "Falha ao carregar preview");
      } finally {
        if (active) setPreviewLoading(false);
      }
    })();

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [asset.id]);

  return (
    <div className="space-y-4 text-sm">
      <div className="flex min-h-36 items-center justify-center overflow-hidden rounded-md border border-dashed border-border bg-muted/30">
        {previewLoading && <span className="text-xs text-muted-foreground">Carregando preview...</span>}
        {!previewLoading && previewError && (
          <span className="px-3 text-center text-xs text-red-400">{previewError}</span>
        )}
        {!previewLoading && !previewError && previewUrl && isImage && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={previewUrl} alt={asset.object_key} className="max-h-48 w-full object-contain" />
        )}
        {!previewLoading && !previewError && previewUrl && isVideo && (
          <video src={previewUrl} controls className="max-h-48 w-full" preload="metadata" />
        )}
        {!previewLoading && !previewError && previewUrl && isAudio && (
          <audio src={previewUrl} controls className="w-full px-3" />
        )}
        {!previewLoading && !previewError && previewUrl && !isImage && !isVideo && !isAudio && (
          <span className="text-xs text-muted-foreground">{asset.content_type}</span>
        )}
        {!previewLoading && !previewError && !previewUrl && (
          <span className="text-xs text-muted-foreground">Sem preview</span>
        )}
      </div>
      {presignedUrl && (
        <a
          href={presignedUrl}
          target="_blank"
          rel="noreferrer"
          className="block truncate text-xs text-primary hover:underline"
        >
          Abrir URL assinada (MinIO)
        </a>
      )}

      <Field label="ID" value={asset.id} mono />
      <Field label="Key" value={asset.object_key} mono />
      <Field label="Categoria" value={asset.category} />
      <Field label="Tamanho" value={formatBytes(asset.size_bytes)} />
      <Field label="Versão" value={String(asset.version ?? 1)} />
      <Field label="SHA-256" value={asset.sha256 ? `${asset.sha256.slice(0, 16)}…` : "—"} mono />
      <Field label="Criado" value={formatDate(asset.created_at)} />

      <div>
        <p className="mb-2 text-xs text-muted-foreground">Metadados de busca</p>
        <div className="space-y-1 text-xs">
          <Field label="Tema" value={String(meta.theme ?? "—")} />
          <Field label="Jogo" value={String(meta.game ?? "—")} />
          <Field label="Personagem" value={String(meta.character ?? "—")} />
          <Field label="Movimento" value={String(meta.motion ?? "—")} />
          <Field label="Cor" value={String(meta.color ?? "—")} />
          <Field
            label="Objetos"
            value={Array.isArray(meta.objects) ? meta.objects.join(", ") : String(meta.objects ?? "—")}
          />
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs text-muted-foreground">Tags</p>
        <div className="mb-2 flex flex-wrap gap-1">
          {(asset.tags ?? []).length === 0 ? (
            <span className="text-xs text-muted-foreground">Sem tags</span>
          ) : (
            asset.tags!.map((t) => (
              <span key={t} className="rounded-md border border-border px-2 py-0.5 text-xs">
                {t}
              </span>
            ))
          )}
        </div>
        <div className="flex gap-2">
          <Input
            placeholder="Nova tag"
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onAddTag()}
          />
          <Button type="button" size="sm" disabled={tagging || !newTag.trim()} onClick={onAddTag}>
            {tagging ? "..." : "Add"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`break-all ${mono ? "font-mono text-xs" : ""}`}>{value}</p>
    </div>
  );
}
