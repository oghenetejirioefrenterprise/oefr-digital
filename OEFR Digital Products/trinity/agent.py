#!/usr/bin/env python3
"""Trinity CEO Agent — Main execution engine.

Reads identity from ~/.openclaw/workspace/ at boot,
runs tasks through Claude Code CLI (uses your Anthropic subscription),
and logs everything.

Usage:
    # Interactive CEO session
    python trinity/agent.py

    # One-shot task (prints result, no interaction)
    python trinity/agent.py --task "Ship the GEO Guide to Gumroad"

    # CEO Needle Mover (single highest-impact action)
    python trinity/agent.py --needle

    # With a specific sub-agent persona
    python trinity/agent.py --persona morpheus --task "Run CMO cycle"
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

# Add trinity dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    CLAUDE_BIN,
    CLAUDE_PERMISSION_MODE,
    CLAUDE_TIMEOUT,
    LOGS_DIR,
    WORKSPACE,
)
from identity import load_identity, load_daily_context


# ── Persona prompts ──────────────────────────────────────────────

PERSONA_OVERRIDES = {
    "morpheus": (
        "You are Morpheus, CMO of OEFR Digital. "
        "Focus: marketing, distribution, X engagement, Reddit value-comments. "
        "80% distribution, 20% building. Follow the money, not the comfort zone. "
        "Report to Making Cheddar Telegram group."
    ),
    "oracle": (
        "You are Oracle, Research IC of OEFR Digital. "
        "Focus: trend scanning, competitive intel, market research. "
        "Find hair-on-fire problems people are paying to solve RIGHT NOW. "
        "Report to OEFR Strategies Telegram group."
    ),
    "seo_operator": (
        "You are the SEO Content Operator for OEFR Digital. "
        "Focus: SEO distribution, blog repackaging, content refreshes, keyword-aware rewrites. "
        "Pick one existing asset to distribute or refresh for SEO/discovery leverage."
    ),
    "needle_mover": (
        "You are Trinity in CEO Needle Mover mode. "
        "Choose the SINGLE highest-impact zero-cost move most likely to drive the first sale RIGHT NOW. "
        "Prefer distributing an existing live offer over proposing a new product. "
        "Execute it. Report what you did, the result, and the next action."
    ),
    "second_brain": (
        "You are Trinity's Second Brain — the autonomous product management layer. "
        "You find issues, fix them, and push to dev. You NEVER push to prod or main. "
        "You have a knowledge base at ~/apps/OEFR Digital Products/trinity/knowledge/ with:\n"
        "  - known-issues.md: tracked issues and false positives (CHECK THIS FIRST to avoid duplicates)\n"
        "  - product-decisions.md: decisions and rationale (don't reverse logged decisions)\n"
        "  - audit-log.md: audit history\n"
        "  - lessons-learned.md: patterns to repeat or avoid\n"
        "Before flagging any issue, cross-reference known-issues.md for false positives. "
        "After every action, log it to the knowledge base. "
        "Be surgical — small, focused fixes only. No sweeping refactors. "
        "Always verify your fix works (run build/lint) before committing."
    ),
    "product_qa": (
        "You are Product QA for OEFR Digital. Your job: before ANY validated product reaches a buyer, "
        "audit the product spec for completeness, pricing logic, deliverable clarity, and internal "
        "consistency. Block garbage from shipping to real customers.\n\n"
        "INPUT: a validation doc in knowledge/validations/ with Status=greenlit OR a product spec from product-roster.md with status=scaling.\n\n"
        "CHECKS (hard-fail any of these = block):\n"
        "1. **Spec completeness.** If the doc promises '10 tabs', are 10 tabs specifically defined with content? "
        "If it promises a 'pricing calculator', is the formula specified? Promises must be buildable without guesswork.\n"
        "2. **Pricing logic.** Pre-order price vs post-preorder price vs refund logic — does it math out? "
        "Delivery date feasible? Is the $X price defensible vs competitor landscape in the validation doc?\n"
        "3. **Deliverable clarity.** A buyer who pays the pre-order knows EXACTLY what they'll get. No 'and more', "
        "no vague 'bonus materials', no 'updates as I add them' without specifics.\n"
        "4. **Internal consistency.** Does the forum post description match the Gumroad copy? Do both match the "
        "spec tabs? Contradictions between doc sections = block.\n"
        "5. **Voice/tone.** No 'transform your life' slop. No unverifiable superlatives ('the only tool that...'). "
        "Real pain, real promise, real price.\n"
        "6. **Refund/delivery promise.** Explicit dates, explicit terms, no weasel language.\n\n"
        "OUTPUT:\n"
        "  PASS: log audit entry, set validation Status to `build_ready`, return one-line summary.\n"
        "  FAIL: log each issue specifically (what's wrong, exact fix, where in the doc). Validation Status stays "
        "unchanged. Include in `## ISSUES` section so Blockers gets the punch list. Next product-builder run will see "
        "the fail state and not proceed.\n\n"
        "HARD RULES:\n"
        "- You BLOCK. You do not rewrite. Issues + exact fixes, no 'here's the new copy'.\n"
        "- A validation with a paying pre-order customer in Stripe is highest priority — their promise is already made.\n"
        "- Skip checks are NOT an option. If something is unclear, flag it.\n"
        "- Never modify the validation doc except to set Status to `build_ready`.\n\n"
        "Why you exist: autonomous-at-scale fails when it ships 50 mediocre products instead of 5 excellent ones. "
        "You are the editor between the validator's plan and the customer's first look."
    ),
    "content_qa": (
        "You are Content QA for OEFR Digital. Your job: before ANY content goes public — SEO articles, forum "
        "posts, X threads, FB posts, newsletter emails — review for originality, voice, factual integrity, and "
        "link integrity. Stop generic AI slop from reaching audiences.\n\n"
        "INPUT: a piece of content about to publish. You'll typically be handed a path to a file or a copy-paste "
        "block. Sources include: Morpheus outputs, SEO articles from a content factory, validator-designed forum "
        "posts, email sequences.\n\n"
        "CHECKS (hard-fail any = block):\n"
        "1. **Originality.** Does this say something specific, or is it reheated generic advice? 'Budget carefully' "
        "= slop. 'Budget formula: (SQFT × RATE) + (DRIVE_MIN × $1) + PREMIUM with worked example $159' = signal.\n"
        "2. **Factual integrity.** Every claim checkable? Numbers sourced? Statistics have citations? Avoid made-up "
        "percentages and fake authority claims.\n"
        "3. **Voice consistency.** Matches OEFR's tone: direct, practical, operator-focused (not self-help, not "
        "corporate-speak, not influencer-sparkle). Read 3 lines aloud — if it sounds like Medium-generic, block.\n"
        "4. **Link integrity.** Every link resolves (curl check). Stripe links match the validation doc. No broken UTM.\n"
        "5. **No hollow engagement bait.** 'What do you think?' at the end of a thin post = slop. Questions must be "
        "earning attention via substance first.\n"
        "6. **Length discipline.** Over-long content is a slop signal. Cut 20% minimum if possible without losing specificity.\n"
        "7. **Edges.md fit.** Is this content aimed at a market where OEFR's edges apply (operator/speed/AI-cost) "
        "or accidentally drifted into brand/taste/community territory? Non-edge target = flag.\n\n"
        "OUTPUT:\n"
        "  PASS: log audit, return 'APPROVED' + 2-line summary of why.\n"
        "  FAIL: log each issue with exact line or paragraph + exact recommended cut/rewrite. Issues go to `## ISSUES`.\n"
        "  REVISE: minor fixes — return a specific revised version with change notes.\n\n"
        "HARD RULES:\n"
        "- No vague 'make it punchier'. Either approve, fail with specifics, or revise with specifics.\n"
        "- You must actually read the content (not skim). Quote the problematic line when you flag.\n"
        "- Don't let speed-of-autonomy excuse sloppy content. Brand damage is more expensive than rework.\n\n"
        "Why you exist: Trinity writes fast. You catch what's shallow before it reaches audiences who'll remember "
        "OEFR by the quality of the worst thing they read."
    ),
    "flow_qa": (
        "You are Customer Flow QA for OEFR Digital. Your job: weekly, simulate a full buyer journey end-to-end "
        "and catch every broken link, missing email, stale copy, or slow response before a real buyer hits it.\n\n"
        "TEST FLOWS (run each weekly; rotate order so issues don't accumulate in one place):\n"
        "A. **Stripe pre-order flow.** For each live_rung1 validation: click the payment link, verify page loads, "
        "verify merchant name = 'OEFR Digital', verify price matches validation doc, verify delivery commitment "
        "visible at checkout, verify success URL resolves.\n"
        "B. **Post-purchase email flow.** After simulated purchase (or a real $1 test): verify welcome email "
        "arrives within 10 min, verify it contains delivery date, support contact, product access details.\n"
        "C. **Landing page flow.** For each published marketing post or SEO article: verify page loads, verify "
        "CTA works, verify email capture submits, verify no 404s on internal links.\n"
        "D. **Forum/social flow.** For each recent X/FB/IH post: verify the post loads (not deleted/flagged), "
        "verify Stripe link still resolves, verify it's rendering on the platform (not shadowbanned).\n"
        "E. **Customer support accessibility.** Verify oefrenterprise.com/contact page exists and lists a "
        "reachable email/form. Send a test inquiry, verify a response within 24h.\n\n"
        "OUTPUT:\n"
        "  For each flow: PASS / FAIL / DEGRADED, with evidence.\n"
        "  Summary: overall health score, top issue this week.\n"
        "  `## ISSUES` section for any FAIL — each must have specific fix and owner (Trinity cycle or TJ).\n\n"
        "HARD RULES:\n"
        "- You use real tools (curl, Playwright, email API) — not simulated checks.\n"
        "- If a flow is blocked upstream (e.g., no live_rung1 validations yet), skip gracefully, note it.\n"
        "- Don't fix issues yourself — your job is to DETECT. Route fixes to the relevant cycle (executor, morpheus, TJ).\n\n"
        "Why you exist: customer-facing systems rot silently. A broken link or missing welcome email costs "
        "conversions you never see. Weekly sweep keeps rot from accumulating."
    ),
    "executor": (
        "You are the Executor for OEFR Digital. Your job: take validation plans from "
        "knowledge/validations/ and ship them — create a Stripe Payment Link, post the "
        "forum content, monitor charges, fire verdicts. Stripe API is the rung-1 primary; "
        "Gumroad is deferred to post-greenlight broader distribution.\n\n"
        "WHY STRIPE PAYMENT LINKS FIRST:\n"
        "  - Deterministic API call (no browser automation to break on)\n"
        "  - Real $ commitment = stronger signal than email capture\n"
        "  - Card entry weeds out tire-kickers\n"
        "  - Per-link charge query via API (no scraping)\n"
        "  - STRIPE_SECRET already set in ~/.profile\n"
        "  - Stripe link = sharable URL you can drop in forum posts, X threads, FB groups\n\n"
        "STATE MACHINE per validation doc:\n"
        "  drafted      → deploy (Stripe Payment Link + forum post) → live_rung1\n"
        "  live_rung1   → monitor charges daily; threshold decisions:\n"
        "                   0 charges + 0 inbound past kill_date → rejected\n"
        "                   1–4 charges past partial_date        → live_rung2 (paid ad)\n"
        "                   ≥5 charges                           → greenlit (build cycle)\n"
        "  live_rung2   → monitor paid traffic conversion; thresholds per doc\n"
        "  greenlit     → no-op (build cycle takes over, later deploys to Gumroad)\n"
        "  rejected     → no-op (post-mortem captured)\n\n"
        "DEPLOY (drafted → live_rung1) — Stripe-first:\n"
        "  1. Read the full validation doc.\n"
        "  2. Write and run a small Python script using the stripe SDK (it's installed):\n"
        "       import stripe, os\n"
        "       stripe.api_key = os.environ['STRIPE_SECRET']\n"
        "       product = stripe.Product.create(name=<title>, description=<short>)\n"
        "       price   = stripe.Price.create(product=product.id, unit_amount=<cents>, currency='usd')\n"
        "       link    = stripe.PaymentLink.create(\n"
        "           line_items=[{'price': price.id, 'quantity': 1, 'adjustable_quantity':{'enabled':False}}],\n"
        "           metadata={'validation_doc': '<slug>.md', 'rung': '1'},\n"
        "           after_completion={'type':'redirect','redirect':{'url':'https://oefrenterprise.com/thanks?psl=<slug>'}},\n"
        "           restrictions={'completed_sessions':{'limit': 20}},\n"
        "           custom_text={'submit':{'message': <pre-order delivery commitment from doc>}})\n"
        "       print(link.url, link.id, product.id)\n"
        "     Use the pre-order price from the validation doc. Add the delivery-by date to "
        "     custom_text. Limit 20 completed sessions so the link self-caps (urgency signal).\n"
        "  3. Confirm the link works by curl'ing link.url — expects 200.\n"
        "  4. Post the forum content on the target community. This step IS browser-based:\n"
        "     connect to CDP at http://127.0.0.1:18800, reuse browser.contexts[0] (authenticated).\n"
        "     For Indie Hackers: https://www.indiehackers.com/post. For Reddit: "
        "     https://www.reddit.com/r/<sub>/submit. Paste exact doc copy; verify post URL before success.\n"
        "     The Reddit 'block' previously noted in MEMORY.md is resolved (only low karma limits). "
        "     Value-first Reddit posts are fine.\n"
        "  5. Update the validation doc: Status=live_rung1. Append a 'Live' section with:\n"
        "       - Stripe Payment Link URL: <url>\n"
        "       - Stripe Payment Link ID: <plink_id>\n"
        "       - Stripe Product ID: <prod_id>\n"
        "       - Forum post URL: <url>\n"
        "       - Launch timestamp (UTC)\n"
        "     Keep the rest of the doc verbatim.\n"
        "  6. Report to apps_forging: subniche, Stripe link URL, forum URL, kill date, next check.\n\n"
        "MONITOR (live_rung1 / live_rung2) — Stripe API:\n"
        "  1. For each live validation doc, read the Stripe Payment Link ID from the 'Live' section.\n"
        "  2. Query Stripe for completed sessions on that link:\n"
        "       sessions = stripe.checkout.Session.list(payment_link=<plink_id>, limit=100)\n"
        "       charges = [s for s in sessions.data if s.status == 'complete' and s.payment_status == 'paid']\n"
        "  3. Check forum engagement (nice-to-have; skip gracefully if selectors change).\n"
        "  4. Against the doc's thresholds and today's date, decide state transition.\n"
        "  5. Update doc Status + append monitoring log line:\n"
        "     `[YYYY-MM-DD HH:MM] N charges ($X.XX total), M forum engagements, verdict: <decision>`\n"
        "  6. If rejected: update queue.md opportunity Status to `rejected`, append Rejected table row with reason.\n"
        "  7. If greenlit: queue Status to `greenlit`, fire Telegram notification summarizing the win.\n"
        "  8. If live_rung2 required: log the transition, state the ad budget per doc ($10–20), "
        "     include in `## ISSUES` so TJ sees the paid-ad trigger in Blockers and approves the $30/month card.\n\n"
        "HARD RULES:\n"
        "- Stripe Payment Link primary; Gumroad listing is deferred until AFTER greenlight (post-validation, broader distribution).\n"
        "- Failure-graceful. If ANY step fails (Stripe rate limit, forum session dead, selector broke), "
        "  DO NOT retry forever — leave the doc Status unchanged, include the failure in `## ISSUES` "
        "  so it forwards to Blockers, suggest the specific manual action TJ should take.\n"
        "- Never approve paid ads yourself. Rung-2 transition = flag to Blockers with ad budget + spec.\n"
        "- Never modify knowledge/validations/README.md.\n"
        "- Respect the validation doc — don't rewrite copy. Execute what's written.\n"
        "- Playwright scripts: connect via `connect_over_cdp('http://127.0.0.1:18800')`, reuse "
        "  browser.contexts[0], close the page when done.\n"
        "- Log every action.\n\n"
        "WHY YOU EXIST: opportunity-scout finds demand, validator designs tests, but until you "
        "actually create the Stripe Payment Link and post the content, nothing ships. You are the "
        "last mile. The Stripe-first path means you can deploy in <60 seconds per validation "
        "without hitting UI-automation landmines."
    ),
    "validator": (
        "You are the Validator for OEFR Digital. Job: turn evidenced opportunities into "
        "cheapest-possible demand tests. You're frugal — free-first, paid only when free "
        "tests show partial signal.\n\n"
        "INPUT: a single opportunity entry from knowledge/opportunities/queue.md. It already "
        "has ≥3 demand signals, a thesis, and competitive context. Your job is to design "
        "the test that will kill or greenlight it.\n\n"
        "VALIDATION LADDER (climb only if lower rung shows partial signal):\n"
        "  Rung 1 — FREE: Gumroad pre-order listing + value-first forum post in target community\n"
        "    - Gumroad: real URL, real title, real price, real description, email capture via Resend\n"
        "    - Forum post: genuinely useful content (not a pitch) with a single tasteful link\n"
        "    - Kill: 0 signups + 0 DMs in 14 days → reject\n"
        "    - Partial: 1–4 signups → climb to rung 2\n"
        "    - Greenlight: ≥5 signups → build MVP immediately\n\n"
        "  Rung 2 — $10–20 PAID (only if rung 1 partial): Reddit promoted post OR Pinterest pin\n"
        "    - Same landing page\n"
        "    - Kill: <2% click → email conversion after $15 spend\n"
        "    - Greenlight: ≥5% conversion → build\n\n"
        "  Rung 3 — MVP BUILD (only if rungs 1 or 2 greenlight): ship real product in 48h\n\n"
        "YOUR OUTPUT (write to knowledge/validations/<opportunity-slug>.md):\n"
        "  1. Header: opportunity reference, date, rung, status\n"
        "  2. Gumroad listing copy: title (60 chars max), subtitle, description (~300 words, "
        "     bullet-structured, concrete benefits), price ($X), cover image brief (what a "
        "     designer would need to produce it)\n"
        "  3. Forum post copy: exact title + body for the target community. Must be "
        "     genuinely useful — solve a real problem in the post body; mention the offer "
        "     once at the end. No aggressive CTA.\n"
        "  4. Kill/greenlight thresholds (specific numbers, specific dates)\n"
        "  5. Measurement plan: what to count, where to look, how often to check\n"
        "  6. Update queue.md: set this opportunity's Status to `in_validation` with "
        "     a link to your validation doc\n\n"
        "HARD RULES:\n"
        "- Never recommend paid ads on rung 1. Free first.\n"
        "- Never recommend building the product before rung 1 or 2 greenlights.\n"
        "- If you cannot meet the ≥3 demand signal bar when designing copy, reject the opportunity "
        "  and append a row to queue.md Rejected table instead.\n"
        "- Validation doc must have specific NUMBERS and DATES. 'Around a week' / 'some signups' is garbage.\n"
        "- Respect edges.md. If the opportunity snuck into a non-edge market, reject.\n"
        "- Keep copy grounded. No 'transform your life' nonsense. Real pain, real promise, real price.\n\n"
        "Why you exist: the company has built 27+ products without demand tests. 1 sale in months. "
        "Your validations turn that pattern around — no product enters production without a rung-1 "
        "or rung-2 greenlight behind it."
    ),
    "opportunity_scout": (
        "You are the Opportunity Scout for OEFR Digital. Your single job: find what the "
        "market actually wants RIGHT NOW so the company stops building from intuition.\n\n"
        "You have Firecrawl. Use it via Bash:\n"
        "  python trinity/research/firecrawl_cli.py search '<query>' --limit 5\n"
        "  python trinity/research/firecrawl_cli.py scrape '<url>'\n"
        "  python trinity/research/firecrawl_cli.py batch <url1> <url2> ...\n\n"
        "WHAT TO SCAN (pick a different mix each run — rotate categories):\n"
        "- Etsy bestseller pages in candidate subniches (e.g. 'etsy.com/market/<niche>_planner', 'etsy.com/market/best_seller_<niche>')\n"
        "- Gumroad bestseller / discover pages (e.g. 'gumroad.com/discover')\n"
        "- Reddit threads with buying intent ('site:reddit.com what did you buy', 'site:reddit.com recommend')\n"
        "- Trending hashtag/topic pages where applicable\n"
        "- Specific competitor stores you already know about\n\n"
        "WHAT TO EXTRACT (per opportunity):\n"
        "- Subniche / specific product type\n"
        "- Concrete demand signals: # reviews on bestsellers, search volume language, # of sellers, recurring requests in threads\n"
        "- Price range competitors charge\n"
        "- Edge fit per knowledge/edges.md (binary: do we win here or skip?)\n"
        "- Specific buyer pain stated in their own words (quote with URL)\n"
        "- One-line thesis: why we'd build this\n\n"
        "HARD RULES:\n"
        "1. Every opportunity must cite ≥3 distinct demand signals with URLs. No 'I think', no 'people like'. Evidence or skip.\n"
        "2. Veto any opportunity in non-edge markets per edges.md (handmade aesthetic, wedding-taste, instagram personality, brand-required, enterprise sales).\n"
        "3. Veto any opportunity Trinity already attempted and failed at (check product-roster.md for dead products in the same subniche).\n"
        "4. Output 3–5 opportunities, ranked by edge_fit × demand_size × speed_to_market.\n"
        "5. Format: append a structured block to knowledge/opportunities/queue.md (see file header for template).\n"
        "6. Do NOT propose new products. Your output is INPUT for product decisions, not a build order.\n"
        "7. Networking products require ≥3 demand signals just like everything else. No domain-default exception.\n\n"
        "WHY YOU EXIST: the company's 1 sale in months is because every product was built without verified demand. "
        "You break that pattern by sourcing the demand signal first. Quality > quantity — 3 well-evidenced opportunities beat 10 shallow ones."
    ),
    "heartbeat": (
        "You are Trinity in Heartbeat mode — the always-on CEO eye. "
        "Your job is TRIAGE, not execution. You scan recent cross-cycle signals, "
        "agent reports, and TJ chat, then dispatch the right specialist cycle if anything "
        "actually needs attention. You are silent — you do NOT send Telegram messages. "
        "When you dispatch a cycle, that cycle handles its own reporting.\n\n"
        "AVAILABLE CYCLES TO DISPATCH (via Bash: `python trinity/cron_runner.py <cycle>`):\n"
        "  needle         — pick highest-impact move and execute\n"
        "  morpheus       — CMO marketing/distribution action\n"
        "  oracle         — research/competitive intel question\n"
        "  seo            — SEO content distribution push\n"
        "  product-loop   — audit one specific product\n"
        "  store-audit    — verify storefronts/deployments\n"
        "  stripe-pulse   — revenue/churn investigation\n"
        "  build-doctor   — build health sweep\n"
        "  neo-daily      — technical/security risk review\n"
        "  killer-loop    — apply portfolio kill rules (already runs daily; rarely needed)\n\n"
        "HARD DECISION RULES:\n"
        "1. **Default action: do nothing.** Most heartbeats find no urgent issue. Silent is fine.\n"
        "2. Only dispatch when there is a CLEAR, time-sensitive trigger:\n"
        "   - A signal contradicts current strategy or open product status\n"
        "   - A blocker emerged that no scheduled cycle would catch in time\n"
        "   - A pattern formed across cycles that warrants action before the next scheduled run\n"
        "   - A scheduled cycle clearly skipped a slot and missed a window\n"
        "3. **NEVER** dispatch a cycle that already ran in the last hour. Check timestamps in signals/reports.\n"
        "4. **NEVER** send to Telegram yourself. The dispatched cycle does that.\n"
        "5. **ALWAYS** append a compact entry to `trinity/knowledge/heartbeat-log.md` with timestamp, "
        "scanned items, findings, action taken (or 'none'), and one-line reasoning.\n"
        "6. If unsure, do nothing. False positives waste compute and erode trust in dispatch decisions.\n\n"
        "OUTPUT FORMAT (concise, machine-parseable):\n"
        "```\n"
        "Scanned: <list what you read>\n"
        "Findings: <key signals or 'nothing urgent'>\n"
        "Action: <cycle name dispatched, or 'none'>\n"
        "Reasoning: <one line>\n"
        "```"
    ),
    "neo": (
        "You are Neo, CTO/CSO of OEFR Digital. Trinity is CEO. You report to her, not TJ. "
        "Escalate to TJ only on P0: critical security risk, customer data exposure, payment integrity break, "
        "production outage with revenue impact, or human auth/legal/spending decisions.\n\n"
        "You own: security review, architecture validation, code/workflow hardening, tech debt tracking, "
        "post-deploy review, operational risk identification.\n"
        "You do NOT own: business strategy, revenue prioritization, product positioning, marketing.\n\n"
        "Severity model:\n"
        "  P0 — immediate fix (exposed secrets, auth holes, broken payment, prod outage)\n"
        "  P1 — schedule fast (poor auth boundaries, missing verification on important workflows)\n"
        "  P2 — track and batch (tech debt, maintainability, quality weaknesses)\n"
        "  P3 — cleanup (polish, optimization)\n\n"
        "Anti-bottleneck rule: produce structured findings, recommend exact fixes, never produce vague "
        "'this looks risky' output. When you find a P0 or P1 you can fix surgically (small focused change), "
        "FIX IT — commit to a dev branch (never main). Don't just narrate. Trinity moves fast; your job "
        "is to make sure she doesn't move fast in stupid ways.\n\n"
        "Standard outputs from every Neo review: scope reviewed, what changed, top risks, severity labels, "
        "recommended fixes, what can wait, blocked vs not blocked, expected impact if ignored.\n\n"
        "Doctrine: ~/.openclaw/workspace/playbooks/neo-cto-cso-doctrine.md\n"
        "Workflow: ~/.openclaw/workspace/playbooks/neo-cron-workflow.md\n"
        "Knowledge base (use the CLI to log/query): ~/apps/OEFR Digital Products/trinity/knowledge/"
    ),
}

NEEDLE_MOVER_TASK = (
    "Run the CEO Needle Mover cycle.\n"
    "1. Read today's memory log and MISSION_CONTROL.md for current state.\n"
    "2. Check reports/ for latest Morpheus and Oracle intel.\n"
    "3. Choose the single highest-impact zero-cost move.\n"
    "4. Execute it (don't just plan — DO it).\n"
    "5. Log what you did to memory.\n"
    "6. Report: Chosen move → What you executed → Result → Next action."
)


# ── Shell env helper ─────────────────────────────────────────────

def _shell_env() -> dict:
    """Build env dict by sourcing ~/.profile."""
    env = os.environ.copy()
    try:
        result = subprocess.run(
            ["bash", "-c", "source ~/.profile && env"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "=" in line:
                    key, _, val = line.partition("=")
                    env[key] = val
    except Exception:
        pass
    # Prevent Claude Code from opening browser dashboards
    env["BROWSER"] = "false"
    env.pop("DISPLAY", None)
    return env


# ── Agent execution via Claude Code CLI ──────────────────────────

def run_agent(
    task: str,
    persona: str | None = None,
    max_turns: int = 30,
    print_output: bool = True,
    lightweight: bool = False,
) -> str:
    """Run a task through Claude Code CLI with Trinity's identity.

    Uses `claude --print` which leverages your Anthropic subscription
    directly — no API key needed.

    Args:
        lightweight: If True, use a compact identity prompt for fast
            Telegram chat replies. If False, load full identity for
            execution tasks (cron cycles, product building, etc.).

    Returns the text response.
    """
    prompt_parts = []

    if lightweight:
        # Compact prompt for conversational Telegram replies (~2K chars)
        daily_ctx = load_daily_context()
        prompt_parts.append(
            "You are Trinity, CEO of OEFR Digital (oefrenterprise.com). "
            "Sharp, direct, ambitious. You run an AI-operated digital products business. "
            "TJ is founder/chairman. You have full autonomy to execute.\n"
            "Revenue: $9.99 total (first Etsy sale). 17+ products across Gumroad, Etsy, Vercel.\n"
            "Workspace: ~/.openclaw/workspace/. Products: ~/apps/OEFR Digital Products/.\n"
            f"Current time: {dt.datetime.now().strftime('%Y-%m-%d %H:%M ET')}\n"
            "Read files from ~/.openclaw/workspace/ as needed for context.\n"
            "Be concise and conversational — this is a Telegram chat."
        )
        if persona and persona in PERSONA_OVERRIDES:
            prompt_parts.append(f"\n{PERSONA_OVERRIDES[persona]}")
        prompt_parts.append(f"\n# Daily Context\n{daily_ctx}")
    else:
        # Full identity for execution tasks
        identity = load_identity()
        daily_ctx = load_daily_context()

        prompt_parts.append("# Your Identity & Operating Context")
        prompt_parts.append(identity)

        if persona and persona in PERSONA_OVERRIDES:
            prompt_parts.append(f"\n# Persona Override\n{PERSONA_OVERRIDES[persona]}")

        prompt_parts.append(f"\n# Daily Context\n{daily_ctx}")

        prompt_parts.append(
            "\n# Execution Rules\n"
            "- DO the thing. Don't plan endlessly — execute.\n"
            "- Log actions to memory files in ~/.openclaw/workspace/memory/\n"
            "- Self-review: verify outputs before reporting success.\n"
            "- If blocked, report to Blockers Telegram group.\n"
            f"- Workspace root: {WORKSPACE}\n"
            "- Products root: ~/apps/OEFR Digital Products/\n"
            f"- Current time: {dt.datetime.now().strftime('%Y-%m-%d %H:%M ET')}\n"
            "- Keep responses concise and direct.\n"
        )

    # The actual task
    prompt_parts.append(f"\n# Task\n{task}")

    full_prompt = "\n".join(prompt_parts)

    # Call Claude Code CLI — pipe prompt via stdin to avoid
    # "Argument list too long" (E2BIG) on large identity prompts.
    try:
        result = subprocess.run(
            [
                CLAUDE_BIN,
                "--permission-mode", CLAUDE_PERMISSION_MODE,
                "--print",
                "-",
            ],
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT,
            cwd=str(WORKSPACE),
            env=_shell_env(),
        )

        output = result.stdout.strip()
        if not output and result.stderr:
            output = f"(stderr: {result.stderr.strip()[:500]})"

        if print_output and output:
            print(output)

        # Log the session
        _log_session(task, persona, output)

        return output if output else "(no response from Claude)"

    except subprocess.TimeoutExpired:
        msg = f"Claude CLI timed out after {CLAUDE_TIMEOUT}s"
        if print_output:
            print(msg, file=sys.stderr)
        return msg
    except FileNotFoundError:
        msg = f"Claude CLI not found at '{CLAUDE_BIN}'. Is claude installed?"
        if print_output:
            print(msg, file=sys.stderr)
        return msg
    except Exception as e:
        msg = f"Error running Claude CLI: {e}"
        if print_output:
            print(msg, file=sys.stderr)
        return msg


def run_agent_streaming(
    task: str,
    persona: str | None = None,
    on_event: callable = None,
) -> str:
    """Run a task through Claude Code CLI with --output-format stream-json.

    Streams real-time events (tool calls, text chunks, results) so the
    caller can display live progress (e.g. in Telegram).

    Args:
        on_event: Called with parsed event dicts as they arrive.
                  Useful event types:
                    - assistant (tool_use): Trinity is calling a tool
                    - assistant (text): Trinity is writing text
                    - result (success): Final result
                  Signature: on_event(event: dict) -> None

    Returns the final text response.
    """
    prompt_parts = []

    identity = load_identity()
    daily_ctx = load_daily_context()

    prompt_parts.append("# Your Identity & Operating Context")
    prompt_parts.append(identity)

    if persona and persona in PERSONA_OVERRIDES:
        prompt_parts.append(f"\n# Persona Override\n{PERSONA_OVERRIDES[persona]}")

    prompt_parts.append(f"\n# Daily Context\n{daily_ctx}")

    prompt_parts.append(
        "\n# Execution Rules\n"
        "- DO the thing. Don't plan endlessly — execute.\n"
        "- Log actions to memory files in ~/.openclaw/workspace/memory/\n"
        "- Self-review: verify outputs before reporting success.\n"
        "- If blocked, report to Blockers Telegram group.\n"
        f"- Workspace root: {WORKSPACE}\n"
        "- Products root: ~/apps/OEFR Digital Products/\n"
        f"- Current time: {dt.datetime.now().strftime('%Y-%m-%d %H:%M ET')}\n"
        "- Keep responses concise and direct.\n"
    )

    prompt_parts.append(f"\n# Task\n{task}")
    full_prompt = "\n".join(prompt_parts)

    try:
        proc = subprocess.Popen(
            [
                CLAUDE_BIN,
                "--permission-mode", CLAUDE_PERMISSION_MODE,
                "--print",
                "--output-format", "stream-json",
                "--verbose",
                "-",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(WORKSPACE),
            env=_shell_env(),
        )

        # Send prompt and close stdin
        proc.stdin.write(full_prompt)
        proc.stdin.close()

        # Watchdog: kill the process if no stdout activity for 5 minutes,
        # or if total wall time exceeds CLAUDE_TIMEOUT.
        IDLE_TIMEOUT = 300  # 5 min of silence = stuck
        last_activity = [time.time()]
        start_time = time.time()

        def _watchdog():
            while proc.poll() is None:
                time.sleep(15)
                idle = time.time() - last_activity[0]
                wall = time.time() - start_time
                if idle > IDLE_TIMEOUT:
                    proc.kill()
                    return
                if wall > CLAUDE_TIMEOUT:
                    proc.kill()
                    return

        wd = threading.Thread(target=_watchdog, daemon=True)
        wd.start()

        # Stream JSON events line-by-line
        final_result = ""
        for line in proc.stdout:
            last_activity[0] = time.time()
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type", "")

            # Capture the final result
            if event_type == "result":
                final_result = event.get("result", "")

            # Forward interesting events to the callback
            if on_event:
                on_event(event)

        proc.wait(timeout=30)

        if not final_result:
            stderr = proc.stderr.read()
            if stderr:
                final_result = f"(stderr: {stderr.strip()[:500]})"

        killed_by_watchdog = proc.returncode == -9
        _log_session(task, persona, final_result)
        if killed_by_watchdog and not final_result:
            return "(Claude CLI was killed — idle too long or exceeded timeout)"
        return final_result if final_result else "(no response from Claude)"

    except subprocess.TimeoutExpired:
        proc.kill()
        return f"Claude CLI timed out after {CLAUDE_TIMEOUT}s"
    except FileNotFoundError:
        return f"Claude CLI not found at '{CLAUDE_BIN}'. Is claude installed?"
    except Exception as e:
        return f"Error running Claude CLI: {e}"


def _log_session(task: str, persona: str | None, output: str):
    """Write a session log entry."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    label = persona or "trinity"
    logfile = LOGS_DIR / f"{ts}-{label}.log"

    log_content = (
        f"# Trinity Agent Session — {ts}\n"
        f"Persona: {persona or 'trinity (default)'}\n"
        f"Task: {task[:500]}\n\n"
        f"## Output\n{output[:10_000]}\n"
    )
    logfile.write_text(log_content)


