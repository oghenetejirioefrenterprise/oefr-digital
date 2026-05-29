# DataStructured Phase 3 — Distribution Sophistication

**Status:** Approved 2026-05-18 (delegated; gates explicitly overridden).
**PRD scope:** marketing-lead, partnerships-lead, cfo, seo-operator agents + multi-channel Telegram routing + affiliate tracking.

---

## Goal

Add four specialized agents and two infra capabilities that move DataStructured from "autonomous + can sell" (Phase 2) to "autonomous + actively driving distribution + financial visibility + organic discovery" (Phase 3).

## Hard rules (still in force, do not change)

- Public data only
- No PII
- Source URL on every row
- Production code only, no mocks
- Test before claiming done
- Folder-scoped to `~/apps/dataStructured/`
- No new paid SaaS — reuse existing subs (Anthropic, Gmail, Stripe, Vercel, Telegram bot)
- Browser-first for platform interactions (no platform-write APIs for posting)
- Never discount

---

## Six sub-projects

### 3.1 — `marketing-lead` agent

**Role:** Channel selection + richer content drafting per product. Sits above the existing `distribution-agent` execution layer (which posts via browser automation). Marketing-lead decides WHICH channels for WHICH product, and drafts the channel-specific content with audience research. Distribution-agent then executes the posting.

