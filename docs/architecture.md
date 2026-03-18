# Architecture

## Infrastructure

```
┌─────────────────────────────────────────────┐
│                  OEFR Digital                │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ NetArch  │  │  Budget   │  │ Invoice  │  │
│  │   Pro    │  │  Wise     │  │  Flow    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │              │              │        │
│  ┌────┴──────────────┴──────────────┴────┐  │
│  │            Vercel (Hosting)           │  │
│  └────┬──────────────┬──────────────┬────┘  │
│       │              │              │        │
│  ┌────┴────┐   ┌─────┴─────┐  ┌────┴────┐  │
│  │ Stripe  │   │  Gumroad  │  │ Vercel  │  │
│  │Payments │   │ Downloads │  │   DNS   │  │
│  └─────────┘   └───────────┘  └─────────┘  │
└─────────────────────────────────────────────┘
```

## Hosting
- **Platform:** Vercel (free tier)
- **Framework:** Next.js (all apps)
- **Domain:** oefrenterprise.com (Vercel nameservers)
- **Email:** Google Workspace (MX records preserved in Vercel DNS)

## Payments
- **Stripe:** Live keys, account `acct_1TAM8w3H4Cmk8ulC`
- **Gumroad:** All 14+ products listed, handles own payouts

## Data Strategy
- **Client-side first:** localStorage for all web apps (zero backend costs)
- **No databases** for consumer apps — keeps hosting free
- **PWA support** on VaultPass, HabitForge (offline-capable)

## AI Operations (OpenClaw)
- **Host:** eve-ng (Ubuntu Linux)
- **Trinity (CEO):** Claude Opus 4.6 — strategy, orchestration, marketing
- **Neo (CTO/CSO):** Claude Sonnet 4.6 — security, code review, architecture
- **Dev Agents:** Claude Sonnet 4.6 — on-demand subagents for building
- **Cron Jobs:**
  - Job Scout: 8 AM ET M-F
  - Nightly Review: 3 AM ET daily
  - Heartbeat: periodic checks

## Deployment Flow
1. Code built by subagent (Claude Sonnet)
2. Trinity reviews / Neo security audits
3. `vercel --prod` deploys to production
4. Stripe keys set via `vercel env add`
5. DNS verified, SSL auto-provisioned
