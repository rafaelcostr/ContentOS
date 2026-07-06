"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { parseApiError } from "@/lib/i18n";
import { useAuthStore } from "@/stores/auth";

function finishLogin(
  setTokens: (access: string, refresh: string) => void,
  access: string,
  refresh: string
) {
  if (!access) {
    throw new Error("Resposta de login inválida. Tente novamente.");
  }
  setTokens(access, refresh);
  window.location.href = "/projects";
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");
  const setTokens = useAuthStore((s) => s.setTokens);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const tokens = await api.login(email.trim(), password);
      finishLogin(setTokens, tokens.access_token, tokens.refresh_token);
    } catch (err) {
      setError(parseApiError(err));
      setLoading(false);
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      await api.register(email.trim(), password, fullName.trim() || "Usuário");
      setSuccess("Conta criada! Entrando...");
      const tokens = await api.login(email.trim(), password);
      finishLogin(setTokens, tokens.access_token, tokens.refresh_token);
    } catch (err) {
      setError(parseApiError(err));
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>ContentOS</CardTitle>
          <CardDescription>
            {mode === "login" ? "Entre na sua conta" : "Crie sua conta para começar"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={mode === "login" ? handleLogin : handleRegister} className="space-y-4">
            {mode === "register" && (
              <Input
                placeholder="Nome completo"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            )}
            <Input
              type="email"
              placeholder="E-mail"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <Input
              type="password"
              placeholder="Senha (mín. 6 caracteres)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={6}
              required
            />
            {error && <p className="text-sm text-red-400">{error}</p>}
            {success && <p className="text-sm text-emerald-400">{success}</p>}
            <Button type="submit" className="w-full" disabled={loading || !email.trim() || !password}>
              {loading
                ? "Aguarde..."
                : mode === "login"
                  ? "Entrar"
                  : "Criar conta e entrar"}
            </Button>
          </form>
          <button
            type="button"
            className="mt-4 w-full text-center text-sm text-muted-foreground hover:text-foreground"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError("");
              setSuccess("");
            }}
          >
            {mode === "login"
              ? "Não tem conta? Criar conta"
              : "Já tem conta? Entrar"}
          </button>
        </CardContent>
      </Card>
    </div>
  );
}
