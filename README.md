# ~/apps

**This directory is not a git repository.** It is a plain folder holding
independent projects, each with its own git repo and history.

That changed on **2026-07-25**. Until then `~/apps` was itself a git repo — the
public `oefr-digital` monorepo — which tracked 14 top-level paths while 37 other
projects underneath kept separate repos of their own. The two schemes overlapped
and, for `options-agent`, actively conflicted: two repos believed they owned the
same 40 files.

The company README that used to live here is now
[`docs/README.md`](docs/README.md), with the other company documentation.

## Current structure

**48 standalone git repos** directly under `~/apps/`. Twelve were extracted from
the old monorepo on 2026-07-25, each with its history preserved via
`git subtree split` (eleven remain — see `oefr-digital` below):

| Project | Commits | Notes |
|---|---|---|
| `oefr-website` | 62 | storefront; 47 previously-unversioned source files committed |
| `trinity-agent` | 31 | 151 tests pass |
| `crypto` | 29 | `.gitignore` added — it had none, and `.env` holds live keys |
| `options-agent` | 24 | double-tracking resolved; prior 73-commit repo archived |
| `OEFR Digital Products` | 22 | 12 nested product repos gitignored |
| `auto-research-trader` | 8 | |
| `tek-proposal` | 5 | |
| `dataStructured` | 4 | 91 tests pass; ops belong to Trinity/Ralph |
| `docs` | 1 | company-level strategy docs |
| `journal` | 1 | |
| `auto-research-trader-v3` | 1 | |

`cycle-trader` (69 commits) was extracted separately earlier the same day.

**No extracted repo has a remote.** Nothing is pushed anywhere unless TJ asks.

## Where to commit

Commit **inside the project directory**. There is no repo at this level any more,
so a `git commit` run from `~/apps` fails rather than silently sweeping up
another project's work. That is the point.

## The old monorepo history

Archived, not deleted:

```bash
git --git-dir=~/repo-archives/apps-monorepo-dotgit-2026-07-25 log --oneline
```

- `~/repo-archives/apps-monorepo-dotgit-2026-07-25/` — the full 259-commit `.git`
- `~/repo-archives/apps-monorepo-MANIFEST.txt` — every commit
- `~/repo-archives/apps-monorepo-EXTRACTION-COMMITS.txt` — the 13 extraction commits

Those 13 commits were **not pushed**. `origin/master` on GitHub still sits 13
commits behind, showing the pre-split state. Pushing is outward-facing and was
left as TJ's call.

## Decisions TJ made on 2026-07-25

- **`oefr-digital` was removed.** It was a stale 2026-03-18 snapshot of 8
  `oefr-website` files (5 of which had since diverged, with `oefr-website`
  holding the newer versions), had no `package.json` and could not build.
  Moved to `~/repo-archives/oefr-digital-stale-duplicate-2026-07-25/` rather
  than deleted outright, so it is recoverable. Nothing referenced its path — no
  cron entry, no script, no `.vercel` link. `oefr-website` builds clean without it.
- **`crypto/auto-research-trader-v3` (632 files) and
  `crypto/auto-research-trader` (3,156 files) stay unversioned, deliberately.**
  TJ's call: still useful, but not worth tracking. They are gitignored inside
  `crypto/` so they can never be swept into that repo by accident. Being outside
  git, they have **no history and no recovery path** — back them up by copying,
  not by committing.
- **The 13 extraction commits were pushed** to `origin/master`. The public repo
  now reflects the split rather than the pre-split monorepo.
- The Etsy password in the public history is **accepted as-is** — the `.profile`
  value stays current. No rotation.

## ⚠️ Still unversioned

These directories have no git repo at all, some of them large:
`hyper-grok-dashboard` (121k files), `email-webhook` (29k), `email-signature`
(21k), `browser-use-mcp-server` (18k), `interview` (10k),
`SMB_youtube_transcripts`, `tiktok-marketing`, `scroll-site-test`,
`eckrown_youtube_transcripts`, `images_openai`, `interview-prep`,
`tradingview-scripts`. They were outside this migration's scope.

`.gitignore` at this level is now inert — nothing reads it. Kept only in case
this directory is ever re-initialised as a repo.
