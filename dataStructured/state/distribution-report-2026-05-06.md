# Distribution Cycle — 2026-05-06

Run completed: 2026-05-07T02:08Z

## Posted

_None. All channels blocked — see Failures section._

## Skipped (already posted)

_None. This is the first distribution run for all 4 queue items._

## Failed

### New FMCSA Carriers — May 2026 — 15,770 Records

| Channel | Error |
|---|---|
| twitter | `networkidle-timeout` — x.com background polling prevents networkidle state |
| reddit:r/Truckers | `bot-detection` — old.reddit.com returning 403; login form unreachable |
| reddit:r/FreightBrokers | `bot-detection` — same root cause; attempt skipped after confirmed systemic failure |
| reddit:r/Entrepreneur | `bot-detection` — same root cause |

**Buy link:** https://buy.stripe.com/cNi14g4CP7aT8mT1iC7IY0c | **Price:** $39

---

### New Florida LLCs & Corps — May 2026 — 15,997 Records

| Channel | Error |
|---|---|
| twitter | `networkidle-timeout` — same root cause as above |
| reddit:r/smallbusiness | `bot-detection` — same root cause |
| reddit:r/Entrepreneur | `bot-detection` — same root cause |

**Buy link:** https://buy.stripe.com/aFaaEQc5h66Pbz5f9s7IY0f | **Price:** $49

---

### SAM.gov Small Biz Contractor Leads — DMV IT Corridor — 4,731 Records

| Channel | Error |
|---|---|
| twitter | `networkidle-timeout` — same root cause |
| reddit:r/govcontracting | `bot-detection` — same root cause |
| reddit:r/consulting | `bot-detection` — same root cause |
| reddit:r/Entrepreneur | `bot-detection` — same root cause |

**Buy link:** https://buy.stripe.com/dRm5kwb1dfHp7iPe5o7IY0g | **Price:** $49

---

### Florida Licensed Real Estate Agents & Brokers — 2026 — 448,610 Records

| Channel | Error |
|---|---|
| twitter | `networkidle-timeout` — same root cause |
| reddit:r/realtors | `bot-detection` — same root cause |
| reddit:r/RealEstate | `bot-detection` — same root cause |
| reddit:r/Entrepreneur | `bot-detection` — same root cause |

**Buy link:** https://buy.stripe.com/cNi8wIb1dfHpeLhe5o7IY0k | **Price:** $49

---

## Root Cause Analysis

Two distinct infrastructure failures blocked the entire run:

### 1. X/Twitter — `networkidle` timeout

- **Symptom:** `Page.goto("https://x.com/home", wait_until="networkidle")` times out after 30s on every attempt.
- **Root cause:** x.com continuously fires background polling requests. The page never reaches Playwright's `networkidle` state (no network activity for 500ms).
- **Affected function:** `_x_tweet()` in `scripts/social_helpers.py` line ~209.
- **Fix (for engineer):** Change `wait_until="networkidle"` → `wait_until="domcontentloaded"` in `_x_tweet()`. The `_x_is_logged_in()` function already uses `domcontentloaded` correctly — replicate that approach.

### 2. Reddit — 403 on old.reddit.com (IP-level block)

- **Symptom:** `curl https://old.reddit.com/login` returns HTTP 403. Playwright cannot find `#user_login` selector because the page never loads.
- **Root cause:** Reddit's CDN (Cloudflare/Fastly) is blocking the server's IP as a data center IP. old.reddit.com is known to block non-residential IPs.
- **Affected function:** `_reddit_login()` in `scripts/social_helpers.py` line ~90.
- **Fix options (for engineer):**
  1. Route Playwright traffic through a residential proxy (preferred — minimal code change).
  2. Switch from `old.reddit.com` to `www.reddit.com` (new Reddit UI) and update selectors.
  3. Use Reddit's official OAuth API instead of browser automation (eliminates bot-detection entirely; requires app registration at reddit.com/prefs/apps).

---

## Summary

| Metric | Value |
|---|---|
| Items in queue | 4 |
| Unique (item, channel) pairs attempted | 15 |
| Posts succeeded | 0 |
| Posts failed | 15 |
| Failure causes | 2 (networkidle-timeout on X, 403/bot-detection on Reddit) |
| All items posted | No |
| Queue items cleared | 0 (all remain `status: "ready"`) |

**Action required:** Engineer must fix `_x_tweet()` networkidle issue and Reddit IP-blocking before distribution can execute. All 4 queue items remain ready for the next successful run. No (item, channel) pair has `status: "posted"` — none are consumed.
