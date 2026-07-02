#!/usr/bin/env python3
"""Trinity CEO Agent — Cron runner.

Drop-in replacement for the shell scripts in ~/.openclaw/workspace/scripts/.
Each function runs a specific agent cycle and delivers results to Telegram.

Usage:
    python trinity/cron_runner.py needle        # CEO Needle Mover
    python trinity/cron_runner.py morpheus      # Morpheus CMO cycle
    python trinity/cron_runner.py oracle        # Oracle Research cycle
    python trinity/cron_runner.py seo           # SEO Content Operator
    python trinity/cron_runner.py nightly       # Nightly Self-Improvement

    # Second Brain cycles
    python trinity/cron_runner.py product-loop  # Full product management sweep
    python trinity/cron_runner.py store-audit   # Audit storefront + products
    python trinity/cron_runner.py stripe-pulse  # Stripe revenue + churn check
    python trinity/cron_runner.py build-doctor  # Build health across all products
    python trinity/cron_runner.py brain-review  # Weekly knowledge base review
    python trinity/cron_runner.py dream         # Nightly dreaming — extract long-term memory from sessions
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Cron uses the Claude Agent SDK path (typed messages, native async,
# usage accounting). Telegram bot keeps the subprocess run_agent() — both
# end up going through the same Claude Code CLI auth so Max subscription
# is preserved on either path.
from agent import run_agent_sdk as run_agent
from tools import send_telegram
from knowledge.wiki import add_signal, generate_briefing, load_for_cycle, reset_daily_signals
from rules import apply_kill_rules, check_llm_output
from rules.governance import retry_instruction

# Cycles whose LLM output is gated by governance.check_llm_output.
# A failed check triggers one retry with a stronger constraint suffix.
# Neo is included defensively — he shouldn't propose products, but the gate
# catches drift if he ever does.
GOVERNED_CYCLES = {
    "morpheus", "oracle", "needle", "product-loop",
    "neo-daily", "neo-weekly",
    "opportunity-scout", "validator-loop", "validator-executor",
    "product-qa-loop", "content-qa-loop",
}

# Cycles that get post-run knowledge-base treatment: signal logging +
# briefing regeneration. Write-to-knowledge cycles are all included.
SIGNALING_PERSONAS = {
    "second_brain", "neo", "opportunity_scout", "validator", "executor",
    "product_qa", "content_qa", "flow_qa",
}

# Deterministic cycles run pure Python — no LLM, no agent loop.
# They are dispatched outside the CYCLE_PROMPTS path.
DETERMINISTIC_CYCLES = {"killer-loop", "sensor-loop", "lifecycle-loop", "funnel-verifier"}


# ── Issue detection ─────────────────────────────────────────────
# If a cycle's output contains issues that need TJ's attention,
# extract them and forward to the Blockers group separately.
# This keeps Blockers as the single pane for "things I need to look at"
# while normal reports go to their designated groups.

ISSUE_MARKER = "## ISSUES"

_ISSUE_INSTRUCTION = (
    "\n\nIMPORTANT OUTPUT FORMAT: If you find issues that need TJ's attention, "
    "include a section starting with '## ISSUES' followed by a brief list. "
    "This section will be forwarded to the Blockers group automatically. "
    "Keep the issues section short and actionable — product, what's wrong, severity. "
    "Everything outside '## ISSUES' is the normal report."
)


def _extract_issues(output: str) -> str | None:
    """Extract the ## ISSUES section from cycle output, if present."""
    match = re.search(r"## ISSUES\s*\n(.*?)(?=\n## [^I]|\Z)", output, re.DOTALL)
    if match:
        issues_text = match.group(1).strip()
        if issues_text:
            return issues_text
    return None


