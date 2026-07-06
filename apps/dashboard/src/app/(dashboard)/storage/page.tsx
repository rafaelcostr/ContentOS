"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { parseApiError } from "@/lib/i18n";
import { formatBytes, formatDate } from "@/lib/utils";


export default function StoragePage() {
  const [theme, setTheme] = useState("");
  const [label, setLabel] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const qc = useQueryClient();

  const { data: stats } = useQuery({ queryKey: ["storage-stats"], queryFn: api.getAssetIndexStats });
  const { data: takes = [] } = useQuery({ queryKey: ["assets-takes"], queryFn: () => api.getAssets("takes") });

  const upload = useMutation({
    mutationFn: () => api.uploadTake(theme.trim(), label.trim(), file!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assets-takes"] });
      qc.invalidateQueries({ queryKey: ["storage-stats"] });
      setTheme("");
      setLabel("");
      setFile(null);
      setErrorMsg("");
      setSuccessMsg("Take enviado com sucesso!");
    },
    onError: (err) => {
      setSuccessMsg("");
      setErrorMsg(parseApiError(err));
    },
  });

  function handleUpload(e: FormEvent) {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");
    if (!theme.trim() || !label.trim() || !file || upload.isPending) return;
    upload.mutate();
  }

  return (
    <div className="p-8">
      <div className="mb-6 flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Armazenamento</h1>
          <p className="text-sm text-muted-foreground">Upload de takes e estatísticas MinIO</p>
        </div>
        <Link href="/assets" className="text-sm text-primary hover:underline">
          Ver biblioteca de assets →
        </Link>

      </div>

      {(errorMsg || successMsg) && (
        <div
          className={`mb-6 rounded-md border px-4 py-3 text-sm ${
            errorMsg
              ? "border-red-500/50 bg-red-500/10 text-red-400"
              : "border-emerald-500/50 bg-emerald-500/10 text-emerald-400"
          }`}
        >
          {errorMsg || successMsg}
        </div>
      )}

      <div className="mb-8 grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Total de arquivos</p>
            <p className="text-2xl font-semibold">{stats?.total_assets ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Espaço usado</p>
            <p className="text-2xl font-semibold">{stats?.total_mb ?? 0} MB</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Takes</p>
            <p className="text-2xl font-semibold">{stats?.by_category?.takes?.count ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Hashes (dedup V2)</p>
            <p className="text-2xl font-semibold">{stats?.indexed_hashes ?? 0}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Enviar take de vídeo</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleUpload} className="space-y-3">
            <div className="grid gap-3 md:grid-cols-3">
              <Input
                placeholder="Tema (ex: GTA 6)"
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
              />
              <Input
                placeholder="Rótulo (ex: intro)"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
              />
              <Input type="file" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </div>
            <Button type="submit" disabled={!theme.trim() || !label.trim() || !file || upload.isPending}>
              {upload.isPending ? "Enviando..." : "Enviar para MinIO"}
            </Button>
            <p className="text-xs text-muted-foreground">Pressione Enter após selecionar o arquivo</p>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Biblioteca de takes</CardTitle>
        </CardHeader>
        <CardContent>
          {takes.length === 0 ? (
            <p className="text-muted-foreground">Nenhum take enviado</p>
          ) : (
            <div className="space-y-2">
              {takes.map((t) => (
                <div
                  key={t.id}
                  className="flex items-center justify-between rounded-md border border-border p-3 text-sm"
                >
                  <span className="font-mono">{t.object_key.split("/").pop()}</span>
                  <span className="text-muted-foreground">
                    {formatBytes(t.size_bytes)} — {formatDate(t.created_at)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
