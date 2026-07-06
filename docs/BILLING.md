# Billing — Stripe (V3 Tier C3)

Organization-scoped subscriptions and a credit ledger for pipeline usage.

## Plans

| Slug | Credits/month | Stripe |
|------|---------------|--------|
| `free` | 50 | — (bootstrap grant) |
| `pro` | 500 | `STRIPE_PRICE_PRO` |
| `enterprise` | 5000 | `STRIPE_PRICE_ENTERPRISE` |

Plans are seeded on gateway startup (`billing_seed.ensure_billing_plans`). Each organization gets an `organization_billing` row with initial free credits.

## Credits

- Creating a pipeline costs `BILLING_PIPELINE_CREDIT_COST` credits (default **1**).
- Set `BILLING_ENFORCE_CREDITS=false` to disable checks in local dev.
- Insufficient balance returns **402 Payment Required**.
- All movements are recorded in `credit_transactions`.

## API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/billing/plans` | JWT / API key | List plans |
| `GET` | `/api/v1/organizations/{org_id}/billing` | Member | Balance + plan |
| `POST` | `/api/v1/organizations/{org_id}/billing/checkout` | Org admin | Stripe Checkout URL |
| `POST` | `/api/v1/organizations/{org_id}/billing/portal` | Org admin | Stripe Customer Portal |
| `POST` | `/api/v1/billing/webhook` | Stripe signature | Webhook handler |

## Environment

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_ENTERPRISE=price_...
STRIPE_SUCCESS_URL=http://localhost:3000/settings?billing=success
STRIPE_CANCEL_URL=http://localhost:3000/settings?billing=cancel
BILLING_PIPELINE_CREDIT_COST=1
BILLING_ENFORCE_CREDITS=true
```

## Stripe test mode

1. Create products/prices in [Stripe Dashboard](https://dashboard.stripe.com/test/products).
2. Set `STRIPE_PRICE_PRO` / `STRIPE_PRICE_ENTERPRISE` to the price IDs.
3. Forward webhooks locally:

```bash
stripe listen --forward-to localhost:8000/api/v1/billing/webhook
```

4. Use test card `4242 4242 4242 4242`.

## Webhook events

| Event | Action |
|-------|--------|
| `checkout.session.completed` | Activate plan + grant credits |
| `customer.subscription.updated` | Sync plan/status |
| `customer.subscription.deleted` | Downgrade to `free` |
| `invoice.paid` | Monthly credit grant (active/trialing) |

Metadata `organization_id` and `plan_slug` must be present on Checkout sessions (set automatically by the gateway).

## Quotas (Tier C4)

Plans also define pipeline quotas. See [QUOTAS.md](./QUOTAS.md).
