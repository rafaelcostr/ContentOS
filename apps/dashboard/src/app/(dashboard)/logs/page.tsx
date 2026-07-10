"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function LogsPage() {
  const { data: logs = [], isLoading } = useQuery({ queryKey: ["logs"], queryFn: () => api.getLogs() });

  return (
    <div className="p-8">
      <h1 className="mb-6 text-2xl font-bold">Registros</h1>
      <Card>
        <CardHeader><CardTitle>Logs recentes</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Carregando...</p>
          ) : logs.length === 0 ? (
            <p className="text-muted-foreground">Nenhum log</p>
          ) : (
            <div className="max-h-[600px] overflow-y-auto font-mono text-xs">
              {logs.map((log) => (
                <div key={log.id} className="mb-2 flex gap-3 border-b border-border/50 pb-2">
                  <span className="shrink-0 text-muted-foreground">{formatDate(log.created_at)}</span>
                  <span className={log.level === "error" ? "text-red-400" : "text-foreground"}>
                    [{log.agent ?? "system"}] {log.message}
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
