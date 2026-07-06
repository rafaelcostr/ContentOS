"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { formatDate, statusColor } from "@/lib/utils";
import { statusLabel } from "@/lib/i18n";

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
                <p className="text-sm text-muted-foreground">{v.width}x{v.height} — {v.duration_seconds ?? "—"}s</p>
                <p className="mt-1 text-xs text-muted-foreground">{formatDate(v.created_at)}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
