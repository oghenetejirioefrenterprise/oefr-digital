# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A **documents-only** proposal package for the TEK client engagement (TEK — Tasty E-Kitchen Ltd, London, tekvers.ai): a product spec/PRD for the "TEK Restaurant Intelligence Platform" plus two pro-forma invoices. There is no application code, build system, or test suite here. This directory is a subdirectory of the `~/apps` git repo, not its own repo.

**Engagement status:** Spec v1.0 and quotes delivered 2026-07-16. No platform build work happens in (or from) this directory until TEK confirms a track and pays a deposit — changes here are document revisions only.

## Document Pipeline

Each deliverable exists in up to three synchronized forms; the **markdown spec is the source of truth** for content:

1. `docs/2026-07-16-tek-intelligence-platform-spec.md` — spec/PRD content (source of truth)
2. `docs/spec.html` + `docs/invoice-OEFR-PF-2026-*.html` — hand-styled print layouts (A4, inline CSS, `@page` rules). Invoices exist only as HTML/PDF; there is no invoice markdown.
3. `docs/*.pdf` — generated from the HTML via headless Chrome

**Current documents (spec v2.0, 2026-07-19):** the active quotation is `invoice-OEFR-PF-2026-003-all-inclusive.html` / `OEFR-PF-2026-003-Invoice-All-Inclusive.pdf` (£18,799 all-inclusive, negotiated face-to-face with TEK; supersedes PF-2026-001/-002, which stay in the repo as history). Spec PDF is `TEK-Intelligence-Platform-Spec-PRD-v2.0.pdf` (v1.0 PDF kept as history).

**When editing content, update all forms:** edit the `.md`, mirror the change into the corresponding `.html`, then regenerate the PDF:

```bash
google-chrome --headless --no-sandbox --print-to-pdf="docs/TEK-Intelligence-Platform-Spec-PRD-v2.0.pdf" --no-pdf-header-footer docs/spec.html
google-chrome --headless --no-sandbox --print-to-pdf="docs/OEFR-PF-2026-003-Invoice-All-Inclusive.pdf" --no-pdf-header-footer docs/invoice-OEFR-PF-2026-003-all-inclusive.html
```

## Conventions That Must Hold

- **Company name on client-facing documents is "OEFR Enterprise Inc"** (never "OEFR Digital"). Contact email: `info@oefrenterprise.com`. Domain: oefrenterprise.com.
- **Invoices are standalone documents:** no "Track A / Track B" or "Option A / Option B" labels, and no cross-references to the other quotation number. Each invoice must fit on **one A4 page** — after any edit, regenerate the PDF and confirm `pdfinfo` reports 1 page.
- **Single agreed engagement (v2.0):** £18,799 all-inclusive for Phases 1–5 (core platform + POS integrations + TEK Guest mobile app), fixed per phase in GBP, defined in Section 12 of the spec. This price was **negotiated face-to-face between TJ and TEK** — it is an agreed close, not a discount; do not reframe it as one. A price change must be reflected in the spec md, spec HTML/PDF, and the invoice HTML/PDF together.
- **Never discount** — pricing changes add value (scope, warranty, SLA), they don't cut price. (Negotiated closes agreed by TJ in person are TJ's call, not discounts.)
- Commit messages for this directory use the `proposal(tek): ...` prefix.
- HTML files are designed for print: keep `@page { size: A4 }`, `break-inside`/`break-after` rules, and `print-color-adjust: exact` intact when editing, and check the regenerated PDF for broken page breaks.