CYCLE_PROMPTS = {
    "needle": {
        "persona": "needle_mover",
        "telegram_group": "oefr_strategies",
        "task": (
            "Run the CEO Needle Mover cycle for OEFR Digital.\n"
            "1. Read MISSION_CONTROL.md and today's memory for current state.\n"
            "2. Check reports/ for latest Morpheus and Oracle intel.\n"
            "3. Choose the single highest-impact zero-cost move most likely to drive the first sale right now.\n"
            "4. Prefer distributing an existing live offer over proposing a new product.\n"
            "5. PRE-FLIGHT EDGES.md GATE (mandatory): Before committing to your chosen move,\n"
            "   read trinity/knowledge/edges.md non-edges section and verify your move does NOT\n"
            "   require any of: TikTok/Instagram personality-driven distribution, creator persona,\n"
            "   face-on-camera, Etsy handmade aesthetic, premium-brand positioning, enterprise\n"
            "   B2B sales motion, or TJ-niche-anchor. Run the gate on your draft:\n"
            "     python3 ~/.openclaw/workspace/scripts/edges-non-edges-gate.py <draft-file>\n"
            "   Exit 0 = ship. Exit 1 = pivot to an edge-aligned move (production speed /\n"
            "   AI-native cost / parallel-experimentation / kill-fast / 24-7 operation /\n"
            "   zero-overhead) on a good-fit channel (Gumroad / owned-domain SEO /\n"
            "   niche professional micro-tools / seasonal digital products / cold-start\n"
            "   small subreddits). DO NOT ship and wait for governance veto retry.\n"
            "6. PRE-FLIGHT BLOG-SLUG GATE (mandatory if your move references any\n"
            "   oefrenterprise.com /blog/* URL): live-validate every slug against the\n"
            "   production sitemap. Never trust memorized or cached slug claims —\n"
            "   the 2026-05-19 Store-Audit-falsely-confirmed-iee-slug class. Run:\n"
            "     python3 ~/.openclaw/workspace/scripts/blog-slug-validator.py <draft-file>\n"
            "   Exit 0 = every /blog/* in the draft resolves HTTP 200. Exit 1 = at\n"
            "   least one slug 404s; the script prints canonical 'did you mean X?'\n"
            "   for each break. Apply the suggested fixes BEFORE shipping — do NOT\n"
            "   ship a customer-facing surface containing a 404 outbound link.\n"
            "7. Execute it — don't just plan.\n"
            "8. Log everything to memory.\n"
            "Return:\n- Chosen move\n- What you executed\n- Result\n- Next action"
        ),
    },
    "morpheus": {
        "persona": "morpheus",
        "telegram_group": "making_cheddar",
        "task": (
            "Run the Morpheus CMO cycle for OEFR Digital.\n"
            "1. Pick the single highest-impact zero-cost marketing/distribution move.\n"
            "2. Prefer distributing or repositioning an existing offer over proposing a new product.\n"
            "3. Do NOT default to TJ-adjacent/network-architect products just because they are familiar.\n"
            "4. Apply filter: can Trinity research, package, publish, and distribute this solo without TJ?\n"
            "5. Prefer products/offers with visible live buyer intent and broad reachable demand.\n"
            "6. If you recommend a niche offer, state the market proof.\n"
            "7. PRE-FLIGHT EDGES.md GATE (mandatory): Before authoring brief or shipping, read\n"
            "   trinity/knowledge/edges.md non-edges section and verify your proposal does NOT\n"
            "   require any of: TikTok/Instagram personality-driven distribution, creator persona,\n"
            "   face-on-camera, Etsy handmade aesthetic, premium-brand positioning, enterprise\n"
            "   B2B sales motion, or TJ-niche-anchor. Run the gate on your draft brief:\n"
            "     python3 ~/.openclaw/workspace/scripts/edges-non-edges-gate.py <draft-brief>\n"
            "   Exit 0 = ship the brief. Exit 1 = pivot to an edge-aligned move (production\n"
            "   speed / AI-native cost / parallel-experimentation / kill-fast / 24-7 operation\n"
            "   / zero-overhead) on a good-fit channel (Gumroad / owned-domain SEO / niche\n"
            "   professional micro-tools / seasonal digital products / cold-start small\n"
            "   subreddits). Two governance vetoes fired 2026-05-15 (TikTok creator + persona\n"
            "   arbitrage) — that retry overhead is exactly what this gate prevents.\n"
            "8. PRE-FLIGHT BLOG-SLUG GATE (mandatory if your brief references any\n"
            "   oefrenterprise.com /blog/* URL — pillar destinations, SEO articles,\n"
            "   funnel links): live-validate every slug against the production sitemap.\n"
            "   Never trust memorized or cached slug claims — the 2026-05-19 Morpheus\n"
            "   17:40 RETRY shipped 2 dead pillar slugs because the Store Audit had\n"
            "   memory-cached a 404 slug as 'correct'. Run:\n"
            "     python3 ~/.openclaw/workspace/scripts/blog-slug-validator.py <draft-brief>\n"
            "   Exit 0 = every /blog/* in the brief resolves HTTP 200. Exit 1 = at\n"
            "   least one slug 404s; the script prints canonical 'did you mean X?'\n"
            "   for each break. Apply the suggested fixes BEFORE handing off the brief\n"
            "   to Trinity day-shift — never ship a customer-facing brief with a slug\n"
            "   that points downstream to a 404.\n"
            "9. PRE-FLIGHT DESTINATION-FIDELITY GATE (mandatory if your brief proposes\n"
            "   a pin / social-post / external-distribution piece whose copy claims\n"
            "   that specific content exists on an oefrenterprise.com destination —\n"
            "   e.g. pin description enumerates H2s, claims '5 federal-law differences',\n"
            "   promises 'parent-side language'). The 2026-05-21 Content QA cycles\n"
            "   caught the SAME drift TWICE in 12h: 10:35 ET REVISE on 504-vs-IEP pin\n"
            "   ('7 decision-points' was a table-row-count proxy, not an article H2)\n"
            "   + 22:35 ET REVISE on PWN pin ('parent-side language for forcing the\n"
            "   written record' was a downstream-product deliverable, NOT a phrase\n"
            "   on the linked article). Pin-clickers land + bounce on structural\n"
            "   mismatch. To gate: at the END of your brief, add a ## destination-\n"
            "   fidelity block listing each destination URL + the exact claim phrases\n"
            "   you assert appear there (verbatim — H2 text, copy excerpts, not\n"
            "   paraphrases). The gate curl-greps each phrase against the LIVE\n"
            "   destination HTML. Format:\n"
            "     ## destination-fidelity\n"
            "     [url] https://www.oefrenterprise.com/blog/<slug>\n"
            "     - \"verbatim H2 or copy phrase\"\n"
            "     - \"another phrase claimed in pin desc\"\n"
            "   Then run:\n"
            "     python3 ~/.openclaw/workspace/scripts/destination-fidelity-gate.py <draft-brief>\n"
            "   Exit 0 = every claim phrase found on its destination HTML (or CLEAN\n"
            "   if no block needed — brief is internal-decision-only). Exit 1 = at\n"
            "   least one MISS; rewrite the claim with the actual H2/copy you found\n"
            "   when you curl'd the URL. Never paraphrase a destination claim from\n"
            "   memory or from source code (JSX strings drift from rendered HTML).\n"
            "10. Log everything to memory.\n"
            "Return:\n- Chosen move\n- What you executed or attempted\n- Result\n- Next action"
        ),
    },
    "oracle": {
        "persona": "oracle",
        "telegram_group": "oefr_strategies",
        "task": (
            "Run the Oracle Research cycle for OEFR Digital.\n"
            "1. Find the most decision-useful market/competitor signal under zero-cost mode.\n"
            "2. Keep it grounded, specific, and directly actionable.\n"
            "3. PRE-FLIGHT EDGES.md GATE (mandatory): Before publishing your `Recommended action`\n"
            "   field, read trinity/knowledge/edges.md non-edges section and verify your\n"
            "   recommendation does NOT propose: TikTok/Instagram personality-driven distribution,\n"
            "   creator persona use (even framed as arbitrage), face-on-camera, Etsy handmade\n"
            "   aesthetic, premium-brand positioning, enterprise B2B sales motion, or TJ-niche-\n"
            "   anchor. Observation/meta-discussion of competitor non-edges is allowed (use\n"
            "   marker 'non-edge per edges.md' or 'cohort observation only' in your text). Run\n"
            "   the gate on your draft:\n"
            "     python3 ~/.openclaw/workspace/scripts/edges-non-edges-gate.py <draft-file>\n"
            "   Exit 0 = ship recommendation. Exit 1 = pivot recommendation to edge-aligned\n"
            "   action. The 2026-05-15 15:00 ET creator-persona-arbitrage retry is the failure\n"
            "   mode this gate prevents.\n"
            "4. PRE-FLIGHT BLOG-SLUG GATE (mandatory if your recommendation references any\n"
            "   oefrenterprise.com /blog/* URL — competitor-article comparisons, refresh\n"
            "   targets, internal-linking proposals): live-validate every slug against the\n"
            "   production sitemap. Never trust memorized or cached slug claims — sensor-\n"
            "   loop integrity false-positives (2026-05-19 Store Audit class) propagate\n"
            "   downstream into briefs. Run:\n"
            "     python3 ~/.openclaw/workspace/scripts/blog-slug-validator.py <draft-file>\n"
            "   Exit 0 = every /blog/* in the draft resolves HTTP 200. Exit 1 = at least\n"
            "   one slug 404s; the script prints canonical 'did you mean X?' for each\n"
            "   break. Fix slugs in your recommendation BEFORE handoff.\n"
            "5. PRE-FLIGHT SANITY CHECK GATE (mandatory if your draft cites any federal\n"
            "   form numbers — HA-XXX / SSA-XXX / I-XXX / N-XXX / W-X / 1099-XX / Schedule X —\n"
            "   any r/<subreddit> references, or claims state-by-state / 50-state scope on a\n"
            "   federal-administered program — SSDI / SSI / DACA / USCIS / IRS): verifies form\n"
            "   identity against a primary-source registry, verifies sub existence via\n"
            "   reddit.com/<sub>/about.json, and flags federal-scope mismatches. The 2026-05-22\n"
            "   Oracle 3-brief-errors-in-36h class is what this gate prevents:\n"
            "   (a) 07:00 ET r/SocialSecurityDisability claimed as cohort sub — sub does NOT\n"
            "       exist (HTTP 404, 23 chars > Reddit 21-char limit).\n"
            "   (b) 15:01 ET Louis Law state-spam 50-state pattern implicitly assumed to\n"
            "       transfer to SSDI — SSDI is federal-administered, 50-state scope is\n"
            "       cosmetic mailing-address variance.\n"
            "   (c) 20:00 ET HA-520 claimed as 'non-attorney representative' form — actually\n"
            "       Appeals Council review; SSA-1696 is the representative-appointment form.\n"
            "   Run:\n"
            "     python3 ~/.openclaw/workspace/scripts/pre-draft-sanity-check.py <draft-file>\n"
            "   Exit 0 = clean. Exit 1 = at least one form/sub/scope claim failed — the\n"
            "   script prints the canonical correction. Fix BEFORE committing the draft\n"
            "   to memory. Network-degraded fallback: prefix with OFFLINE=1 (registry-only\n"
            "   fast path still catches known-bad forms + known-bad sub names).\n"
            "6. Log findings to memory.\n"
            "Return:\n- Key finding\n- Evidence\n- Why it matters now\n- Recommended action\n- Risk/caveat"
        ),
    },
    "seo": {
        "persona": "seo_operator",
        "telegram_group": "oefr_strategies",
        "task": (
            "Run the SEO Content Operator cycle for OEFR Digital under zero-cost mode.\n"
            "1. Pick one existing asset to distribute or refresh for SEO/discovery leverage.\n"
            "2. Keep it practical: exact asset, angle, title/copy, channel, and why now.\n"
            "3. PRE-FLIGHT BLOG-SLUG GATE (mandatory if you propose any internal-link\n"
            "   refresh, cross-link addition, or pillar/cluster reference to an existing\n"
            "   oefrenterprise.com /blog/* URL): live-validate every slug before writing\n"
            "   the diff. Never paste a slug from memory:\n"
            "     python3 ~/.openclaw/workspace/scripts/blog-slug-validator.py <draft-or-diff>\n"
            "   Exit 0 = every /blog/* reference is canonical-and-LIVE. Exit 1 = fix\n"
            "   slugs per the 'did you mean' canonical suggestions before shipping the\n"
            "   diff. The 2026-05-19 dead-pillar-slug propagation class is the failure\n"
            "   mode this prevents.\n"
            "4. DEPLOY-OR-HANDOFF (mandatory if you edit any file under ~/apps/oefr-website/):\n"
            "   RUNTIME FACT — the `oefr-digital` Vercel project has NO git-push auto-deploy\n"
            "   webhook configured. Editing a source file (lib/blog-posts.ts, app/**/page.tsx,\n"
            "   components/**, etc.) WITHOUT shipping the deploy = the change sits dead in\n"
            "   working tree until a downstream persona accidentally absorbs it. The 2026-05-20\n"
            "   08:00 ET SEO Operator cycle hit this failure mode and was only saved because\n"
            "   CEO Needle Mover 09:00 ET happened to run a deploy on the same window. Never\n"
            "   assume 'Vercel will deploy on next push' — verify with action.\n"
            "   Pick ONE of these two paths per cycle, NEVER both, NEVER neither:\n"
            "     (a) SHIP-IT (preferred if your edit is the entire intended change):\n"
            "         cd ~/apps/oefr-website && git add <file> && \\\n"
            "         git commit -m 'seo(<scope>): <what>' && \\\n"
            "         git push origin <current-branch> && \\\n"
            "         vercel --prod --yes && \\\n"
            "         # then curl-verify the change is LIVE on www.oefrenterprise.com before\n"
            "         # declaring success in your memory log (e.g. `curl -s <url> | grep -F\n"
            "         # '<new-text>'` should return non-empty)\n"
            "     (b) HANDOFF (only if your edit is partial / batched / collision-risk):\n"
            "         Write the diff to /tmp/seo-operator-<YYYY-MM-DD-HHMM>-pending-deploy.diff\n"
            "         AND signal explicitly: `python trinity/knowledge/cli.py signal seo \\\n"
            "         'PENDING DEPLOY: <path> edited at <ts>, see <diff-path>, ship next CEO\n"
            "         Needle Mover cycle'`. Your memory entry MUST name the diff path so the\n"
            "         next persona that runs `signal | grep PENDING DEPLOY` can find it.\n"
            "5. Log actions to memory.\n"
            "Return:\n- Asset to push\n- Distribution angle\n- Exact copy or title\n- Channel\n- Expected upside\n- Deploy disposition (SHIP-IT commit-hash + curl-verified | HANDOFF diff-path)"
        ),
    },
    "nightly": {
        "persona": None,
        "telegram_group": "oefr_strategies",
        "task": (
            "Run the Nightly Self-Improvement review for OEFR Digital.\n"
            "1. Read today's memory log and any reports generated today.\n"
            "2. Identify ONE blocker where TJ had to intervene (or could have).\n"
            "3. Document the fix in memory/self-improvement.md.\n"
            "4. Implement the fix if possible (update configs, scripts, workflows).\n"
            "5. Report the improvement.\n"
            "Return:\n- Blocker identified\n- Root cause\n- Fix implemented\n- Prevention going forward"
        ),
    },

    # ── Second Brain cycles ─────────────────────────────────────
    # These use the knowledge CLI for structured logging:
    #   python trinity/knowledge/cli.py log-issue <product> <desc> [--status open]
    #   python trinity/knowledge/cli.py log-audit <type> <product> <findings> <actions>
    #   python trinity/knowledge/cli.py signal <cycle> <message>
    #   python trinity/knowledge/cli.py query <topic>
    #   python trinity/knowledge/cli.py briefing
    "product-loop": {
        "persona": "second_brain",
        "telegram_group": "apps_forging",
        "task": (
            "Run the Second Brain Product Loop for OEFR Digital.\n\n"
            "KNOWLEDGE CLI — use these to read/write the knowledge base:\n"
            "  python trinity/knowledge/cli.py query <topic>     # search knowledge\n"
            "  python trinity/knowledge/cli.py log-issue <product> '<desc>' --status open\n"
            "  python trinity/knowledge/cli.py log-audit <type> <product> '<findings>' '<actions>'\n"
            "  python trinity/knowledge/cli.py signal product-loop '<key finding>'\n"
            "  python trinity/knowledge/cli.py briefing          # regenerate briefing\n\n"
            "STEPS:\n"
            "1. Run `python trinity/knowledge/cli.py query open` to see current open issues.\n"
            "2. Pick the SINGLE highest-impact product that needs attention.\n"
            "   Products root: ~/apps/OEFR Digital Products/\n"
            "   Key products: netarch-pro, habitforge, resume-builder, invoice-generator,\n"
            "   subscription-tracker, content-calendar, meal-planner, password-vault,\n"
            "   compliance-calendar, budget-tracker, net-salary-calc, ai-layoff-pack\n"
            "3. For the chosen product:\n"
            "   a. Read its package.json, CLAUDE.md, and key source files\n"
            "   b. Run `npm run build` to check for build errors\n"
            "   c. Run `npm run lint` if available\n"
            "   d. Check for obvious bugs, broken imports, dead code\n"
            "   e. Check for security issues (exposed keys, XSS, etc.)\n"
            "4. If you find a REAL issue (not a false positive):\n"
            "   a. Fix it surgically (small, focused change)\n"
            "   b. Run build again to verify the fix\n"
            "   c. Commit to a dev branch (NEVER main)\n"
            "   d. Log with: python trinity/knowledge/cli.py log-issue <product> '<desc>'\n"
            "   e. Log with: python trinity/knowledge/cli.py log-audit product-loop <product> '<findings>' '<actions>'\n"
            "5. If no issues found, log a clean audit.\n"
            "6. Signal key finding: python trinity/knowledge/cli.py signal product-loop '<summary>'\n\n"
            "Return:\n- Product audited\n- Issues found (or 'clean')\n- Fixes applied\n- Committed to branch\n- Next product to audit"
        ),
    },
    "store-audit": {
        "persona": "second_brain",
        "telegram_group": "apps_forging",
        "task": (
            "Run the Second Brain Store Audit for OEFR Digital.\n\n"
            "KNOWLEDGE CLI — use these to read/write the knowledge base:\n"
            "  python trinity/knowledge/cli.py query <topic>\n"
            "  python trinity/knowledge/cli.py log-issue <product> '<desc>' --status open\n"
            "  python trinity/knowledge/cli.py log-audit store-audit <product> '<findings>' '<actions>'\n"
            "  python trinity/knowledge/cli.py signal store-audit '<key finding>'\n\n"
            "STEPS:\n"
            "1. Run `python trinity/knowledge/cli.py query false-positive` to check what to skip.\n"
            "2. Check oefr-digital.vercel.app — use curl to verify it responds with 200.\n"
            "3. For each deployed product, check:\n"
            "   a. Does the Vercel deployment exist? (`vercel ls` in the product dir)\n"
            "   b. Any recent deployment failures? (`vercel inspect` on latest)\n"
            "   c. Are environment variables set? (`vercel env ls`)\n"
            "4. Check Gumroad product pages are live (curl the URLs from gumroad-products/).\n"
            "5. Check Etsy listings are accessible.\n"
            "6. BLOG-SLUG VERIFICATION (mandatory, never self-correct from memory): for any\n"
            "   /blog/<slug> URL you intend to claim as '200 verified', validate it through\n"
            "   the deterministic gate, NOT by re-typing what you remember the canonical to be:\n"
            "     python3 ~/.openclaw/workspace/scripts/blog-slug-validator.py /blog/<slug>\n"
            "   If exit 1, the gate prints the canonical 'did you mean X?' — record that\n"
            "   canonical in your audit notes, NOT the slug you originally typed. The\n"
            "   2026-05-19 Store Audit false-positive (iee-request-34-cfr-300-502 logged\n"
            "   as 200 when actually 404; the canonical is independent-educational-\n"
            "   evaluation-iee-request-34-cfr-300-502) is the failure-mode this prevents.\n"
            "7. Log all findings with the knowledge CLI.\n\n"
            "Return:\n- Storefront status\n- Products checked\n- Issues found\n- Actions taken"
        ),
    },
    "stripe-pulse": {
        "persona": "second_brain",
        "telegram_group": "making_cheddar",
        "task": (
            "Run the Second Brain Stripe Pulse for OEFR Digital.\n\n"
            "KNOWLEDGE CLI:\n"
            "  python trinity/knowledge/cli.py query stripe\n"
            "  python trinity/knowledge/cli.py query churn\n"
            "  python trinity/knowledge/cli.py log-audit stripe-pulse <product> '<findings>' '<actions>'\n"
            "  python trinity/knowledge/cli.py signal stripe-pulse '<key finding>'\n\n"
            "STEPS:\n"
            "1. Check for previous stripe-related findings: `python trinity/knowledge/cli.py query stripe`\n"
            "2. Use the Stripe CLI or API to check:\n"
            "   a. Recent charges/payments (last 7 days)\n"
            "   b. Any failed payments or disputes\n"
            "   c. Active subscriptions count\n"
            "   d. Recent customer activity\n"
            "   e. Any webhook failures\n"
            "3. If a customer recently churned (canceled subscription):\n"
            "   a. Investigate: when did they sign up, what product, any support tickets?\n"
            "   b. Log a churn autopsy with the knowledge CLI\n"
            "4. Log revenue pulse with the knowledge CLI.\n"
            "5. If revenue is zero for 7+ days, flag it as a blocker.\n\n"
            "Return:\n- Revenue (7d)\n- Active customers\n- Churn events\n- Payment failures\n- Recommended action"
        ),
    },
    "build-doctor": {
        "persona": "second_brain",
        "telegram_group": "apps_forging",
        "task": (
            "Run the Second Brain Build Doctor across ALL OEFR Digital products.\n\n"
            "KNOWLEDGE CLI:\n"
            "  python trinity/knowledge/cli.py query wont-fix     # skip these\n"
            "  python trinity/knowledge/cli.py log-issue <product> '<desc>' --status open\n"
            "  python trinity/knowledge/cli.py log-audit build-doctor <product> '<findings>' '<actions>'\n"
            "  python trinity/knowledge/cli.py signal build-doctor '<summary>'\n\n"
            "STEPS:\n"
            "1. Check what to skip: `python trinity/knowledge/cli.py query wont-fix`\n"
            "2. For each product in ~/apps/OEFR Digital Products/ that has a package.json:\n"
            "   a. cd into the directory\n"
            "   b. Run `npm run build 2>&1` and capture output\n"
            "   c. If build fails: log issue, attempt a fix if obvious\n"
            "   d. If build succeeds: mark as healthy\n"
            "3. For entryexpert (Python): run `python -c 'import models'` to check imports.\n"
            "4. Log full results with the knowledge CLI.\n"
            "5. Signal summary: `python trinity/knowledge/cli.py signal build-doctor 'X/Y healthy'`\n\n"
            "IMPORTANT: Run `npm install` before build if node_modules is missing.\n"
            "IMPORTANT: Do NOT run all builds in parallel — do them sequentially.\n"
            "IMPORTANT: Set timeout per build to 120s. Skip if it takes longer.\n\n"
            "Return:\n- Products checked: N\n- Healthy: N\n- Broken: N (list them)\n- Fixes attempted\n- Fixes that worked"
        ),
    },
    "brain-review": {
        "persona": "second_brain",
        "telegram_group": "oefr_strategies",
        "task": (
            "Run the Weekly Second Brain Review.\n\n"
            "KNOWLEDGE CLI:\n"
            "  python trinity/knowledge/cli.py query <topic>\n"
            "  python trinity/knowledge/cli.py briefing           # regenerate briefing\n"
            "  python trinity/knowledge/cli.py log-lesson '<lesson>' '<context>' --category win|failure|process\n"
            "  python trinity/knowledge/cli.py reset-signals      # clear for new week\n\n"
            "STEPS:\n"
            "1. Read all four knowledge files in ~/apps/OEFR Digital Products/trinity/knowledge/\n"
            "2. Archive issues that were fixed more than 30 days ago.\n"
            "3. Check if any 'open' issues are actually resolved now (run a quick check).\n"
            "4. Identify patterns:\n"
            "   a. Which products keep breaking? Why?\n"
            "   b. Which audits keep finding the same things?\n"
            "   c. Are there lessons we're not learning?\n"
            "5. Log patterns as lessons: `python trinity/knowledge/cli.py log-lesson '<lesson>' '<context>'`\n"
            "6. Regenerate briefing: `python trinity/knowledge/cli.py briefing`\n"
            "7. Reset daily signals: `python trinity/knowledge/cli.py reset-signals`\n"
            "8. Update MISSION_CONTROL.md with current product health status.\n\n"
            "Return:\n- Knowledge base size (entries per file)\n- Issues: open/fixed/false-positive\n- Top patterns identified\n- Cleanup actions taken"
        ),
    },
    "dream": {
        "persona": "second_brain",
        "telegram_group": "oefr_strategies",
        "task": (
            "Run the Nightly Dream Cycle — consolidate today's conversations into long-term memory.\n\n"
            "You are processing today's Telegram session logs to extract important information\n"
            "that should persist in the wiki knowledge base. This is like how the brain\n"
            "consolidates short-term memory into long-term memory during sleep.\n\n"
            "KNOWLEDGE CLI:\n"
            "  python trinity/knowledge/cli.py log-issue <product> '<desc>' --status open\n"
            "  python trinity/knowledge/cli.py log-decision '<what>' '<context>' '<why>'\n"
            "  python trinity/knowledge/cli.py log-lesson '<lesson>' '<context>' --category win|failure|process\n"
            "  python trinity/knowledge/cli.py signal dream '<summary>'\n"
            "  python trinity/knowledge/cli.py briefing\n\n"
            "STEPS:\n"
            "1. Read today's session log: ~/apps/OEFR Digital Products/trinity/knowledge/sessions/\n"
            "   (find today's date file, e.g. 2026-04-10.md)\n"
            "2. Read the existing knowledge base for context:\n"
            "   python trinity/knowledge/cli.py query open\n"
            "3. For EACH conversation in the session log, extract:\n"
            "   a. DECISIONS: Did TJ decide something? ('do X', 'don't do Y', 'switch to Z')\n"
            "      → Log with: python trinity/knowledge/cli.py log-decision\n"
            "   b. ISSUES: Did TJ report a problem? Did Trinity find a bug?\n"
            "      → Log with: python trinity/knowledge/cli.py log-issue\n"
            "   c. TASKS: Did TJ assign work? ('build X', 'fix Y', 'ship Z')\n"
            "      → Log with: python trinity/knowledge/cli.py log-lesson (as task context)\n"
            "   d. FEEDBACK: Did TJ correct Trinity? ('not that', 'wrong approach')\n"
            "      → Log with: python trinity/knowledge/cli.py log-lesson --category failure\n"
            "   e. WINS: Did something work well? Positive feedback?\n"
            "      → Log with: python trinity/knowledge/cli.py log-lesson --category win\n"
            "   f. CONTEXT: Key business context mentioned (revenue, customers, partnerships)\n"
            "      → Log with: python trinity/knowledge/cli.py log-decision\n"
            "4. Skip small talk, greetings, and noise — only extract actionable intelligence.\n"
            "5. Check for duplicates before logging (query the knowledge base first).\n"
            "6. ISSUE-CLOSE VERIFICATION GATE (mandatory before marking ANY issue as 'fixed'):\n"
            "   FAILURE MODE (2026-05-23): Dream cycle 00:32 ET closed oefr-website-email-delivery\n"
            "   as 'fixed' because TJ said he added Gmail app passwords to ~/.profile. But the\n"
            "   env-var names used @ and . characters (POSIX-invalid). Bash silently rejected them.\n"
            "   Neo caught 9h later that the vars never loaded. The 'P0 closed' claim was factually\n"
            "   wrong — would have broken first-sale fulfillment at the worst possible moment.\n"
            "   RULE: NEVER mark an issue as 'fixed' based on narrative alone. Run verification:\n"
            "   - For env-var/credential issues: python3 ~/.openclaw/workspace/scripts/issue-close-verifier.py env <VAR_NAME>\n"
            "   - For URL/endpoint issues: python3 ~/.openclaw/workspace/scripts/issue-close-verifier.py url <URL>\n"
            "   - For file-existence issues: python3 ~/.openclaw/workspace/scripts/issue-close-verifier.py file <PATH>\n"
            "   - For capability issues: python3 ~/.openclaw/workspace/scripts/issue-close-verifier.py cmd '<verification_command>'\n"
            "   Gate must return [VERIFIED] (exit 0) before you write status=fixed.\n"
            "   If gate returns [FAILED] (exit 1), mark issue as 'reported-fix-unverified' and\n"
            "   flag for next Neo Daily or Trinity day-shift to investigate. Do NOT close.\n"
            "7. Regenerate the briefing: python trinity/knowledge/cli.py briefing\n"
            "8. Write a dream summary to memory.\n\n"
            "Return:\n- Sessions processed: N\n- Decisions extracted: N\n- Issues found: N\n"
            "- Lessons logged: N\n- Issues verified-closed: N\n- Issues verification-failed: N\n"
            "- Key themes from today"
        ),
    },

    # ── Neo (CTO/CSO) cycles ────────────────────────────────────
    # Migrated from ~/.openclaw/workspace/scripts/run-neo-claude.sh into
    # Trinity's framework. Daily = act on top finding (fix on dev), not
    # just narrate. Weekly = broader architecture review + hardening backlog.
    # See ~/.openclaw/workspace/playbooks/neo-cto-cso-doctrine.md for full doctrine.
    "neo-daily": {
        "persona": "neo",
        "telegram_group": "oefr_strategies",
        "task": (
            "Run the Daily Technical Risk Review for OEFR Digital.\n\n"
            "KNOWLEDGE CLI:\n"
            "  python trinity/knowledge/cli.py query <topic>     # check for false positives FIRST\n"
            "  python trinity/knowledge/cli.py log-issue <product> '<desc>' --status open|fixed\n"
            "  python trinity/knowledge/cli.py log-audit neo-daily <product> '<findings>' '<actions>'\n"
            "  python trinity/knowledge/cli.py signal neo-daily '<key finding>'\n\n"
            "STEPS:\n"
            "1. Check for known false positives: python trinity/knowledge/cli.py query false-positive\n"
            "2. Read MISSION_CONTROL.md, today's memory, recent reports/.\n"
            "3. The Product Roster is in your wiki context — products marked dead should NOT receive any technical work.\n"
            "4. Inspect recent technical changes:\n"
            "   - git log --since='1 day ago' --all across active products in ~/apps/OEFR Digital Products/\n"
            "   - vercel ls (recent deployments)\n"
            "   - grep for exposed secrets in committed code (sk_live, AKIA, BEGIN PRIVATE KEY, etc.)\n"
            "   - Check auth/payment boundaries on any changed files\n"
            "   - Check cron jobs that take external actions (browser automation, Telegram, Stripe)\n"
            "5. Identify the SINGLE highest-severity finding (P0 > P1 > P2 > P3) on a still-active product.\n"
            "6. If it's a P0 or P1 you can fix surgically (small, focused change):\n"
            "   a. Fix it. Commit to a dev branch (NEVER main).\n"
            "   b. Run build/lint to verify.\n"
            "   c. Log fix: python trinity/knowledge/cli.py log-issue <product> '<desc>' --status fixed\n"
            "   d. Log audit: python trinity/knowledge/cli.py log-audit neo-daily <product> '<findings>' '<actions>'\n"
            "7. If it's P0+ but you can't fix (needs TJ for auth/spending/legal): include in '## ISSUES' section so it forwards to Blockers.\n"
            "8. Write the daily report to ~/.openclaw/workspace/reports/neo-daily-YYYY-MM-DD.md\n"
            "   Format: scope reviewed, what changed, top risks (with severity P0-P3), exact fixes applied or recommended, what can wait, blocked vs not blocked, expected impact if ignored.\n"
            "9. Signal: python trinity/knowledge/cli.py signal neo-daily '<one-line summary>'\n\n"
            "FAILURE MODES TO AVOID (from neo-cron-workflow.md):\n"
            "- Generic security platitudes ('use HTTPS', 'rotate secrets')\n"
            "- No severity labels\n"
            "- No exact recommended fix\n"
            "- Routing everything to TJ instead of Trinity\n"
            "- Just narrating without acting on fixable P0/P1 issues\n\n"
            "Return:\n- Scope reviewed\n- Top risk with severity (P0-P3)\n- Fix applied (or recommended)\n- What can wait\n- Blocked vs not blocked\n- Expected impact if ignored"
        ),
    },
    "product-qa-loop": {
        "persona": "product_qa",
        "telegram_group": "oefr_strategies",
        "task": (
            "Run Product QA on validations that are ready to ship to customers.\n\n"
            "PATHS:\n"
            "  PROJECT     = /home/oghenetejiri/apps/OEFR Digital Products\n"
            "  VALIDATIONS = $PROJECT/trinity/knowledge/validations/\n"
            "  ROSTER      = $PROJECT/trinity/knowledge/product-roster.md\n\n"
            "STEPS:\n"
            "1. List validations: `ls -lt \"$PROJECT/trinity/knowledge/validations/\"*.md` (skip README.md).\n"
            "2. For each validation whose Status is `greenlit`, `live_rung1` with paid charges, or `live_rung2`, apply all 6 persona checks:\n"
            "   - Spec completeness (every promise buildable with spec in the doc)\n"
            "   - Pricing logic (pre-order vs post, refund math, competitive defensibility)\n"
            "   - Deliverable clarity (buyer knows exactly what they pay for)\n"
            "   - Internal consistency (forum copy matches Gumroad copy matches spec)\n"
            "   - Voice/tone (no slop, no unverifiable superlatives)\n"
            "   - Refund/delivery promise (explicit dates, no weasel)\n"
            "3. For each checked validation, log the audit via knowledge CLI:\n"
            "   `python \"$PROJECT/trinity/knowledge/cli.py\" log-audit product-qa <slug> '<findings>' '<actions>'`\n"
            "4. PASS → append a 'QA: PASS' line to the validation doc's monitoring log + set Status to `build_ready` "
            "   (create that status if missing; it lives between live_rung1-greenlit and actual product build).\n"
            "5. FAIL → log issues with exact line numbers and fixes; include in `## ISSUES` section for Blockers forwarding. "
            "   Validation Status stays unchanged. Do NOT rewrite copy yourself.\n"
            "6. Signal: `python \"$PROJECT/trinity/knowledge/cli.py\" signal product-qa '<N audited, M blocked>'`\n\n"
            "Return:\n- Validations audited: N\n- Pass: N\n- Fail: N (top issue per failure)\n- Build-ready after this run: <list>"
        ),
    },
    "content-qa-loop": {
        "persona": "content_qa",
        "telegram_group": "oefr_strategies",
        "task": (
            "Run Content QA on recent outputs from writing cycles before they reach public distribution.\n\n"
            "PATHS:\n"
            "  PROJECT   = /home/oghenetejiri/apps/OEFR Digital Products\n"
            "  REPORTS   = ~/.openclaw/workspace/reports/\n"
            "  MEMORY    = ~/.openclaw/workspace/memory/\n"
            "  X-LOG     = ~/.openclaw/workspace/projects/x-post-log.md\n\n"
            "STEPS:\n"
            "1. Identify content produced in the last 24h that has NOT yet been QA'd. Sources to scan:\n"
            "   - Morpheus reports today (`grep -l morpheus $MEMORY/$(date +%Y-%m-%d).md` or check $REPORTS)\n"
            "   - Recent x-post-log entries (tail -40 $X-LOG)\n"
            "   - Any SEO articles pending publish (check for drafts in $REPORTS or ~/apps/oefr-website/ content dir)\n"
            "   - Forum post drafts in validation docs (Rung-1 body if not yet executed)\n"
            "2. For each piece, apply the 7 persona checks:\n"
            "   - Originality (specific vs generic)\n"
            "   - Factual integrity (claims sourced)\n"
            "   - Voice consistency (direct/practical, not influencer/corporate)\n"
            "   - Link integrity (curl each URL)\n"
            "   - No hollow engagement bait\n"
            "   - Length discipline (cut 20% if possible without losing specificity)\n"
            "   - Edges.md fit (target market rewards OEFR edges, not non-edges)\n"
            "3. For each check, record the verdict via the knowledge CLI:\n"
            "   `python \"$PROJECT/trinity/knowledge/cli.py\" log-audit content-qa '<source>' '<findings>' '<actions>'`\n"
            "4. Outcomes:\n"
            "   APPROVED → log, move on.\n"
            "   REVISE → produce a concrete revised version with change notes, log, signal for re-distribution.\n"
            "   FAIL → specific issues + exact rewrites in `## ISSUES` section; content stays unpublished until fixed.\n"
            "5. Signal: `python \"$PROJECT/trinity/knowledge/cli.py\" signal content-qa '<N reviewed, M failed>'`\n\n"
            "Return:\n- Content reviewed: N\n- Approved: N\n- Revised: N\n- Failed (blocked): N\n- Top issue this run (one line)"
        ),
    },
    "customer-flow-qa": {
        "persona": "flow_qa",
        "telegram_group": "oefr_strategies",
        "task": (
            "Run Customer Flow QA — weekly end-to-end buyer-journey simulation.\n\n"
            "PATHS:\n"
            "  PROJECT     = /home/oghenetejiri/apps/OEFR Digital Products\n"
            "  VALIDATIONS = $PROJECT/trinity/knowledge/validations/\n\n"
            "FLOWS (run each; degrade gracefully if a prerequisite isn't live yet):\n"
            "A. Stripe pre-order flow — for every live_rung1 / live_rung2 validation, use Playwright CDP or curl to:\n"
            "   - Load the Stripe Payment Link URL (expect HTTP 200, page renders)\n"
            "   - Verify merchant header shows 'OEFR Digital'\n"
            "   - Verify price matches the validation doc\n"
            "   - Verify delivery commitment visible\n"
            "   - Verify success URL resolves (load oefrenterprise.com/thanks?psl=<slug>)\n"
            "B. Post-purchase email flow — if a lifecycle engine exists (Resend), verify a welcome email template\n"
            "   is set up for each product. If not yet implemented, note gap in `## ISSUES`.\n"
            "C. Landing page flow — curl oefrenterprise.com homepage + /about + /terms + /privacy + /refund + /contact.\n"
            "   Note which return 404 so TJ knows what's still missing for compliance + UX.\n"
            "D. Forum/social flow — for each recent X post in the last 7 days (pull from x-post-log.md and/or search),\n"
            "   verify the tweet still loads (not deleted/shadowbanned); verify embedded Stripe link still resolves.\n"
            "E. Support accessibility — verify /contact page lists an email or form; if oefrenterprise.com/contact is 404, flag.\n\n"
            "OUTPUT:\n"
            "  For each flow letter A-E: PASS / FAIL / DEGRADED with evidence (URL, HTTP code, screenshot if unusual).\n"
            "  Summary: overall buyer-journey health score (N flows passing / total).\n"
            "  `## ISSUES` for any FAIL/DEGRADED with specific fix + owner (which cycle or TJ).\n\n"
            "HARD RULES:\n"
            "- Use real tools (curl, Playwright). No simulated checks.\n"
            "- Don't attempt fixes yourself — detect only. Route fixes to executor, morpheus, or TJ.\n"
            "- If CDP browser session is dead and a flow needs browser, degrade that flow to 'BLOCKED' and report.\n\n"
            "Return:\n- Flows passing: N/5\n- Top buyer-facing issue this week\n- New regressions vs last week (if any)"
        ),
    },
    "validator-executor": {
        "persona": "executor",
        "telegram_group": "oefr_strategies",
        "task": (
            "Run the Validator Executor — advance all validation docs through their state machine. "
            "DEPLOY EACH DOC ON THE LANE IT DECLARES IN ITS **Rung** LINE — do NOT assume Stripe.\n\n"
            "LANE RULE (this closes the 30+ day DEPLOY=0 freeze / false-TJ-escalation, 2026-06-04 nightly fix):\n"
            "  - A doc declaring 'FREE Gumroad pre-order + value-first forum post' deploys on the BROWSER lane\n"
            "    (Gumroad CDP/Playwright on :98 with GUMROAD_USERNAME/GUMROAD_PASSWORD + a Reddit value post).\n"
            "    Both platforms are ALREADY AUTHENTICATED. This is SELF-SERVICEABLE — execute it yourself.\n"
            "  - DO NOT escalate the lane choice ('browser vs Stripe charge-now') to TJ. The doc already\n"
            "    picked the lane; re-asking TJ is a FALSE escalation and the documented #1 failure mode.\n"
            "  - Charge-now Stripe Payment Links on an UNBUILT product re-introduce chargeback risk\n"
            "    (COMPANY_VALUES). Only use the Stripe lane when the doc's **Rung** explicitly declares it.\n\n"
            "PATHS (absolute; cwd is ~/.openclaw/workspace/):\n"
            "  PROJECT     = /home/oghenetejiri/apps/OEFR Digital Products\n"
            "  VALIDATIONS = $PROJECT/trinity/knowledge/validations/\n"
            "  QUEUE       = $PROJECT/trinity/knowledge/opportunities/queue.md\n"
            "  ROUTER      = ~/.openclaw/workspace/scripts/deploy-lane-router.py (deterministic lane verdict)\n"
            "  DEPLOY_NOW  = ~/.openclaw/workspace/memory/DEPLOY_NOW_QUEUE.md (router output — read FIRST)\n"
            "  CDP         = http://127.0.0.1:18800 (Gumroad listing + forum posts; not needed for Stripe)\n\n"
            "STEPS:\n"
            "0. Run the deterministic router and read its queue BEFORE deciding any deploy:\n"
            "   `python3 ~/.openclaw/workspace/scripts/deploy-lane-router.py` then read DEPLOY_NOW_QUEUE.md.\n"
            "   Anything it marks SELF_SERVICEABLE_* must be deployed this cycle — never escalated to TJ.\n"
            "1. List all validation docs:\n"
            "   `ls -lt \"$PROJECT/trinity/knowledge/validations/\"*.md`  (skip README.md)\n"
            "2. For each doc:\n"
            "   a. Parse: Status, **Rung** declared lane, Stripe Payment Link ID (if present), forum URL (if present), thresholds, kill_date, partial_date.\n"
            "   b. Determine state; advance per the state machine in your persona.\n\n"
            "3a. For DEPLOY when the doc declares the GUMROAD pre-order lane (browser, chargeback-safe — PREFERRED):\n"
            "   a. Create the FREE Gumroad pre-order listing from the doc's §1 copy (title/subtitle/description/price)\n"
            "      via CDP/Playwright on :98 using GUMROAD_USERNAME/GUMROAD_PASSWORD. Pre-order = no charge until release.\n"
            "   b. Verify the listing URL returns HTTP 200.\n"
            "   c. Post the doc's §2 value-first forum copy to its named subreddit via CDP+xdotool on :98 (pure value, no CTA).\n"
            "   d. Update the doc: Status=live_rung1; append a 'Live' section with the Gumroad URL, forum permalink,\n"
            "      and launch UTC timestamp; write both into distribution_evidence_path so the kill_date can be VALID.\n\n"
            "3b. For DEPLOY only when the doc explicitly declares the STRIPE pre-order lane:\n"
            "   a. Write a small Python script (e.g. /tmp/executor-deploy-<slug>.py) that uses the stripe SDK:\n"
            "        import stripe, os\n"
            "        stripe.api_key = os.environ['STRIPE_SECRET']\n"
            "        product = stripe.Product.create(name=..., description=...)\n"
            "        price   = stripe.Price.create(product=product.id, unit_amount=<cents>, currency='usd')\n"
            "        link    = stripe.PaymentLink.create(\n"
            "            line_items=[{'price': price.id, 'quantity': 1}],\n"
            "            metadata={'validation_doc': '<slug>.md', 'rung': '1'},\n"
            "            after_completion={'type':'redirect','redirect':{'url':'https://oefrenterprise.com/thanks?psl=<slug>'}},\n"
            "            restrictions={'completed_sessions':{'limit': 20}},\n"
            "            custom_text={'submit':{'message': <delivery commitment from doc>}})\n"
            "        print(link.url, link.id, product.id, price.id)\n"
            "      Use the pre-order price from the validation doc (convert to cents). Quantity limit 20.\n"
            "   b. Run the script. Capture URL + IDs.\n"
            "   c. Verify link works: `curl -sI <link.url>` expects 200.\n"
            "   d. Post the forum content via browser (CDP). For Indie Hackers OR Reddit (Reddit is fine now — "
            "      only low karma limits, not blocked). For FB groups use the x-browser-profile if applicable.\n"
            "   e. Update the validation doc: Status=live_rung1. Append a 'Live' section with Stripe URL + link ID + product ID + forum URL + launch UTC timestamp.\n\n"
            "4. For MONITOR (live_rung1 / live_rung2) — Stripe API, not scraping:\n"
            "   a. For each live doc, read Stripe Payment Link ID from the 'Live' section.\n"
            "   b. Query Stripe:\n"
            "        sessions = stripe.checkout.Session.list(payment_link='<plink_id>', limit=100)\n"
            "        paid     = [s for s in sessions.data if s.status == 'complete' and s.payment_status == 'paid']\n"
            "   c. Compute total $ charged; check forum engagement (best-effort).\n"
            "   d. Against thresholds + today's date, decide: stay / reject / partial / greenlight.\n"
            "   e. Update doc Status + append a monitoring log line with date, charge count, total $, decision.\n"
            "   f. If rejected/greenlit/partial, update queue.md's opportunity Status accordingly.\n"
            "   g. If greenlit → fire a Telegram win summary in the executor report.\n"
            "   h. If partial → include ## ISSUES requesting TJ's $30 card approval for the rung-2 paid ad.\n\n"
            "FAILURE HANDLING:\n"
            "- Stripe API fails (rate limit, auth): Status stays, ## ISSUES with stripe error text.\n"
            "- Forum post fails but Stripe succeeded: Status=live_rung1 (Stripe is the primary signal), "
            "  ## ISSUES noting the forum post needs manual launch — specify the exact copy + URL to paste to.\n"
            "- Everything else: best-effort, fail open, flag to blockers, next run retries.\n\n"
            "Return:\n- Validations reviewed: N\n- Deploys completed: N (with Stripe Payment Link URLs)\n"
            "- Transitions: drafted→live_rung1: N, live_rung1→rejected: N, live_rung1→greenlit: N, etc.\n"
            "- Blockers raised: N (summarize)"
        ),
    },
    "validator-loop": {
        "persona": "validator",
        "telegram_group": "oefr_strategies",
        "task": (
            "Run the Validator Loop — turn the top unvalidated opportunity into a cheapest-possible demand test.\n\n"
            "PATHS (absolute; your cwd is ~/.openclaw/workspace/):\n"
            "  PROJECT  = /home/oghenetejiri/apps/OEFR Digital Products\n"
            "  QUEUE    = $PROJECT/trinity/knowledge/opportunities/queue.md\n"
            "  EDGES    = $PROJECT/trinity/knowledge/edges.md\n"
            "  ROSTER   = $PROJECT/trinity/knowledge/product-roster.md\n"
            "  VALIDATIONS = $PROJECT/trinity/knowledge/validations/\n\n"
            "STEPS:\n"
            "1. Read the queue and find the highest-ranked opportunity with status=candidate:\n"
            "   `cat \"$QUEUE\"`\n"
            "2. Verify it still passes the gates:\n"
            "   `cat \"$EDGES\"` — edge fit?\n"
            "   `cat \"$ROSTER\"` | grep -i '<opportunity subniche>' — already dead?\n"
            "3. If veto: append a row to the queue's Rejected table, signal, done.\n"
            "4. Otherwise, design the rung-1 FREE validation per your persona contract. Produce:\n"
            "   - Gumroad listing copy (title ≤60 chars, subtitle, ~300-word bullet-structured description, price $X, cover image brief)\n"
            "   - Forum post copy (target community + exact title + body; genuinely useful; one tasteful mention of the offer at the end)\n"
            "   - Kill/greenlight thresholds with specific numbers and specific dates (e.g. 'by 2026-04-30')\n"
            "   - Measurement plan (what to count, where, how often)\n"
            "5. Write the full doc to:\n"
            "   $VALIDATIONS/<YYYY-MM-DD>-<opportunity-slug>.md\n"
            "   Use a slug that MATCHES the opportunity queue entry so the two files stay linked.\n"
            "6. Update $QUEUE — change that opportunity's Status to `in_validation` and append a link to the validation doc.\n"
            "7. Signal: `python \"$PROJECT/trinity/knowledge/cli.py\" signal validator-loop '<subniche> → rung-1 live, kill <date>'`\n\n"
            "HARD RULES (from persona):\n"
            "- Never propose paid ads on rung 1. Free first.\n"
            "- Never propose building the product before rung 1 or 2 greenlights.\n"
            "- Specific numbers + dates, not 'soon' / 'some'.\n"
            "- Respect edges.md — veto if a non-edge market snuck through.\n"
            "- No 'transform your life' copy — real pain, real promise, real price.\n\n"
            "Return:\n- Opportunity selected: <subniche>\n- Validation status: designed | rejected\n"
            "- Gumroad URL-ready slug: <slug>\n- Target community: <subreddit/forum>\n- Kill date: YYYY-MM-DD\n- Doc path: <file>"
        ),
    },
    "opportunity-scout": {
        "persona": "opportunity_scout",
        "telegram_group": "oefr_strategies",
        "task": (
            "Run the Opportunity Scout demand-discovery cycle.\n\n"
            "PATHS (use absolute — your cwd is ~/.openclaw/workspace/, not the repo):\n"
            "  PROJECT      = /home/oghenetejiri/apps/OEFR Digital Products\n"
            "  FIRECRAWL    = $PROJECT/trinity/research/firecrawl_cli.py\n"
            "  EDGES        = $PROJECT/trinity/knowledge/edges.md\n"
            "  ROSTER       = $PROJECT/trinity/knowledge/product-roster.md\n"
            "  QUEUE        = $PROJECT/trinity/knowledge/opportunities/queue.md\n\n"
            "STEPS:\n"
            "1. Read your guardrails first:\n"
            "   `cat \"$PROJECT/trinity/knowledge/edges.md\"`\n"
            "   `cat \"$PROJECT/trinity/knowledge/product-roster.md\"`  # know what's already dead\n"
            "   `cat \"$PROJECT/trinity/knowledge/opportunities/queue.md\"`  # avoid re-evaluating same niches\n\n"
            "2. Pick a candidate-subniche set to investigate this run. Rotate across runs — don't only scan the same categories.\n"
            "   Reasonable starting categories (digital products, women-skewed but per edges.md avoid taste/community-driven niches):\n"
            "     - personal finance / budget tools\n"
            "     - home/family organization (excluding wedding-aesthetic)\n"
            "     - small-business templates / SOP packs\n"
            "     - health/wellness trackers (non-personality)\n"
            "     - educational planners / homeschool ops (note: some homeschool subniches ARE community-driven — check edges)\n"
            "     - professional/career adjacent (resume, interview, salary)\n\n"
            "3. For 2-3 chosen subniches, search and scrape demand signal:\n"
            "   `python \"$FIRECRAWL\" search '<niche> bestseller etsy' --limit 5`\n"
            "   `python \"$FIRECRAWL\" search 'site:reddit.com what did you buy <niche>' --limit 5`\n"
            "   `python \"$FIRECRAWL\" scrape 'https://gumroad.com/discover?query=<niche>'`\n"
            "   `python \"$FIRECRAWL\" scrape '<top competitor URL from search>'`\n\n"
            "4. Extract evidence per the persona contract:\n"
            "   - Subniche / specific product type\n"
            "   - ≥3 demand signals with URLs (review counts, search results, recurring asks, competitor sales counts)\n"
            "   - Buyer pain in their own words (quote with URL)\n"
            "   - Price range competitors charge\n"
            "   - Edge fit per edges.md (binary: this market rewards our edges or not)\n\n"
            "5. Apply hard rules — VETO any opportunity that:\n"
            "   - Has fewer than 3 distinct demand signals\n"
            "   - Falls in a non-edge market per edges.md (handmade aesthetic, wedding-taste-driven, instagram-personality, brand-required)\n"
            "   - Was attempted by a now-dead product in the roster\n\n"
            "6. Append 3–5 ranked opportunities to the queue using the template at the top of $QUEUE.\n"
            "   Use today's date in the heading, score each as edge_fit × demand × speed.\n\n"
            "7. Append a row to the Rejected table for any niche you considered and skipped, with reason.\n\n"
            "8. Log: `python \"$PROJECT/trinity/knowledge/cli.py\" signal opportunity-scout '<one-line: N opportunities added, top niche>'`\n\n"
            "Return:\n- Subniches scanned: <list>\n- Opportunities added: N\n- Top opportunity (one line)\n- Rejected this run: M (top reason)"
        ),
    },
    "heartbeat": {
        "persona": "heartbeat",
        "telegram_group": None,           # silent — dispatched cycle reports
        "model": "claude-sonnet-4-6",     # Sonnet for cheap routing/triage
        "task": (
            "Run the Trinity Heartbeat triage scan.\n\n"
            "PATHS (use absolute — your cwd is ~/.openclaw/workspace/, not the products repo):\n"
            "  PROJECT  = /home/oghenetejiri/apps/OEFR Digital Products\n"
            "  CRON     = $PROJECT/trinity/cron_runner.py\n"
            "  CLI      = $PROJECT/trinity/knowledge/cli.py\n"
            "  HBLOG    = $PROJECT/trinity/knowledge/heartbeat-log.md\n"
            "  REPORTS  = ~/.openclaw/workspace/reports\n"
            "  CHATHIST = $PROJECT/trinity/chat-history\n\n"
            "STEPS:\n"
            "1. Read today's cross-cycle signals:\n"
            "   `python \"$PROJECT/trinity/knowledge/cli.py\" signals`\n"
            "2. Read the briefing:\n"
            "   `python \"$PROJECT/trinity/knowledge/cli.py\" briefing`\n"
            "3. List the most recent agent reports (last 10 by mtime):\n"
            "   `ls -lt ~/.openclaw/workspace/reports/ | head -10`\n"
            "4. Check your heartbeat history to avoid duplicate dispatches in a short window:\n"
            "   `tail -40 \"$PROJECT/trinity/knowledge/heartbeat-log.md\"`\n"
            "5. (Only if signals are unclear) skim TJ's recent chat:\n"
            "   `ls -lt \"$PROJECT/trinity/chat-history/\" | head -3`\n"
            "6. DECIDE per the hard rules in your persona:\n"
            "   - Default: do nothing.\n"
            "   - Dispatch only on a clear, time-sensitive trigger.\n"
            "   - Never re-dispatch a cycle that ran in the last hour.\n"
            "7. If you decide to dispatch, run it as a subprocess from the project dir:\n"
            "   `cd \"$PROJECT\" && /home/oghenetejiri/venvs/oefr/bin/python trinity/cron_runner.py <cycle>`\n"
            "   The dispatched cycle handles its own Telegram reporting; you stay silent.\n"
            "8. **MANDATORY** — append your scan as a single block to the heartbeat log. This is not optional:\n"
            "   `cat >> \"$PROJECT/trinity/knowledge/heartbeat-log.md\" <<'EOF'\n"
            "   ## [YYYY-MM-DD HH:MM] heartbeat\n"
            "   Scanned: <items>\n"
            "   Findings: <key signals or 'nothing urgent'>\n"
            "   Action: <cycle dispatched, or 'none'>\n"
            "   Reasoning: <one line>\n"
            "   EOF`\n"
            "   Replace YYYY-MM-DD HH:MM with the actual current timestamp.\n"
            "9. Return the same block as your output (single, concise)."
        ),
    },
    "neo-weekly": {
        "persona": "neo",
        "telegram_group": "oefr_strategies",
        "task": (
            "Run the Weekly Architecture & Security Sweep for OEFR Digital.\n\n"
            "KNOWLEDGE CLI:\n"
            "  python trinity/knowledge/cli.py query <topic>\n"
            "  python trinity/knowledge/cli.py log-issue <product> '<desc>' --status open\n"
            "  python trinity/knowledge/cli.py log-audit neo-weekly <product> '<findings>' '<actions>'\n"
            "  python trinity/knowledge/cli.py log-lesson '<lesson>' '<context>' --category process\n"
            "  python trinity/knowledge/cli.py signal neo-weekly '<key finding>'\n\n"
            "STEPS:\n"
            "1. Read all reports/neo-daily-* from the last 7 days (in ~/.openclaw/workspace/reports/).\n"
            "2. Identify recurring patterns across daily reports:\n"
            "   - Same issue across multiple products?\n"
            "   - Same class of risk repeating?\n"
            "   - Workflows that keep almost-failing?\n"
            "3. Architecture review of the active surface (use the Product Roster in your wiki context — skip dead products):\n"
            "   - Inspect cron jobs that take external actions\n"
            "   - Inspect browser automation workflows that touch live business ops\n"
            "   - Inspect auth/payment boundaries across active products\n"
            "   - Inspect skills affecting company-critical workflows\n"
            "   - Inspect Trinity's own infrastructure (rules layer, governance gate, signal store)\n"
            "4. Update product-roster.md Notes column for products with hardening priority — append e.g. 'Neo P1: <issue>' to their notes.\n"
            "5. Log recurring patterns as lessons: python trinity/knowledge/cli.py log-lesson '<pattern>' '<context>' --category process\n"
            "6. Write the weekly report to ~/.openclaw/workspace/reports/neo-weekly-YYYY-MM-DD.md\n"
            "   Format: recurring weak patterns, security concerns, architecture risks, quality debt, severity (P0-P3), exact recommended fixes, hardening agenda for next week.\n"
            "7. Signal: python trinity/knowledge/cli.py signal neo-weekly '<one-line summary>'\n\n"
            "Output: structured operator report. Severity labels mandatory. Exact fixes preferred over vague recommendations.\n\n"
            "Return:\n- Patterns identified\n- Top hardening priorities (P0-P3)\n- Recommended fixes\n- Hardening backlog for next week"
        ),
    },
}

