# Phase 2 sub-project 4 — customer-success agent

**Status:** Approved 2026-05-18 (delegated).
**PRD scope:** *"activates at first paid sale; handles onboarding email, day-3 check-in, refresh notifications, support inbox triage."*

---

## Goal

Stand up a `customer-success` employee that polls Stripe for new charges/subscriptions every 2 hours, sends welcome emails to new customers, sends day-3 check-in emails, and sends quarterly refresh notifications to active subscribers when the engineer has uploaded fresh data.

**Support inbox triage is deferred** — there's no inbox to triage until customers actually email us. v1 sets the reply-to to `info@oefrenterprise.com`; routing to an agent comes in v2 (Phase 3+ when a marketing-lead-style agent exists).

## Architecture

**New employee:** `.trinity/employees/customer-success/identity.md`

**New scheduler cycle:** `customer_sweep` every 2 hours (cron `0 */2 * * *`)

**New helper script:** `scripts/email_sender.py` — thin wrapper around `smtplib` for Gmail SMTP.

**State files (new):**

- `state/stripe-poll-cursor.json` — `{"last_polled_at": "<ISO-8601 UTC>"}`. Cursor for incremental polling.
- `state/customers/<email-safe>.json` — one file per buyer. Schema:
  ```json
  {
    "email": "buyer@example.com",
    "first_purchase_at": "2026-05-19T14:23:00Z",
    "purchases": [
      {"slug": "new-fmcsa-carrier-leads-2026-05", "type": "one_time", "stripe_charge_id": "ch_...", "purchased_at": "..."}
    ],
    "subscriptions": [
      {"slug": "new-fmcsa-carrier-leads-2026-05", "stripe_subscription_id": "sub_...", "started_at": "...", "status": "active"}
    ],
    "emails_sent": {
      "welcome": "2026-05-19T14:25:00Z",
      "day3": null,
      "refresh_2026_Q3": null
    }
  }
  ```
- `state/subscription-refresh-log/<slug>-<YYYY-Qq>.json` — written by engineer (or founder running engineer manually) when fresh data is ready for delivery to subscribers. Schema:
  ```json
  {
    "slug": "new-fmcsa-carrier-leads-2026-05",
    "quarter": "2026-Q3",
    "refresh_at": "2026-08-17T...",
    "gist_url": "https://gist.github.com/.../refresh-Q3.csv",
    "notes": "Δ vs Q2: +812 carriers, -34 deauthorized"
  }
  ```
  customer-success agent reads this file; if present and customers haven't been notified, sends refresh email with this Gist URL.

## Email infrastructure

**SMTP:** Gmail. `smtp.gmail.com:587`, STARTTLS.