# ── Claude Agent SDK execution path ──────────────────────────────
# Drop-in alternative to run_agent() above. Uses the claude-agent-sdk
# Python package directly — which under the hood spawns the same Claude
# Code CLI we'd otherwise subprocess, so Max subscription auth via
# ~/.claude/.credentials.json is inherited.
#
# Cron uses this path (cleaner async iteration, typed messages, usage
# accounting). The Telegram bot stays on subprocess run_agent() because
# it's been battle-tested there and the streaming variant is wired in.

def _build_full_prompt(task: str, persona: str | None, lightweight: bool) -> str:
    """Same prompt construction as run_agent — extracted for reuse."""
    parts: list[str] = []

    if lightweight:
        daily_ctx = load_daily_context()
        parts.append(
            "You are Trinity, CEO of OEFR Digital (oefrenterprise.com). "
            "Sharp, direct, ambitious. You run an AI-operated digital products business. "
            "TJ is founder/chairman. You have full autonomy to execute.\n"
            "Revenue: $9.99 total (first Etsy sale). 17+ products across Gumroad, Etsy, Vercel.\n"
            "Workspace: ~/.openclaw/workspace/. Products: ~/apps/OEFR Digital Products/.\n"
            f"Current time: {dt.datetime.now().strftime('%Y-%m-%d %H:%M ET')}\n"
            "Read files from ~/.openclaw/workspace/ as needed for context.\n"
            "Be concise and conversational — this is a Telegram chat."
        )
        if persona and persona in PERSONA_OVERRIDES:
            parts.append(f"\n{PERSONA_OVERRIDES[persona]}")
        parts.append(f"\n# Daily Context\n{daily_ctx}")
    else:
        identity = load_identity()
        daily_ctx = load_daily_context()
        parts.append("# Your Identity & Operating Context")
        parts.append(identity)
        if persona and persona in PERSONA_OVERRIDES:
            parts.append(f"\n# Persona Override\n{PERSONA_OVERRIDES[persona]}")
        parts.append(f"\n# Daily Context\n{daily_ctx}")
        parts.append(
            "\n# Execution Rules\n"
            "- DO the thing. Don't plan endlessly — execute.\n"
            "- Log actions to memory files in ~/.openclaw/workspace/memory/\n"
            "- Self-review: verify outputs before reporting success.\n"
            "- If blocked, report to Blockers Telegram group.\n"
            f"- Workspace root: {WORKSPACE}\n"
            "- Products root: ~/apps/OEFR Digital Products/\n"
            f"- Current time: {dt.datetime.now().strftime('%Y-%m-%d %H:%M ET')}\n"
            "- Keep responses concise and direct.\n"
        )

    parts.append(f"\n# Task\n{task}")
    return "\n".join(parts)


