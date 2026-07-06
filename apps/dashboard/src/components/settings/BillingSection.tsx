"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type BillingPlan, type OrgBilling } from "@/lib/api";
import { getOrganizationId } from "@/lib/org-context";

function formatUsd(cents: number | null): string {
  if (cents === null) return "Custom";
  if (cents === 0) return "Free";
  return `$${(cents / 100).toFixed(0)}/mo`;
}

function formatQuota(used: number, limit: number): string {
  if (limit <= 0) return `${used} / ∞`;
  return `${used} / ${limit}`;
}

export function BillingSection() {
  const [orgId, setOrgId] = useState<string | null>(null);
  const [billing, setBilling] = useState<OrgBilling | null>(null);
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (id: string) => {
    setError(null);
    try {
      const [b, p] = await Promise.all([api.getOrgBilling(id), api.listBillingPlans()]);
      setBilling(b);
      setPlans(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao carregar billing");
    }
  }, []);

  useEffect(() => {
    const id = getOrganizationId();
    setOrgId(id);
    if (id) void load(id);
  }, [load]);

  async function handleCheckout(planSlug: string) {
    if (!orgId) return;
    setLoading(true);
    setError(null);
    try {
      const { checkout_url } = await api.startBillingCheckout(orgId, planSlug);
      window.location.href = checkout_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Checkout indisponível");
      setLoading(false);
    }
  }

  async function handlePortal() {
    if (!orgId) return;
    setLoading(true);
    setError(null);
    try {
      const { portal_url } = await api.openBillingPortal(orgId);
      window.location.href = portal_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Portal indisponível");
      setLoading(false);
    }
  }

  if (!orgId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Plano e créditos</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Selecione uma organização na barra lateral.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Plano e créditos</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p className="text-sm text-red-500">{error}</p>}
        {billing && (
          <div className="rounded-md border border-border p-4 text-sm">
            <p>
              Plano atual: <strong>{billing.plan_name}</strong> ({billing.subscription_status})
            </p>
            <p className="mt-1 text-muted-foreground">
              Créditos: <strong>{billing.credits_balance}</strong> / {billing.monthly_credits} por ciclo
            </p>
            <p className="mt-1 text-muted-foreground">
              Pipelines este mês:{" "}
              <strong>{formatQuota(billing.monthly_pipelines_used, billing.monthly_pipeline_quota)}</strong>
            </p>
            <p className="text-muted-foreground">
              Concorrentes:{" "}
              <strong>{formatQuota(billing.concurrent_pipelines_active, billing.max_concurrent_pipelines)}</strong>
            </p>
            {billing.has_stripe_customer && billing.stripe_enabled && (
              <Button variant="outline" size="sm" className="mt-3" disabled={loading} onClick={() => void handlePortal()}>
                Gerenciar assinatura
              </Button>
            )}
          </div>
        )}
        <div className="grid gap-3 sm:grid-cols-3">
          {plans.map((plan) => (
            <div key={plan.slug} className="rounded-md border border-border p-4 text-sm">
              <p className="font-medium">{plan.name}</p>
              <p className="text-muted-foreground">{plan.monthly_credits} créditos/mês</p>
              <p className="text-xs text-muted-foreground">
                {plan.monthly_pipeline_quota <= 0
                  ? "Pipelines ilimitados"
                  : `${plan.monthly_pipeline_quota} pipelines/mês`}
                {" · "}
                {plan.max_concurrent_pipelines <= 0
                  ? "concorrência ilimitada"
                  : `${plan.max_concurrent_pipelines} simultâneos`}
              </p>
              <p className="mt-1 font-mono text-xs">{formatUsd(plan.price_usd_cents)}</p>
              {plan.slug !== "free" && plan.stripe_available && billing?.plan_slug !== plan.slug && (
                <Button
                  size="sm"
                  className="mt-3"
                  disabled={loading}
                  onClick={() => void handleCheckout(plan.slug)}
                >
                  Assinar
                </Button>
              )}
            </div>
          ))}
        </div>
        {billing && !billing.stripe_enabled && (
          <p className="text-xs text-muted-foreground">
            Stripe não configurado — apenas plano free com créditos iniciais.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