# Append the issue-format instruction to all second brain cycles
for name, spec in CYCLE_PROMPTS.items():
    if spec.get("persona") in SIGNALING_PERSONAS:
        spec["task"] += _ISSUE_INSTRUCTION


def _run_lifecycle_loop():
    """Deterministic cycle — customer lifecycle emails via Resend.

    Polls Stripe for completed Checkout Sessions on known Payment Links,
    enrols new customers into the pre_order_welcome sequence, and sends
    any due steps. Reports to oefr_strategies; forwards failures to blockers.
    """
    print("[Trinity] Starting lifecycle-loop cycle...")
    from lifecycle.runner import run as lifecycle_run

    report = lifecycle_run()
    text = report.as_text()
    print("\n" + text + "\n")

    send_telegram(text[:3900], "oefr_strategies")

    if report.failures:
        msg = "[lifecycle-loop] " + "\n".join(report.failures)
        send_telegram(msg[:3800], "blockers")

    if report.new_customers or report.emails_sent:
        summary = (
            f"lifecycle-loop: {report.new_customers} new customers, "
            f"{report.emails_sent} emails sent, {report.emails_failed} failed"
        )
        add_signal("lifecycle-loop", summary)
        generate_briefing()

    print("[Trinity] lifecycle-loop cycle complete.")