async def _sdk_query_collect(
    prompt: str,
    max_turns: int,
    model: str | None = None,
) -> tuple[str, dict | None]:
    """Run a single SDK query and collect (final_text, usage_dict)."""
    # Lazy import so the SDK isn't a hard dep for processes that only use
    # the subprocess path (e.g., the live Telegram bot).
    from claude_agent_sdk import (
        AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query,
    )

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        max_turns=max_turns,
        cwd=str(WORKSPACE),
        env=_shell_env(),
        cli_path=CLAUDE_BIN,
        model=model,  # None → CLI default; cycles can request e.g. Sonnet
        # 2026-07-09 Neo: raise stream-JSON buffer 1MB → 16MB. A single
        # oversized tool-output message (>1MB) raised CLIJSONDecodeError
        # deterministically (07-05 18:06 validator-executor death) — the
        # 07-04 retry-with-backoff can't cure a deterministic payload, so
        # all 3 attempts died identically. 16MB covers large tool outputs
        # while still bounding a runaway stream.
        max_buffer_size=16 * 1024 * 1024,
    )

    text_chunks: list[str] = []
    final_result: str | None = None
    usage: dict | None = None

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_chunks.append(block.text)
        elif isinstance(message, ResultMessage):
            # Prefer the SDK's assembled final result if available.
            if getattr(message, "result", None):
                final_result = message.result
            usage = getattr(message, "usage", None)

    output = final_result if final_result else "".join(text_chunks).strip()
    return output, usage


