"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type OrganizationApiKey, type OrganizationApiKeyCreated } from "@/lib/api";
import { getOrganizationId } from "@/lib/org-context";

export function ApiKeysSection() {
  const [orgId, setOrgId] = useState<string | null>(null);
  const [keys, setKeys] = useState<OrganizationApiKey[]>([]);
  const [name, setName] = useState("");
  const [scope, setScope] = useState<"read" | "write">("read");
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (id: string) => {
    setError(null);
    try {
      setKeys(await api.listApiKeys(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao carregar API keys");
    }
  }, []);

  useEffect(() => {
    const id = getOrganizationId();
    setOrgId(id);
    if (id) void load(id);
  }, [load]);

  async function handleCreate() {
    if (!orgId || !name.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const created: OrganizationApiKeyCreated = await api.createApiKey(orgId, {
        name: name.trim(),
        scope,
      });
      setCreatedKey(created.api_key);
      setName("");
      await load(orgId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao criar API key");
    } finally {
      setLoading(false);
    }
  }

  async function handleRevoke(keyId: string) {
    if (!orgId) return;
    setError(null);
    try {
      await api.revokeApiKey(orgId, keyId);
      await load(orgId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao revogar API key");
    }
  }

  if (!orgId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>API keys</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Selecione uma organização na barra lateral para gerenciar API keys.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>API keys</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Use o header <code className="rounded bg-muted px-1">X-API-Key</code> para acesso programático.
          Requer admin da organização.
        </p>
        {error && <p className="text-sm text-red-500">{error}</p>}
        {createdKey && (
          <div className="rounded-md border border-amber-500/50 bg-amber-500/10 p-3 text-sm">
            <p className="font-medium">Copie agora — não será exibida novamente:</p>
            <code className="mt-2 block break-all font-mono text-xs">{createdKey}</code>
            <Button variant="ghost" size="sm" className="mt-2" onClick={() => setCreatedKey(null)}>
              Fechar
            </Button>
          </div>
        )}
        <div className="flex flex-wrap items-end gap-2">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Nome</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="CI / integração" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Escopo</label>
            <select
              className="h-9 rounded-md border border-border bg-background px-3 text-sm"
              value={scope}
              onChange={(e) => setScope(e.target.value as "read" | "write")}
            >
              <option value="read">read (viewer)</option>
              <option value="write">write (editor)</option>
            </select>
          </div>
          <Button onClick={handleCreate} disabled={loading || !name.trim()}>
            Criar key
          </Button>
        </div>
        <div className="divide-y divide-border">
          {keys.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">Nenhuma API key ativa.</p>
          ) : (
            keys.map((k) => (
              <div key={k.id} className="flex items-center justify-between gap-4 py-3 text-sm">
                <div>
                  <p className="font-medium">{k.name}</p>
                  <p className="font-mono text-xs text-muted-foreground">
                    cos_{k.key_prefix}_… · {k.scope} · {k.rate_limit_per_minute}/min
                  </p>
                </div>
                <Button variant="outline" size="sm" onClick={() => void handleRevoke(k.id)}>
                  Revogar
                </Button>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