def _run_sensor_loop():
    """Deterministic cycle — runs all sensors, writes signals to SQLite store.

    Each sensor is best-effort: one failure does not block others.
    Aggregates results and posts a compact summary to apps_forging.
    Forwards any P0 conditions (Stripe failure, all sessions dead) to blockers.
    """
    print("[Trinity] Starting sensor-loop cycle...")
    from sensors import init_db
    from sensors.stripe_sensor import run as stripe_run
    from sensors.etsy_sensor import run as etsy_run
    from sensors.x_sensor import run as x_run

    init_db()

    results = {}
    for name, fn in (("stripe", stripe_run), ("etsy", etsy_run), ("x", x_run)):
        try:
            results[name] = fn()
        except Exception as e:
            results[name] = {
                "status": "crashed",
                "rows_written": 0,
                "error": f"{type(e).__name__}: {e}",
                "summary": f"{name} sensor crashed",
            }

    lines = ["# Sensor Loop Report", f"Date: {dt.datetime.now().isoformat(timespec='seconds')}", ""]
    total_rows = 0
    blockers: list[str] = []
    for name, r in results.items():
        total_rows += r.get("rows_written", 0)
        status = r.get("status", "?")
        summary = r.get("summary", "")
        lines.append(f"- **{name}** [{status}] — {summary}")
        if status in ("failed", "crashed") and name == "stripe":
            blockers.append(f"Stripe sensor {status}: {r.get('error', '')}")
    lines.append("")
    lines.append(f"Total signals written: {total_rows}")
    text = "\n".join(lines)
    print("\n" + text + "\n")

    send_telegram(text[:3900], "oefr_strategies")

    if blockers:
        send_telegram("[sensor-loop] " + "\n".join(blockers)[:3800], "blockers")

    add_signal("sensor-loop", f"sensor-loop: {total_rows} signals across {len(results)} sensors")
    generate_briefing()
    print("[Trinity] sensor-loop cycle complete.")