**Credentials (from `~/.profile`):**
- `GMAIL_APP_PASSWORD` (set)
- Sender: `oghenetejiri@gmail.com` (TJ's Gmail — the only authenticated mailbox we have)

**Headers:**
- `From: "DataStructured" <oghenetejiri@gmail.com>` — display name overrides personal address
- `Reply-To: info@oefrenterprise.com` — keeps replies in the business inbox
- `Subject:` per email type

**Email templates (inline in the agent's identity, no external template engine):**

1. **Welcome (one-time purchase):**
   - Subject: `Your DataStructured purchase — {product name}`
   - Body: thank-you + download link (re-served from launch-report's Gist URL) + reply-to-this-email line + signature

2. **Welcome (subscription):**
   - Subject: `Welcome to DataStructured — {product name} subscription`
   - Body: thank-you + first download link + "your next refresh arrives ~quarterly" + signature

3. **Day-3 check-in:**
   - Subject: `Quick check-in — anything broken with {product name}?`
   - Body: 3-line message asking if data was useful, what would make it better. No upsell.

4. **Subscription refresh:**
   - Subject: `Fresh data — {product name} ({quarter})`
   - Body: "Here's your Q{n} refresh. Download below. Δ since last quarter: {notes}." + new Gist URL + signature

## Stripe polling

Each `customer_sweep` cycle:

1. Read cursor from `state/stripe-poll-cursor.json` (default: 90 days ago for first run).
2. Use `stripe.Charge.list(created={"gte": cursor_ts}, limit=100, expand=["data.invoice", "data.payment_intent"])` to get charges since cursor.
3. Use `stripe.Subscription.list(created={"gte": cursor_ts}, limit=100, status="all")` for subscriptions.
4. For each charge/subscription:
   - Extract customer email (from `charge.billing_details.email` or `customer.email`)
   - Determine product slug from `line_items` → `price.product` → match against `state/products/*/launch-report.json` for `stripe_product_id` or `stripe_subscription_product_id`
   - Skip if can't determine slug (log warning)
5. Update/create `state/customers/<email-safe>.json` adding to `purchases[]` or `subscriptions[]` (idempotent by stripe_charge_id / stripe_subscription_id)
6. Send welcome email if `emails_sent.welcome` is null. Record sent timestamp.
7. Update cursor to `now()` at the end.

Day-3 check-in (separate scan, runs in same cycle):
- Iterate all `state/customers/*.json`
- For any customer with `first_purchase_at` between 72 and 96 hours ago and `emails_sent.day3 is null` → send check-in, record timestamp

Refresh notifications (separate scan, runs in same cycle):
- For each `state/subscription-refresh-log/*.json` (this quarter's files):
  - Read the slug + quarter + gist_url
  - Iterate `state/customers/*.json` for any active subscription matching slug
  - For each customer where `emails_sent.refresh_<YYYY_Qq>` is null → send refresh email, record timestamp

## Idempotency / safety

- Welcome email: only sends if `emails_sent.welcome is null`. Cursor advances regardless, so a re-run won't re-send.
- Day-3: keyed on `emails_sent.day3`. One-shot.
- Refresh: keyed on `emails_sent.refresh_<YYYY_Qq>`. One per quarter per customer.
- Cursor advances ONLY at end of cycle, after Stripe pull + writes succeed. If cycle crashes mid-way, next cycle re-pulls (Stripe API is idempotent for reads; customer file writes are idempotent by stripe_id).
- Email sender failures (SMTP error) DO NOT advance the per-customer email-sent flag → next cycle retries.

## Email-safe filename

`<email-safe>` = `email.replace("@", "_at_").replace("+", "_plus_")`. Avoids filesystem-unsafe chars and keeps grep-ability.

## What's out of scope for v1

- Support inbox triage (no inbox yet; Reply-To routes to business email — founder reads)
- Auto-cancel handling on subscription churn (just observed/logged for now)
- Engagement analytics (open/click tracking — needs Mailgun or similar; out of scope per bootstrap rule)
- HTML email templates (plain text is fine for transactional)
- Email rate limiting (Gmail's 500/day limit is more than enough for v1 volume)
- Multi-product subscriptions (only FMCSA has a subscription today)

## Tasks

1. Create `.trinity/employees/customer-success/identity.md` with role + workflow + templates
2. Add `[employees.customer-success]` block + `[scheduler.cycles.customer_sweep]` block to `trinity.toml`
3. Create `scripts/email_sender.py` — Gmail SMTP wrapper
4. Create `scripts/customer_sweep.py` — Stripe polling + email dispatch logic (the actual implementation; agent identity references this script to be invoked via Bash)
5. Restart daemon; verify scheduler shows 5 cycles
6. Smoke test: run `scripts/customer_sweep.py` once manually; verify no errors (likely no new customers since FMCSA launch; cursor still advances)
7. Commit

## Engineer agent identity update (small)

Append to engineer identity:

```markdown
## Subscription refresh delivery (Phase 2+)

When you generate a refreshed dataset for a subscription product (manually or via trigger):
1. Upload the new CSV to a new GitHub Gist.
2. Write `state/subscription-refresh-log/<slug>-<YYYY>-Q<n>.json` with the slug, quarter, refresh timestamp, gist URL, and short delta notes.
3. customer-success agent will pick this up within 2 hours and email all active subscribers.
```
