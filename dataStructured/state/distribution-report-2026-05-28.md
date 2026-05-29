# Distribution Cycle Report — 2026-05-28

## Summary

| Metric | Count |
|---|---|
| Shipped products in queue | 16 |
| (item, channel) pairs evaluated | 66 |
| Already posted (LinkedIn, historical) | 14 |
| **Unposted pairs identified** | **52** |
| Posts attempted this cycle | 3 (1 probe per channel) |
| **Posts succeeded** | **0** |
| Posts failed | 3 |
| Pairs intentionally **not** re-attempted | 49 |

**Outcome: BLOCKED.** All three distribution channels are non-functional from this
environment. This is a confirmed environmental/infrastructure blocker, not a content
or queue problem. It matches the two open BLOCKED board tasks (#16 Twitter, #17 Reddit).

---

## What ran this cycle

1. **Queue was missing** (`state/distribution-queue.json` did not exist — only its
   `.lock`). Reconstructed it from each product's authoritative `launch-report.json`
   (live Stripe/Gumroad URLs) + `spec.json` (name/price/audience), reusing the
   historical `item_id` from the distribution log so `already_posted()` dedup still
   matches prior entries. Script: `scripts/rebuild_distribution_queue.py`.
   Result: **16 shipped products** (1 skipped — `nonprofit-board-directors-executives`
   has no live Stripe link, i.e. not yet shipped).

2. **Computed the unposted matrix** against `state/distribution-log.json`:
   - Twitter: 16 unposted
   - Reddit: 34 unposted (across mapped niche subreddits + r/Entrepreneur)
   - LinkedIn: 2 unposted (`auto-dealership`, `epa-tri`)

3. **Attempted one representative post per channel** via `scripts/social_helpers.py`.
   All failed (see root cause). The remaining 49 pairs were **not** hammered —
   repeated browser-automation against IP-blocked platforms worsens bot-detection and
   risks the accounts, with zero chance of success until the blocker is fixed.

---

## Root cause (confirmed this cycle)

### Twitter & Reddit — `ANTHROPIC_API_KEY not set`
`social_helpers.py` drives both X and Reddit through **browser-use**, whose
`ChatAnthropic` agent requires `ANTHROPIC_API_KEY`. That key is **intentionally
unexported** — `~/.profile` states:

> "Do NOT export any ANTHROPIC_* tokens — Claude CLI uses ~/.claude/.credentials.json
> OAuth (Max subscription)."

So every X/Reddit attempt fails instantly on the key check. Fresh probes this cycle:
```
post-twitter → FAILED — ANTHROPIC_API_KEY not set — source ~/.profile first
post-reddit  → FAILED — ANTHROPIC_API_KEY not set — source ~/.profile first
```
The historical log corroborates this (28 direct "not set" failures, plus 96
"agent returned empty / no permalink" downstream failures).

### Twitter & Reddit — also IP-level bot detection
Even with a key, the datacenter IP is blocked: the log shows recurring
`ip-block`, Cloudflare `403`, and `networkidle-timeout` errors on x.com and reddit.com.
Two independent blockers stacked on these channels.

### LinkedIn — login page unreachable (IP/bot wall)
LinkedIn uses raw Playwright (no API key needed) and has succeeded historically.
This cycle both LinkedIn attempts failed at login:
```
FAILED — Page.wait_for_selector: Timeout 15000ms exceeded.
  waiting for locator("input[name='session_key']")
```
The login form never renders — consistent with an IP-level bot wall. No saved session
cookies exist (`state/browser_cookies/` is empty), so a fresh login is forced every run
and immediately blocked.

---

## Remediation (hand-off to Trinity / TJ — outside this agent's scope)

The queue and content pipeline are healthy. To unblock distribution, one of:

1. **Provide browser-use an LLM credential that is NOT the OAuth Max token.**
   - Option A: route `social_helpers.py` browser-use agents to `OPENAI_API_KEY`
     (already in `~/.profile`; a working `scripts/post_twitter_openai.py` exists as a
     reference) instead of `ChatAnthropic`.
   - Option B: supply a dedicated metered `ANTHROPIC_API_KEY` for automation only.
2. **Defeat IP-level bot detection** — run the browser leg through a residential
   proxy, or post from a non-datacenter host. Required for X *and* Reddit *and*
   (now) LinkedIn regardless of the LLM fix.
3. **Persist LinkedIn session cookies** once a human/residential login succeeds, so
   the raw-Playwright path stops hitting the login wall every run
   (`state/browser_cookies/linkedin.json`).

Until at least #1 + #2 land, all social channels remain blocked and further automated
attempts only generate failed log entries + bot-detection heat.

---

## Unposted pairs (full inventory, 52)

| Product | Unposted channels |
|---|---|
| auto-dealership-license-database-2026-05 | twitter, linkedin, reddit:r/Entrepreneur |
| ca-cslb-licensed-contractors-2026-05 | twitter, reddit:r/Entrepreneur, reddit:r/govcontracting |
| cms-medicare-home-health-agencies-2026-05 | twitter, reddit:r/Entrepreneur, reddit:r/HealthIT, reddit:r/homehealth |
| epa-tri-toxic-release-reporting-facilities-2026-05 | twitter, linkedin, reddit:r/Entrepreneur |
| faa-civil-aircraft-registration-2026-05 | twitter, reddit:r/Entrepreneur, reddit:r/aviation |
| fdic-bank-branch-directory-2026-05 | twitter, reddit:r/Entrepreneur |
| fl-alcoholic-beverage-licensees-2026-05 | twitter, reddit:r/Entrepreneur, reddit:r/bartenders, reddit:r/restaurateur |
| fl-real-estate-agent-licenses-2026-05 | twitter, reddit:r/Entrepreneur, reddit:r/RealEstate, reddit:r/realtors |
| new-business-formations-csv-2026-05 | twitter, reddit:r/Entrepreneur, reddit:r/smallbusiness |
| nppes-dentists-dental-practices-2026-05 | twitter, reddit:r/Dentistry, reddit:r/Entrepreneur |
| nppes-physical-therapist-clinics-2026-05 | twitter, reddit:r/Entrepreneur, reddit:r/physicaltherapy |
| samgov-small-biz-contractor-leads-2026-05 | twitter, reddit:r/Entrepreneur, reddit:r/govcontracting |
| sec-registered-investment-advisers-2026-05 | twitter, reddit:r/Entrepreneur, reddit:r/FinancialPlanning, reddit:r/personalfinance |
| ttb-brewery-winery-distillery-directory-2026-05 | twitter, reddit:r/Entrepreneur |
| tx-tdlr-electricians-2026-05 | twitter, reddit:r/Entrepreneur, reddit:r/electricians, reddit:r/govcontracting |
| tx-tdlr-hvac-contractors-2026-05 | twitter, reddit:r/Entrepreneur, reddit:r/HVAC, reddit:r/govcontracting |

(LinkedIn already posted for the other 14 products — historical successes retained.)

---

## Artifacts produced this cycle
- `state/distribution-queue.json` — **rebuilt** (16 items, schema-valid)
- `scripts/rebuild_distribution_queue.py` — queue reconstruction tool (new)
- `state/distribution-log.json` — +3 failed entries (1 linkedin, 1 twitter, 1 reddit probes)

**Generated:** 2026-05-28 (DataStructured distribution-agent)