def _run_funnel_verifier():
    """Deterministic cycle — walks every revenue surface end-to-end.

    Landing pages, Gumroad product pages, Stripe payment links, webhook
    endpoint ownership/health, fulfillment gates. Any failure is a
    direct sales blocker and goes straight to the blockers group.
    """
    print("[Trinity] Starting funnel-verifier cycle...")
    from verifier import run as verifier_run

    report = verifier_run()
    passed = sum(1 for r in report.results if r.ok)
    summary = f"funnel-verifier: {passed}/{len(report.results)} revenue-surface checks passed"
    print(f"[Trinity] {summary}")

    if report.failures:
        lines = [f"[funnel-verifier] {len(report.failures)} BROKEN revenue surfaces:"]
        for f in report.failures:
            lines.append(f"- [{f.name}] {f.check} — {f.detail}")
        send_telegram("\n".join(lines)[:3900], "blockers")

    add_signal("funnel-verifier", summary + (
        f"; FAILURES: {', '.join(f.name + ':' + f.check for f in report.failures)[:400]}"
        if report.failures else ""))
    generate_briefing()
    print("[Trinity] funnel-verifier cycle complete.")


def _run_killer_loop():
    """Deterministic cycle — applies kill rules to the product roster.

    No LLM. Reads product-roster.md, transitions statuses, writes back,
    appends post-mortems, sends a structured report to Telegram.
    """
    print("[Trinity] Starting killer-loop cycle...")
    report = apply_kill_rules()
    text = report.as_text()
    print("\n" + text + "\n")

    # Portfolio lifecycle decisions belong with strategy reports.
    send_telegram(text[:3900], "oefr_strategies")

    # If anything died, surface to Blockers so TJ sees it.
    deaths = [a for a in report.actions if a.to_status == "dead"]
    if deaths:
        msg = "[killer-loop] Products moved to dead:\n\n" + "\n".join(
            f"- {a.product}: {a.reason}" for a in deaths
        )
        send_telegram(msg[:3800], "blockers")

    # Log a cross-cycle signal so opportunity-scout (Phase 2) can react.
    if report.actions:
        summary = (
            f"killer-loop: {len(report.actions)} transitions, "
            f"portfolio {report.portfolio_size_before} → {report.portfolio_size_after}"
        )
        add_signal("killer-loop", summary)
        generate_briefing()

    print("[Trinity] killer-loop cycle complete.")


