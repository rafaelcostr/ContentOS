/** Rótulos em português para status e UI compartilhada. */

export const STATUS_LABELS: Record<string, string> = {
  pending: "Aguardando",
  running: "Executando",
  completed: "Concluído",
  failed: "Falhou",
  retrying: "Tentando novamente",
  cancelled: "Cancelado",
  online: "Online",
  offline: "Offline",
  idle: "Ocioso",
  queued: "Na fila",
  healthy: "Saudável",
  loading: "Carregando",
  ready: "Pronto",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function parseApiError(err: unknown): string {
  if (!(err instanceof Error)) return "Erro desconhecido. Tente novamente.";
  const msg = err.message;
  if (msg.includes("401")) return "Sessão expirada. Faça login novamente.";
  if (msg.includes("403")) return "Sem permissão para esta ação.";
  if (msg.includes("404")) return "Recurso não encontrado.";
  if (msg.includes("422")) return "Dados inválidos. Verifique os campos.";
  if (msg.includes("500")) return "Erro no servidor. Tente mais tarde.";
  return msg.replace(/^API \d+: /, "").slice(0, 200) || "Erro ao comunicar com a API.";
}