**Architecture:**
- New employee: `.trinity/employees/marketing-lead/identity.md`
- New scheduler cycle: `marketing_plan` at 11:00 ET daily (before research at 13:00, so the day's distribution planning happens at top of day)
- Output: writes channel-specific drafts to `state/marketing-plans/{date}.json` with structure:
  ```json
  {
    "version": 1,
    "generated_at": "...",
    "plans": [
      {
        "item_id": "<distribution-queue id>",
        "channel": "reddit|twitter|linkedin",
        "subreddit_or_handle": "r/trucking",
        "draft": {"title": "...", "body": "..."} | {"thread": [...]} | {"text": "..."},
        "rationale": "Why this channel for this product",
        "scheduled_for": "ISO-8601"
      }
    ]
  }
  ```
- Distribution-agent's existing 21:00 cycle reads from BOTH `state/distribution-queue.json` (legacy) AND `state/marketing-plans/{today}.json` (new). When marketing-plan exists for an item, use its draft; otherwise fall back to distribution-agent's own templating.

**MVP scope:** generates plans for top 3 unposted items × 1 channel each per day. Multi-channel-per-item is v2.

### 3.2 — `partnerships-lead` agent

**Role:** Affiliate recruitment via personalized outreach. Identifies people in target audiences with audience reach (newsletter writers, YouTube creators, podcast hosts) and proposes affiliate partnerships.

**Architecture:**
- New employee: `.trinity/employees/partnerships-lead/identity.md`
- New scheduler cycle: `partnerships_scan` weekly (Mondays at 10:00 ET)
- Output: writes affiliate-candidate briefs to `state/partnerships/candidates/{slug}.json`:
  ```json
  {
    "candidate": "newsletter or person name",
    "url": "their content URL",
    "audience_match_score": 1-10,
    "outreach_template": "personalized DM text",
    "status": "drafted | sent | reply_received | partnership_active | declined",
    "added_at": "..."
  }
  ```
- Affiliate pipeline tracking lives in `state/partnerships/active.json` — list of active partnerships with: candidate name, slug, commission rate (default 30%), UTM code, signup date, total referred revenue
- v1 outreach: agent drafts the outreach but founder approves/sends (no auto-DM to strangers — that violates platform norms and is high-risk)

**MVP scope:** weekly batch of 3-5 candidate briefs surfaced to founder via Telegram (using sub-project 5's marketing-reports channel). Founder decides which to send.

### 3.3 — `cfo` agent

**Role:** Daily financial digest. Pulls Stripe data, computes MRR / new revenue / refunds / anomalies. Proposes pricing experiments based on conversion patterns.

**Architecture:**
- New employee: `.trinity/employees/cfo/identity.md`
- New scheduler cycle: `cfo_digest` at 18:30 ET daily (before CEO pipeline at 19:00 — CEO consumes CFO's numbers in the daily DM)
- Output: writes daily digest to `state/cfo-digest/{date}.json`:
  ```json
  {
    "date": "2026-05-18",
    "mrr": 29,
    "active_subscriptions": 1,
    "one_time_revenue_today": 0,
    "one_time_revenue_30d": 0,
    "refunds_today": 0,
    "refunds_30d": 0,
    "anomalies": [],
    "pricing_experiments_proposed": []
  }
  ```
- Anomaly detection: simple thresholds for v1 (e.g., refund rate > 5%, MRR drop > 10%, subscription churn > 20%)
- CEO identity update: at 19:00, read `state/cfo-digest/{today}.json` and include the headline numbers in the daily DM

**MVP scope:** daily digest, anomaly flagging, single-product pricing-experiment proposals (no multi-product A/B testing yet).

### 3.4 — `seo-operator` agent

**Role:** SEO-optimized product descriptions + blog content for organic discovery. Builds long-tail content that ranks for buyer-intent searches.

**Architecture:**
- New employee: `.trinity/employees/seo-operator/identity.md`
- New scheduler cycle: `seo_publish` at 08:00 ET on Tuesdays + Fridays (low-cadence — quality over quantity)
- Output: writes blog posts to `state/blog/posts/{slug}.md` with frontmatter (title, description, keyword target, published date, related product slugs)
- Storefront update: add `/blog/` route + `/blog/{slug}/` route that reads from `state/blog/posts/`
- v1 content types: "How to use {dataset} for {use case}" + "{dataset} vs commercial alternatives" + "What's in the latest {dataset} refresh"
- Schema.org BlogPosting JSON-LD on each post (deferred — JSON-LD security-hook still blocks; basic meta tags only for v1)

**MVP scope:** agent writes 1 post per scheduled run (2 posts/week). Storefront renders the blog index + per-post pages.

### 3.5 — Multi-channel Telegram routing

**Role:** Route specialized agent output to topic-specific Telegram groups instead of all DMing the founder. Keeps the CEO's DM clean while delivering CFO numbers, compliance flags, marketing reports to dedicated chats.

**Architecture:**
- Add `[telegram.channels]` block to `trinity.toml`:
  ```toml
  [telegram.channels]
  founder_dm = 1366707521          # existing — CEO's daily DM (unchanged)
  compliance_flags = ""            # group ID for compliance NEEDS_FOUNDER_REVIEW + REVOCATION events
  financial_alerts = ""            # group ID for CFO anomalies + daily digest
  marketing_reports = ""           # group ID for marketing-lead plans + partnerships briefs
  ```
- Telegram group IDs are LEFT EMPTY in the commit; founder fills them after creating the groups manually (one-time setup; documented in CLAUDE.md)
- Helper: `scripts/telegram_dispatch.py` — takes (channel_name, message) and routes to the configured chat_id, falling back to founder_dm if the channel isn't configured yet (so we don't lose messages during the founder-setup gap)
- Agent identity updates (compliance-officer, cfo, marketing-lead, partnerships-lead) reference this helper

**MVP scope:** routing infra + helper + 3 named channels (compliance, financial, marketing). Founder creates the groups + populates IDs.

### 3.6 — Affiliate tracking (UTM + Stripe reconciliation)

**Role:** Track which partnerships drove which sales without paying for SaaS attribution tools.

**Architecture:**
- UTM codes are appended to Stripe Payment Links via query string: `?utm_source={partner_handle}&utm_medium=affiliate&utm_campaign={product_slug}`
- Stripe Checkout passes UTM params to `client_reference_id` if configured; for Payment Links we use the `Hosted Invoice URL` query-string forwarding (Stripe stores in `customer.metadata.utm_source` if metadata-collection is enabled on the Payment Link)
- For v1 simplicity: maintain a mapping in `state/partnerships/utm-links.json`:
  ```json
  {
    "version": 1,
    "links": [
      {
        "partner": "trucker_dad_newsletter",
        "product_slug": "new-fmcsa-carrier-leads-2026-05",
        "utm_code": "td_fmcsa_q2_2026",
        "stripe_payment_link": "https://buy.stripe.com/...?client_reference_id=td_fmcsa_q2_2026",
        "created_at": "...",
        "commission_pct": 30
      }
    ]
  }
  ```
- Reconciliation runs in `customer-success` agent's existing sweep: for each new charge, check if `client_reference_id` matches a UTM code; if so, log to `state/partnerships/sales-log.json` and accumulate to `state/partnerships/active.json` partner totals
- Payouts: founder reviews monthly `state/partnerships/active.json` and pays via existing payment method (manual for v1)

**MVP scope:** UTM-link generation helper + reconciliation in customer-success + sales log. Automatic payouts are explicitly deferred.

---

## Order of execution

Sub-projects within Phase 3 have minimal dependencies. Recommended order:

1. **3.5 (Telegram routing)** first — every other agent will use it. Build the infra, leave channel IDs empty.
2. **3.3 (cfo)** — easiest to validate (just reads Stripe; produces a JSON digest)
3. **3.1 (marketing-lead)** — depends on existing distribution-queue (already there)
4. **3.4 (seo-operator)** — independent
5. **3.6 (affiliate tracking)** — infra layer; integrates with customer-success
6. **3.2 (partnerships-lead)** — depends on 3.5 (Telegram routing to marketing channel) and 3.6 (UTM link gen)

Will execute in this dependency-aware order.

## Phase 3 success criteria (per PRD)

Tracking-only — gates are temporal and customer-dependent, so satisfying them is independent of build completion:

- ≥10 paying customers across all products
- ≥20% of new customers from non-paid channels (SEO, affiliate, word-of-mouth)
- ≥1 active affiliate driving sales
- CFO daily digest delivered for 60 consecutive days

These will validate organically over the next ~60 days; Phase 4 entry waits on them OR another explicit founder override.