def _governance_gate(cycle: str, task: str, persona, result: str) -> str:
    """Check LLM output against governance rules; retry once if it fails.

    Phase 0 enforcement: rejects networking-niche proposals lacking
    signal evidence; rejects non-edge market proposals. The agent loop
    cannot rationalize past these checks because they run as code.

    Returns the final (possibly retried) result.
    """
    if cycle not in GOVERNED_CYCLES:
        return result

    check = check_llm_output(result, cycle=cycle)
    if check.passed:
        return result

    print(f"\n[Trinity] Governance rejected output for {cycle}:")
    print(check.as_text())
    print("[Trinity] Retrying with stronger constraint...")

    retry_task = task + retry_instruction(check, cycle)
    retry_result = run_agent(
        task=retry_task,
        persona=persona,
        max_turns=20,
        print_output=True,
    )

    # Re-check the retry. If still failing, surface to Blockers but return
    # the retry output (better than nothing for downstream consumers).
    final_check = check_llm_output(retry_result or "", cycle=cycle)
    if not final_check.passed:
        msg = (
            f"[{cycle}] Governance rejected output twice — TJ review needed:\n\n"
            f"{final_check.as_text()}\n\n"
            f"Last output (truncated):\n{(retry_result or '')[:1500]}"
        )
        send_telegram(msg[:3800], "blockers")
        print("[Trinity] Governance retry also failed; flagged to blockers.")

    return retry_result or result


