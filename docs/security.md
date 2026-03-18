# Security

## CTO/CSO: Neo
All security audits and sign-offs handled by Neo (Claude Sonnet 4.6).

## Audit History

### March 17, 2026 — P0 Fixes Deployed
All 5 critical vulnerabilities patched:
1. **NetArch Pro** — Private downloads + APP_URL protection (was: public download URLs)
2. **OEFR Digital** — Fake review injection removed (was: client-side review submission)
3. **InvoiceFlow** — Dev bypass removed (was: debug flag skipped payment check)
4. **BudgetWise** — Payment verification hardened
5. **HabitForge** — Payment verification hardened

### March 18, 2026 — Neo's First Full Audit
4 P0 critical findings:
1. **GCP key on disk** (careerAI) — service account key file in repo
2. **Mass credential exposure** (careerAI) — .env with secrets committed
3. **Hyperliquid private key** — plaintext in .env (hyper-grok-dashboard)
4. **Unauthenticated admin endpoints** (careerAI) — DB admin routes with no auth

**Status:** Remediation pending

## Security Rules
- Neo signs off before any product ships
- No secrets in repos or client-side code
- Payment verification server-side only (never trust URL params)
- All download URLs require Stripe session verification
- localStorage apps: no sensitive data stored client-side