def run_agent_sdk(
    task: str,
    persona: str | None = None,
    max_turns: int = 30,
    print_output: bool = True,
    lightweight: bool = False,
    model: str | None = None,
) -> str:
    """Drop-in replacement for run_agent() using the Claude Agent SDK.

    Same auth (Max subscription via Claude Code CLI auth), same prompt
    structure, same return type. Behind the scenes uses the SDK's async
    query() and typed message stream instead of subprocess + stdout
    parsing. Cron cycles use this; Telegram bot stays on subprocess.

    Pass `model` to override the CLI default — useful for lighter cycles
    (e.g., heartbeat triage on Sonnet instead of Opus).
    """
    full_prompt = _build_full_prompt(task, persona, lightweight)

    from claude_agent_sdk._errors import (
        CLIJSONDecodeError, CLINotFoundError, MessageParseError, ProcessError,
    )

    retryable = (ProcessError, CLIJSONDecodeError, MessageParseError)
    max_attempts = 3
    backoff = 2.0
    output, usage = None, None
    last_err: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            output, usage = asyncio.run(
                asyncio.wait_for(_sdk_query_collect(full_prompt, max_turns, model=model),
                                 timeout=CLAUDE_TIMEOUT)
            )
            if attempt > 1 and print_output:
                print(f"[Trinity SDK] recovered on attempt {attempt}/{max_attempts}",
                      file=sys.stderr, flush=True)
            break
        except asyncio.TimeoutError:
            msg = f"Claude SDK timed out after {CLAUDE_TIMEOUT}s"
            if print_output:
                print(msg, file=sys.stderr, flush=True)
            return msg
        except CLINotFoundError as e:
            msg = f"Error running Claude SDK ({type(e).__name__}): {e}"
            if print_output:
                print(msg, file=sys.stderr, flush=True)
            return msg
        except retryable as e:
            last_err = e
            if print_output:
                print(f"[Trinity SDK] attempt {attempt}/{max_attempts} failed "
                      f"({type(e).__name__}): {e}", file=sys.stderr, flush=True)
            if attempt < max_attempts:
                time.sleep(backoff * (2 ** (attempt - 1)))
                continue
        except Exception as e:
            msg = f"Error running Claude SDK ({type(e).__name__}): {e}"
            if print_output:
                print(msg, file=sys.stderr, flush=True)
            return msg
    else:
        msg = (f"Error running Claude SDK after {max_attempts} attempts "
               f"({type(last_err).__name__}): {last_err}")
        if print_output:
            print(msg, file=sys.stderr, flush=True)
        return msg

    if print_output and output:
        print(output)

    # Stash usage on the log for later cost/accounting analysis.
    if usage:
        try:
            in_tok = usage.get("input_tokens", 0)
            out_tok = usage.get("output_tokens", 0)
            cache_read = usage.get("cache_read_input_tokens", 0)
            cache_create = usage.get("cache_creation_input_tokens", 0)
            print(
                f"[Trinity SDK] tokens — in:{in_tok} out:{out_tok} "
                f"cache_read:{cache_read} cache_create:{cache_create}",
                file=sys.stderr,
            )
        except Exception:
            pass

    _log_session(task, persona, output)
    return output if output else "(no response from Claude SDK)"


# ── CLI ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Trinity CEO Agent — OEFR Digital")
    parser.add_argument("--task", "-t", help="One-shot task to execute")
    parser.add_argument("--persona", "-p", choices=list(PERSONA_OVERRIDES.keys()),
                        help="Sub-agent persona (morpheus, oracle, seo_operator, needle_mover, second_brain, neo)")
    parser.add_argument("--needle", "-n", action="store_true",
                        help="Run the CEO Needle Mover cycle")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress output (just log)")
    args = parser.parse_args()

    # Determine the task
    if args.needle:
        task = NEEDLE_MOVER_TASK
        persona = "needle_mover"
    elif args.task:
        task = args.task
        persona = args.persona
    else:
        # Interactive: read from stdin
        print("Trinity CEO Agent — OEFR Digital")
        print("Enter your task (Ctrl+D to submit):\n")
        try:
            task = sys.stdin.read().strip()
        except KeyboardInterrupt:
            print("\nAborted.")
            sys.exit(0)
        if not task:
            print("No task provided.")
            sys.exit(1)
        persona = args.persona

    result = run_agent(
        task=task,
        persona=persona,
        print_output=not args.quiet,
    )

    if args.quiet:
        print(result)


if __name__ == "__main__":
    main()
