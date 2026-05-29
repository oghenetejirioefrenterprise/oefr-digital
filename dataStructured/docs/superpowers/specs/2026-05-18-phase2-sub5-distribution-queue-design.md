# Phase 2 sub-project 5 — distribution queue consumer (CEO manual path)

**Status:** Approved 2026-05-18 (delegated).
**PRD scope:** *"Distribution queue consumer (early — CEO posts to one channel manually as preparation for `marketing-lead` in phase 3)"*

---

## Current state (precedes PRD scope)

The v1 build already shipped substantial distribution infrastructure that **exceeds** the PRD's Phase 2 sub-project 5 scope:

- `state/distribution-queue.json` — items added by CEO/engineer post-ship
- `state/distribution-log.json` — per-(item, channel) posting record
- `state/distribution-report-{date}.md` — daily summaries
- `.trinity/employees/distribution-agent/identity.md` — full multi-channel posting agent
- `scripts/social_helpers.py` — Reddit + X + LinkedIn via browser-use automation
- 21:00 ET scheduler cycle posts unposted items automatically

The PRD asks for LESS than this: a single channel, manually CEO-driven. Reality went further during v1.

## Therefore, Phase 2 sub-project 5 deliverable is small

Add a **founder-review-before-post manual path** the CEO can invoke when an item warrants extra care (e.g., first post to a new channel, post that might step on community norms). This sits ALONGSIDE the existing automated distribution-agent — it doesn't replace it.

## Architecture

**New script:** `scripts/distribution_draft.py`

CLI:
```
python scripts/distribution_draft.py --item-id <id> --channel <reddit|twitter|linkedin> [--send-for-approval]
```

What it does:
1. Reads the item from `state/distribution-queue.json` by id
2. Generates a channel-appropriate draft (Reddit: title + body; X: thread; LinkedIn: text). Reuses templating logic from existing distribution-agent prompts.
3. Prints the draft to stdout.
4. If `--send-for-approval` is set: sends the draft to the founder via Telegram DM (using existing trinity Telegram API) with a "approve to post / decline" prompt.
5. Logs intent (not post) to `state/distribution-drafts/{item-id}-{channel}-{timestamp}.json`.

**No new scheduler cycle.** CEO invokes this on-demand from the 19:00 cycle when a manual-review flow is needed. Default flow stays automatic via distribution-agent.

**No new employee.** The CEO already has Bash tool access; this is just a new script in their toolbox.

## CEO identity update

Append a short section under "Common commands" or near the end of CEO identity:

```markdown
## Manual distribution path (for high-stakes posts)

For an item that should NOT auto-post (e.g., first post to a new community, sensitive niche, founder wants final say):

```bash
# Generate a draft + send to founder for approval via Telegram
python scripts/distribution_draft.py --item-id <id> --channel <reddit|twitter|linkedin> --send-for-approval
```

Founder approves via Telegram reply. After approval, distribution-agent's normal cycle posts it.

For routine items, do nothing — the 21:00 cycle handles them automatically.
```

## Approval mechanism

For v1 simplicity: `--send-for-approval` writes the draft as a "pending approval" entry to `state/distribution-drafts/`. The founder reads via Telegram DM and manually replies "approve <draft-id>" or "decline <draft-id>". A future enhancement can wire this through to auto-post on approval; v1 just surfaces the draft.

No webhook; uses existing trinity Telegram API to send the DM.

## What's NOT in this sub-project

- Auto-post on Telegram approval reply (manual for v1; CEO triggers post after founder OK)
- Multi-channel orchestration in the draft (one channel per draft script invocation)
- A/B testing variants of post copy
- Engagement tracking on posted items (Phase 3 marketing-lead)
- Replacing or restricting the existing distribution-agent's automated flow

## Tasks

1. Create `scripts/distribution_draft.py`. Should be ~80 lines: parse args, load queue item, generate draft (use Anthropic SDK with a simple prompt that takes the item + channel), optionally Telegram-send via existing helper. Reuse trinity's existing Telegram API helper from `trinity-agent` (import `trinity.telegram.api.TelegramAPI`).
2. Create `state/distribution-drafts/.gitkeep` so the directory exists in the repo.
3. Append "Manual distribution path" section to `.trinity/employees/ceo/identity.md`.
4. Smoke test: run the script with `--item-id new-fmcsa-carrier-leads-2026-05-2026-05-04 --channel twitter` (no `--send-for-approval`). Verify it prints a draft, exits 0.
5. Commit.

No daemon restart needed — no new cycle, no new employee.
