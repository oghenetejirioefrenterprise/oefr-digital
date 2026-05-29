# Phase 2 sub-project 3 — recurring billing

**Status:** Approved 2026-05-18 (delegated approval).
**PRD scope:** *"Recurring-billing capability (one product converted to a $9-49/month membership with quarterly refresh cadence)"*

---

## Goal

Convert one existing product (FMCSA New Carriers — $39 one-time) into ALSO offering a $29/month subscription with quarterly dataset refresh. The one-time Payment Link stays; the subscription is added alongside, not as a replacement. Storefront renders both CTAs when subscription Payment Link is present.

**Out of scope for this sub-project:** email automation, subscriber onboarding, refresh notifications — those belong to sub-project 4 (`customer-success` agent). Sub-project 3 is purely "make it possible to subscribe."

## Decisions

| Question | Decision | Reasoning |
|---|---|---|
| Which product gets the first subscription? | FMCSA New Carriers (May 2026) | Most demand signal (already $39 product, 15,770-row monthly-fresh dataset is naturally subscription-shaped) |
| Subscription price | $29/month | PRD range $9–49; $29 anchored to $39 one-time = slight discount per refresh ($29×3 = $87/quarterly vs $39 quarterly = $156/yr → ~44% savings) |
| Refresh cadence | Quarterly (every ~90 days) | PRD explicit; matches FMCSA's natural monthly churn cycle accumulating into quarterly deltas |
| Delivery mechanism (subscriber gets new CSV) | Email containing fresh Gist link each quarter | Existing one-time delivery is also Gist link from Stripe success page; consistent UX |
| Subscription Payment Link vs Stripe Checkout embed | Payment Link | Matches v1 storefront pattern; no client SDK needed |
| Where in the storefront page does subscription CTA live? | Below one-time CTA, secondary visual weight | One-time is primary (instant value); subscription is the "love this? get fresh data quarterly" cross-sell |

## Architecture

**New Stripe objects** (created via API in a one-shot script):
- Product: `dsl_fmcsa-carriers-monthly` — "New FMCSA Carriers — Monthly Subscription"
- Price: $29/month recurring
- Payment Link: subscription mode, links to this price

**Schema change — `launch-report.json` for FMCSA gets three new optional fields:**
- `stripe_subscription_product_id`
- `stripe_subscription_price_id`
- `stripe_subscription_payment_link_url`

**Storefront changes:**
- `lib/types.ts` — add the three optional fields to `LaunchReport`
- `components/CheckoutCTAs.tsx` — render subscription CTA below existing one-time + Gumroad CTAs when subscription fields present:
  ```
  Buy now — $39 via Stripe   [primary]
  Or buy on Gumroad           [secondary]
  ─────
  Or subscribe — $29/month (quarterly refresh)   [tertiary, smaller]
  ```

**Spec change — `spec.json` for FMCSA** gets a new `subscription_note` field that the product detail page renders if present:
- "Get this dataset refreshed every quarter — $29/month subscription. Quarterly delta included."

This narrative bit makes the subscription option understandable to the buyer.

**No new scheduler cycles.** No new agents. No webhook listener.

## Subscriber tracking (for sub-project 4 to consume)

When the script creates the subscription product/price, it ALSO writes the subscription metadata to a new tracking file:

`state/subscription-products.json`:
```json
{
  "version": 1,
  "products": {
    "new-fmcsa-carrier-leads-2026-05": {
      "stripe_subscription_product_id": "prod_XXX",
      "stripe_subscription_price_id": "price_XXX",
      "stripe_subscription_payment_link_url": "https://buy.stripe.com/...",
      "monthly_price_usd": 29,
      "refresh_cadence_days": 90,
      "next_refresh_due": "2026-08-16"
    }
  }
}
```

Sub-project 4's customer-success agent will read this file to know what to email subscribers about and when refreshes are due.

## Tasks

1. Write `scripts/create_fmcsa_subscription.py` — uses `STRIPE_SECRET` from env; creates Product + Price + Payment Link; updates `state/products/new-fmcsa-carrier-leads-2026-05/launch-report.json`; creates `state/subscription-products.json`. Idempotent (checks existing before creating).
2. Run the script in this environment to create the live Stripe objects.
3. Update `site/lib/types.ts` — add three new optional fields to `LaunchReport`; add `subscription_note?: string` to `ProductSpec`.
4. Update `site/components/CheckoutCTAs.tsx` — add subscription CTA block (conditional on `launch.stripe_subscription_payment_link_url`).
5. Update `site/app/products/[slug]/page.tsx` — render `spec.subscription_note` if present, near the CTAs.
6. Add `subscription_note` to FMCSA's `spec.json`: "Get this dataset refreshed every quarter — $29/month subscription. Quarterly delta included; cancel anytime."
7. Local build + smoke test (verify FMCSA page shows both one-time + subscription CTAs).
8. Commit + push. Vercel auto-deploys.
9. Live smoke test https://data.oefrenterprise.com/products/new-fmcsa-carrier-leads-2026-05.

## Engineer agent identity update

Append to engineer identity (under existing storefront verification section):

```markdown
## Subscription products

When a product has a subscription Payment Link in `state/subscription-products.json`:
- During smoke test, ALSO `curl -fsSL` the subscription Payment Link and verify 200
- During quarterly refresh: generate fresh dataset, upload new Gist, write new Gist URL to `state/subscription-refresh-log/{slug}-{YYYY-Qq}.json` for customer-success to consume.

Quarterly refresh automation belongs to a future cycle; v1 expects founder/CEO to manually trigger via `trinity run "Refresh subscription product fmcsa" -e engineer`.
```