def main():
    if len(sys.argv) < 2:
        all_cycles = sorted(set(CYCLE_PROMPTS.keys()) | DETERMINISTIC_CYCLES)
        print(f"Usage: {sys.argv[0]} <{'|'.join(all_cycles)}>")
        sys.exit(1)

    cycle = sys.argv[1]

    # Deterministic dispatch (pure Python, no LLM).
    if cycle in DETERMINISTIC_CYCLES:
        if cycle == "killer-loop":
            _run_killer_loop()
            return
        if cycle == "sensor-loop":
            _run_sensor_loop()
            return
        if cycle == "lifecycle-loop":
            _run_lifecycle_loop()
            return
        if cycle == "funnel-verifier":
            _run_funnel_verifier()
            return
        print(f"Unknown deterministic cycle: {cycle}")
        sys.exit(1)

    if cycle not in CYCLE_PROMPTS:
        all_cycles = sorted(set(CYCLE_PROMPTS.keys()) | DETERMINISTIC_CYCLES)
        print(f"Usage: {sys.argv[0]} <{'|'.join(all_cycles)}>")
        sys.exit(1)

    spec = CYCLE_PROMPTS[cycle]

    print(f"[Trinity] Starting {cycle} cycle...")

    # For second brain cycles, inject targeted wiki context into the task
    task = spec["task"]
    if spec.get("persona") in SIGNALING_PERSONAS:
        wiki_context = load_for_cycle(cycle)
        if wiki_context:
            task = (
                f"# Wiki Context (auto-loaded for this cycle)\n"
                f"{wiki_context}\n\n"
                f"# Task\n{task}"
            )

    result = run_agent(
        task=task,
        persona=spec["persona"],
        max_turns=20,
        print_output=True,
        model=spec.get("model"),  # None → CLI default; cycles can request Sonnet
    )

    # SDK failure sentinel — run_agent_sdk returns its error message string when
    # the underlying claude CLI subprocess dies (e.g. "Fatal error in message reader"
    # SSE close-path bug observed since 2026-04-19). Treating that string as a real
    # report pollutes Telegram, signal store, briefing, and the next cycle's context.
    # See ~/.openclaw/workspace/memory/self-improvement.md (2026-05-11 entry).
    SDK_FAILURE_PREFIXES = (
        "Error running Claude SDK",
        "Claude SDK timed out",
    )
    sdk_failed = bool(result) and any(
        result.lstrip().startswith(p) for p in SDK_FAILURE_PREFIXES
    )
    if sdk_failed:
        print(f"[Trinity] SDK failure detected — skipping dispatch / signal / "
              f"briefing for {cycle}: {result[:200]}", file=sys.stderr, flush=True)
        # Single Blockers ping per failure so the cron outage is visible without
        # poisoning the cycle's primary group or the knowledge base.
        try:
            send_telegram(
                f"[{cycle}] SDK failure — cycle aborted, no signal/briefing written.\n"
                f"{result[:1500]}",
                "blockers",
            )
        except Exception as send_err:
            print(f"[Trinity] Could not notify blockers: {send_err}",
                  file=sys.stderr, flush=True)
        print(f"[Trinity] {cycle} cycle aborted (SDK failure).")
        sys.exit(1)

    # Governance gate: rejects TJ-default niche proposals without signal evidence.
    # Pure Python — agent loop cannot rationalize past it.
    if result:
        result = _governance_gate(cycle, task, spec["persona"], result)

    # Silent cycles (telegram_group=None) suppress ALL Telegram dispatch —
    # including the issue-to-blockers forwarding. The dispatched cycle (e.g.
    # spawned by heartbeat) is responsible for its own reporting.
    silent = spec["telegram_group"] is None

    # Deliver full report to the cycle's designated group
    if result and spec["telegram_group"]:
        summary = result[:3900]
        send_telegram(summary, spec["telegram_group"])
        print(f"\n[Trinity] Delivered to {spec['telegram_group']}")

    # Forward issues to Blockers (separate from the main report) — skipped when silent.
    if result and not silent:
        issues = _extract_issues(result)
        if issues:
            header = f"[{cycle}] Issues requiring attention:\n\n"
            send_telegram(header + issues[:3800], "blockers")
            print(f"[Trinity] Issues forwarded to blockers")

    # Post-cycle: log a signal and refresh the briefing
    if result and spec.get("persona") in SIGNALING_PERSONAS:
        # Extract a one-line summary as a signal for other cycles
        first_meaningful = ""
        for line in result.splitlines():
            stripped = line.strip().lstrip("- ")
            if stripped and len(stripped) > 10 and not stripped.startswith("#"):
                first_meaningful = stripped[:200]
                break
        if first_meaningful:
            add_signal(cycle, first_meaningful)

        # Regenerate briefing so the next cycle sees updated state
        generate_briefing()
        print(f"[Trinity] Briefing regenerated, signal logged")

    print(f"[Trinity] {cycle} cycle complete.")


if __name__ == "__main__":
    main()
