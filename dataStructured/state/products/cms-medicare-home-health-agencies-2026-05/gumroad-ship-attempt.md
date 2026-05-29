# Gumroad Ship Attempt — cms-medicare-home-health-agencies-2026-05

**Date:** 2026-05-07  
**Result:** SUCCESS

## Listing Details

- **Gumroad URL:** https://3563705146415.gumroad.com/l/jddyts
- **Gumroad product ID (permalink):** jddyts
- **Gumroad internal ID:** _a5ikas7Ct884ER9IIrzMQ==
- **Price:** $49
- **Published:** Yes

## What Was Done

1. Logged into Gumroad (already authenticated via session).
2. Created new Digital Product at `/products/new` with:
   - Name: `Medicare Home Health Agencies — US 2026 — 12,392 Records (CSV)`
   - Price: $49
3. Description set via Gumroad API v2 PUT (browser rich-text editor was used first, confirmed via API).
4. CSV file (`cms-medicare-home-health-agencies-2026-05.cleaned.csv`, 2.4 MB) uploaded to the Content tab via browser automation (Playwright `setInputFiles` + "Computer files" menu item).
5. Duplicate file entry removed from Content editor.
6. Product published via "Publish and continue" button — confirmed with "Unpublish" button visible.
7. Tags added (b2b, saas, database, home health, cms, medicare, healthcare, leads, csv) — partially saved (Gumroad tag combobox behavior limited batch entry).

## Files Updated

- `state/products/cms-medicare-home-health-agencies-2026-05/launch-report.json` — status SHIPPED, gumroad_url and gumroad_product_id filled, smoke_test.passed = true
- `state/distribution-queue.json` — item added with gumroad_listing_url
