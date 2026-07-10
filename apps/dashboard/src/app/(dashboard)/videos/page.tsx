"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, ExternalLink, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type Video } from "@/lib/api";
import { formatDate, statusColor } from "@/lib/utils";
import { statusLabel } from "@/lib/i18n";

function safeFileName(title: string) {
  return `${title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || "video"}.mp4`;
}

function VideoActions({ video }: { video: Video }) {
  const queryClient = useQueryClient();
  const [isLoadingAsset, setIsLoadingAsset] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const renderAssetId = video.render_asset_id;

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteVideo(video.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["videos"] }),
    onError: (err) => setError(err instanceof Error ? err.message : "Falha ao excluir vídeo"),
  });

  async function openRender(download = false) {
    if (!renderAssetId) return;
    setIsLoadingAsset(true);
    setError(null);
    try {
      const { url } = await api.getAssetContentObjectUrl(renderAssetId);
      if (download) {
        const link = document.createElement("a");
        link.href = url;
        link.download = safeFileName(video.title);
        document.body.appendChild(link);
        link.click();
        link.remove();
      } else {
        window.open(url, "_blank", "noopener,noreferrer");
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao abrir vídeo");
    } finally {
      setIsLoadingAsset(false);
    }
  }

  return (
    <div className="mt-4 space-y-2">
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => openRender(false)}
          disabled={!renderAssetId || isLoadingAsset}
          title={renderAssetId ? "Abrir vídeo" : "Render não vinculado"}
        >
          <ExternalLink className="mr-2 h-4 w-4" />
          Abrir
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => openRender(true)}
          disabled={!renderAssetId || isLoadingAsset}
          title={renderAssetId ? "Baixar vídeo" : "Render não vinculado"}
        >
          <Download className="mr-2 h-4 w-4" />
          Baixar
        </Button>
        <Button
          size="sm"
          variant="destructive"
          onClick={() => deleteMutation.mutate()}
          disabled={deleteMutation.isPending}
          title="Excluir da lista"
        >
          <Trash2 className="mr-2 h-4 w-4" />
          Excluir
        </Button>
      </div>
      {!renderAssetId ? <p className="text-xs text-amber-400">Render ainda não vinculado a este registro.</p> : null}
      {error ? <p className="text-xs text-red-400">{error}</p> : null}
    </div>
  );
}

export default function VideosPage() {
  const { data: videos = [], isLoading } = useQuery({ queryKey: ["videos"], queryFn: api.getVideos });

  return (
    <div className="p-8">
      <h1 className="mb-6 text-2xl font-bold">Vídeos</h1>
      {isLoading ? (
        <p className="text-muted-foreground">Carregando...</p>
      ) : videos.length === 0 ? (
        <Card><CardContent className="p-8 text-center text-muted-foreground">Nenhum vídeo gerado ainda</CardContent></Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {videos.map((v) => (
            <Card key={v.id}>
              <CardHeader>
                <CardTitle className="text-base">{v.title}</CardTitle>
                <Badge className={statusColor(v.status)}>{statusLabel(v.status)}</Badge>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {v.width}x{v.height} - {v.duration_seconds?.toFixed(1) ?? "-"}s
                </p>
                <p className="mt-1 text-xs text-muted-foreground">{formatDate(v.created_at)}</p>
                <VideoActions video={v} />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
