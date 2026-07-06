"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { getAccessToken } from "@/lib/auth-token";
import { useAuthStore } from "@/stores/auth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const logout = useAuthStore((s) => s.logout);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    setReady(true);
    api.me().catch(() => {
      logout();
      setError("Sessão inválida. Redirecionando para login...");
      router.replace("/login");
    });
  }, [router, logout]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center pl-64">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center pl-64">
        <p className="text-muted-foreground">Verificando sessão...</p>
      </div>
    );
  }

  return <>{children}</>;
}
