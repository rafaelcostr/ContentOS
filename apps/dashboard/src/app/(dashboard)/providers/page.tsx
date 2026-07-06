"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

const PROVIDER_INFO: Record<string, { label: string; description: string }> = {
  ollama: { label: "Ollama + Qwen3", description: "LLM local — roteiros, cenas, metadados" },
  openai: { label: "OpenAI GPT", description: "LLM cloud — alternativa paga" },
  piper: { label: "Piper TTS", description: "Narração local em PT-BR" },
  elevenlabs: { label: "ElevenLabs", description: "TTS cloud premium" },
  local: { label: "Whisper Large-v3", description: "Legendas locais via faster-whisper" },
  whisper: { label: "Whisper Local", description: "Alias para whisper local" },
  openai_whisper: { label: "OpenAI Whisper", description: "API cloud de transcrição" },
};

function ProviderCard({ type, active, available }: { type: string; active: string; available: string[] }) {
  const info = PROVIDER_INFO[active] ?? { label: active, description: "Provider configurado" };
  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{type}</p>
      <h2 className="mt-2 text-lg font-semibold">{info.label}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{info.description}</p>
      <p className="mt-4 text-xs text-muted-foreground">
        Ativo: <span className="font-mono text-foreground">{active}</span>
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {available.map((p) => (
          <span
            key={p}
            className={`rounded-full px-2 py-0.5 text-xs ${
              p === active ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
            }`}
          >
            {p}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function ProvidersPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["providers"],
    queryFn: api.getProviderStatus,
  });
  const { data: health } = useQuery({
    queryKey: ["providers-health"],
    queryFn: api.getProviderHealth,
    refetchInterval: 15000,
  });

  return (
    <div className="p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Provedores de IA</h1>
        <p className="text-sm text-muted-foreground">
          Camada de abstração — troque IA sem alterar agentes (Strategy Pattern)
        </p>
      </header>

      {health && (
        <div className={`mb-6 rounded-lg border p-4 ${health.all_healthy ? "border-emerald-500/50 bg-emerald-500/10" : "border-amber-500/50 bg-amber-500/10"}`}>
          <p className="text-sm font-medium">
            Stack local: {health.all_healthy ? "Todos os serviços online" : "Aguardando serviços..."}
          </p>
          <div className="mt-2 flex flex-wrap gap-3">
            {health.providers.map((p) => (
              <span key={p.name} className="text-xs font-mono">
                <span className={p.healthy ? "text-emerald-400" : "text-amber-400"}>
                  {p.healthy ? "●" : "○"}
                </span>{" "}
                {p.name}: {p.detail || p.url}
              </span>
            ))}
          </div>
        </div>
      )}

      {isLoading && <p className="text-muted-foreground">Carregando...</p>}
      {error && <p className="text-red-400">Erro ao carregar providers</p>}

      {data && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <ProviderCard type="Texto (LLM)" active={data.text} available={data.available_text} />
          <ProviderCard type="Voz (TTS)" active={data.speech} available={data.available_speech} />
          <ProviderCard type="Legendas (STT)" active={data.subtitle} available={data.available_subtitle} />
        </div>
      )}

      <section className="mt-8 rounded-lg border border-border bg-card p-6">
        <h2 className="font-semibold">Como trocar</h2>
        <pre className="mt-4 overflow-x-auto rounded-md bg-muted p-4 font-mono text-xs">
{`# .env
TEXT_PROVIDER=ollama      # ollama | openai
SPEECH_PROVIDER=piper     # piper | elevenlabs
SUBTITLE_PROVIDER=local   # local | openai

OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://ollama:11434
PIPER_URL=http://piper:5000
WHISPER_URL=http://whisper:8080`}
        </pre>
      </section>
    </div>
  );
}
