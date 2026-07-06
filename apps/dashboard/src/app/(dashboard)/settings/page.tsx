import { ApiKeysSection } from "@/components/settings/ApiKeysSection";
import { BillingSection } from "@/components/settings/BillingSection";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const settings = [
  { key: "OPENAI_MODEL", value: "gpt-4o" },
  { key: "ELEVENLABS_VOICE_ID", value: "21m00Tcm4TlvDq8ikWAM" },
  { key: "MINIO_BUCKET", value: "contentos" },
  { key: "JWT_ACCESS_EXPIRE_MINUTES", value: "15" },
];

export default function SettingsPage() {
  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Configurações</h1>
      <BillingSection />
      <ApiKeysSection />
      <Card>
        <CardHeader><CardTitle>Variáveis de ambiente</CardTitle></CardHeader>
        <CardContent className="divide-y divide-border">
          {settings.map((s) => (
            <div key={s.key} className="flex items-center justify-between py-4">
              <span className="font-mono text-sm text-muted-foreground">{s.key}</span>
              <span className="rounded bg-muted px-3 py-1 font-mono text-sm">{s.value}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
