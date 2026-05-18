# DataStructured Phase 2 — Subdomain Storefront Design

**Status:** Approved 2026-05-18.
**Parent PRD:** [`docs/PRD.md`](../../PRD.md) — Phase 2 scope item: *"Custom subdomain storefront (Next.js page per product) on a chosen subdomain (e.g. `data.<owned-domain>`); engineer publishes to subdomain alongside Stripe + Gumroad."*
**Sub-project sequence:** Storefront is sub-project 1 of 5 in Phase 2. Subsequent: product-manager agent → recurring billing → customer-success → distribution-queue consumer.

---

## Goal

Stand up a public storefront at `data.oefrenterprise.com` that renders one page per shipped DataStructured product, with checkout CTAs to existing Stripe Payment Links and Gumroad listings. The engineer agent's workflow gains one step (`git push` after writing launch-report); new products appear on the site within ~3–5 minutes of push via Vercel auto-deploy.

This is sub-project 1 of Phase 2 (5 components). It must ship on its own before the next sub-project starts. The 14-day Phase 1 autonomy gate is administratively closed (no buyer contact occurred during the 4-day daemon outage 2026-05-11 → 05-15, so the missing daily DMs are immaterial). The trinity-agent watchdog bug that caused the outage was fixed in commit `3ab49e0`.

---

## Why subdomain, not subpath under oefr-website

The PRD's hard rule #6 is *"Folder-scoped. No agent here references projects outside `~/apps/dataStructured/`."* A subpath under `oefr-website` would force cross-project file references and couple two distinct lines of business. The subdomain keeps DataStructured artifacts entirely inside its own folder and matches the PRD's explicit `data.<owned-domain>` example.

---

## Architecture

**Tech stack:**
- Next.js 14 (App Router) with TypeScript
- Tailwind CSS
- Vercel deployment with custom subdomain `data.oefrenterprise.com`
- No database — all data sourced from filesystem reads of sibling `state/` directory

**Project location:** `~/apps/dataStructured/site/`

**Folder layout:**
```
~/apps/dataStructured/site/
├── app/
│   ├── layout.tsx              # Root layout, fonts, metadata
│   ├── page.tsx                # Homepage: hero + product grid
│   ├── products/
│   │   └── [slug]/
│   │       └── page.tsx        # Per-product detail page
│   ├── about/
│   │   └── page.tsx            # Brief story page
│   ├── robots.txt/
│   │   └── route.ts            # Static robots.txt
│   └── sitemap.ts              # Dynamic sitemap from product list
├── components/
│   ├── ProductCard.tsx         # Homepage grid item
│   ├── ProductHero.tsx         # Detail page hero
│   ├── BonusStack.tsx          # Bullet list of bonuses
│   └── CheckoutCTAs.tsx        # Stripe + Gumroad buttons
├── lib/
│   ├── products.ts             # listProducts() / getProduct(slug) reading state/
│   └── types.ts                # ProductSpec, LaunchReport TypeScript types
├── public/
│   ├── og-default.png          # Default Open Graph image
│   └── favicon.ico
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.mjs
└── vercel.json                 # includeFiles for state/products/
```

---

## Data flow

Server components read product data from the bundled `state/products/` directory at request time. Pages are statically generated for known shipped products via `generateStaticParams`; new product slugs come online with the next deploy. No external data store — the filesystem is the source of truth.

The original design considered ISR (60s revalidate) for "auto-discovery" of new products, but on Vercel the deployed bundle is immutable — re-running the server component reads the same files. So ISR adds no value over SSG here. The actual refresh mechanism is **redeploy-on-push**: engineer agent commits the new `spec.json` + `launch-report.json`, pushes, Vercel auto-deploys, new product page goes live ~3–5 minutes later (Vercel build time).

**Reading logic (`lib/products.ts`):**

```typescript
import { readFile, readdir } from "fs/promises";
import path from "path";

const STATE_DIR = path.join(process.cwd(), "..", "state", "products");

export async function listProducts(): Promise<Product[]> {
  const dirs = await readdir(STATE_DIR, { withFileTypes: true });
  const products: Product[] = [];
  for (const dir of dirs) {
    if (!dir.isDirectory()) continue;
    const product = await tryLoadProduct(dir.name);
    if (product) products.push(product);
  }
  return products.sort((a, b) => b.spec.created.localeCompare(a.spec.created));
}

async function tryLoadProduct(slug: string): Promise<Product | null> {
  const specPath = path.join(STATE_DIR, slug, "spec.json");
  const launchPath = path.join(STATE_DIR, slug, "launch-report.json");
  try {
    const spec: ProductSpec = JSON.parse(await readFile(specPath, "utf8"));
    const launch: LaunchReport = JSON.parse(await readFile(launchPath, "utf8"));
    if (launch.status !== "FULLY_SHIPPED") return null;
    if (spec.compliance_verdict !== "PASS") return null;
    return { slug, spec, launch };
  } catch {
    return null;
  }
}
```

**Filter rules — products only render if BOTH:**
1. `launch-report.json` exists and `status === "FULLY_SHIPPED"`
2. `spec.json` exists and `compliance_verdict === "PASS"`

This guarantees drafts, compliance failures, and in-progress shipments never leak to the public site.

**Render mode:** SSG via `generateStaticParams` on `/products/[slug]`. Homepage and about are statically generated. No ISR. New products require a redeploy (triggered by `git push`).

---

## Routes

### `/` — Homepage
- Hero section: "Public data, structured for sale." + one-line value prop
- Product grid: cards for every shipped product, sorted by `created` desc
- Card content: product name, price, summary (1 line), row count, "View →"
- Footer: copyright, GitHub link if exists, autonomous-agent-collective tagline

### `/products/[slug]` — Product detail
- Hero: product name, price, row count, summary
- Bonus stack (bullet list from `spec.bonus_stack`)
- "Who buys this" (from `spec.audience`)
- Data source citation (from `spec.source`) — visible, not hidden
- Two CTAs:
  - **Primary button:** "Buy now — $X via Stripe" → `launch.stripe_payment_link_url`
  - **Secondary button:** "Or buy on Gumroad" → `launch.gumroad_listing_url` (only if present)
- Schema.org Product JSON-LD in head for SEO
- Sample data preview: if `state/products/<slug>/sample.csv` exists (engineer-generated), render first 5 rows as a table; otherwise omit gracefully

`generateStaticParams` enumerates shipped slugs at build; ISR handles new products after deploy.

### `/about` — Story page
- One-paragraph explanation: autonomous agent collective, public-data-only ethic, source-citation guarantee
- Link back to homepage

### `/robots.txt`
- `User-agent: * / Allow: /` — fully crawlable
- Sitemap reference

### `/sitemap.xml`
- Dynamic from `listProducts()` — homepage, /about, /products/<slug> for each shipped product

---

## Checkout flow

Each product page has two outbound CTAs:

1. **Primary — Stripe Payment Link** (existing infrastructure from v1):
   - Link target: `launch.stripe_payment_link_url`
   - Opens Stripe-hosted checkout
   - Asset delivery: existing Stripe success page → GitHub Gist download link (unchanged from v1)
2. **Secondary — Gumroad** (existing infrastructure from v1):
   - Link target: `launch.gumroad_listing_url`
   - Opens Gumroad's product page
   - Only renders if `launch.gumroad_listing_url` is set

**No new payment integration in this sub-project.** Recurring billing (Phase 2 sub-project 3) introduces Stripe Checkout sessions with subscription mode.

---

## State directory in deploy

Vercel needs the product spec JSONs at runtime. Two facts to reconcile:

1. **Spec files are small** (`spec.json` + `launch-report.json` = ~5 KB per product)
2. **Dataset CSVs are large** (FMCSA = 13 MB; CSLB = 55 MB; NPPES = 78 MB). Vercel deploy limit is 250 MB unzipped. Including all datasets would blow it out within ~5 products.

**Solution:** include only the JSON files, exclude the CSVs.

**`.gitignore` rule (already needed):**
```
state/datasets/*.csv
state/*.csv
```

**`site/vercel.json` `includeFiles`:**
```json
{
  "functions": {
    "app/**": {
      "includeFiles": "../state/products/**/*.json"
    }
  }
}
```

This guarantees Vercel bundles spec + launch-report JSONs into every serverless function but leaves the multi-megabyte CSVs out.

---

## Engineer agent integration

**One small additive workflow step.** Engineer's existing job (write `spec.json`, write `launch-report.json`, run smoke test) extends with a `git add && git commit && git push` step so Vercel auto-deploys the new product page.

**Updated `engineer` employee identity:**
> After Stripe + Gumroad shipping, commit the new `spec.json` + `launch-report.json` to git and push. Vercel auto-deploys the storefront within ~3–5 minutes. Wait for the deploy to complete (poll `https://data.oefrenterprise.com/products/<slug>` for HTTP 200), then run smoke test as the final step of shipping.

**Updated smoke-test contract:**
```bash
curl -fsSL https://data.oefrenterprise.com/                          # 200
curl -fsSL https://data.oefrenterprise.com/products/<slug>          # 200 + name
curl -fsSL <launch.stripe_payment_link_url>                          # 200
[ -n "<launch.gumroad_listing_url>" ] && curl -fsSL <gumroad_url>   # 200 if present
```

---

## DNS & deployment

**Domain registrar:** existing oefrenterprise.com setup.
**DNS record:** add CNAME `data.oefrenterprise.com → cname.vercel-dns.com.`
**Vercel project:** new project linked to `~/apps/dataStructured/site/` directory in the monorepo. Domain assignment via Vercel dashboard.
**CI:** Vercel auto-deploys on `git push` to `master` (the repo's tracked production branch per recent commits). Initial deploy is performed manually via `vercel --prod` from `~/apps/dataStructured/site/` during the implementation plan to bootstrap the Vercel project; thereafter every push deploys automatically.

---

## SEO

**Per-product meta tags** (from spec):
- `<title>` = `${spec.name} | DataStructured`
- `<meta name="description">` = first 155 chars of `spec.summary`
- Open Graph: `og:title`, `og:description`, `og:image` (default for v1, per-product image later)
- Schema.org Product JSON-LD: name, description, offers (price + URL), image

**Sitemap:** dynamic per `listProducts()`. Robots fully open.

**Per-product OG image** is explicitly deferred — default OG image at launch, dynamic OG image generation (Next.js `ImageResponse`) is a later iteration.

---

## What this sub-project explicitly does NOT include

- Customer accounts / login (Phase 4)
- Search or filtering UI (Phase 4 SaaS vision)
- Stripe Checkout subscription integration (Phase 2 sub-project 3)
- Customer-success email automation (Phase 2 sub-project 4)
- Analytics beyond Vercel default (deferred)
- Per-product dynamic OG images (deferred)
- Sample-CSV preview generation (engineer agent change, deferred)
- Cart / multi-product checkout (out of scope; one-time products always)

---

## Success criteria

Sub-project ships when ALL true:

1. `data.oefrenterprise.com` returns HTTP 200 on `/`, `/about`, `/products/<slug>` for every shipped product (all 16 current product folders qualified by filter)
2. Stripe Payment Link CTA on every product page loads its Stripe-hosted checkout page (HTTP 200)
3. Gumroad CTA renders for every product with a Gumroad URL in launch-report
4. Vercel build succeeds with `state/products/*/spec.json` + `launch-report.json` included; deploy under 250 MB
5. New product (any one shipped after the storefront goes live) appears on `/` and at `/products/<slug>` within 10 minutes of `git push` of its `spec.json` + `launch-report.json` (allowing for Vercel build + cache propagation)
6. Engineer employee identity updated; engineer's next product ships with storefront verification in smoke test
7. Lighthouse mobile score ≥ 90 on homepage and one product page (basic perf hygiene)

---

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| `state/products/` not on Vercel filesystem at runtime | Explicit `vercel.json` `includeFiles` directive; smoke test catches missing data |
| Engineer forgets to `git push` after writing launch-report | Add explicit push step to engineer identity; CEO pipeline cycle can verify storefront state matches state/products/ list as an audit |
| Large CSVs accidentally committed to git → Vercel deploy fails | `.gitignore` updated for `state/datasets/*.csv`; pre-commit hook (optional Phase 2 sub-sub-project) |
| Subdomain DNS propagation delay | Acceptable one-time; verify `dig data.oefrenterprise.com` returns Vercel CNAME before declaring done |
| Stripe Payment Link URL changes (e.g., product price update) | `launch-report.json` is the single source of truth; engineer overwrites the file on update; storefront ISR picks up the change within 60s |
| Product with compliance FAIL leaks | Filter logic checks `compliance_verdict === "PASS"` AND `status === "FULLY_SHIPPED"` — both required. Compliance officer is the gate, storefront is belt-and-suspenders. |

---

## Open questions resolved during design

| Question | Answer |
|---|---|
| Subdomain or subpath under oefr-website? | Subdomain — folder-scoped hard rule + PRD example |
| ISR vs SSG vs SSR? | SSG with `generateStaticParams` — Vercel bundles state at build time, so ISR adds no value; redeploy-on-push is the refresh mechanism |
| Stripe Checkout embed vs Payment Link redirect? | Payment Link redirect — recurring billing sub-project introduces Checkout later |
| New Stripe products with subscription mode? | Out of scope for storefront; introduced in sub-project 3 |
| Include datasets in deploy? | No — only JSON metadata; CSVs gitignored |
| Engineer agent gains new tools? | No — only an updated smoke-test step |

---

## Cross-project memory updates required

After ship:

- Update `project_datastructured_v1.md` memory: storefront live at `data.oefrenterprise.com`, Phase 2 sub-project 1 of 5 complete
- Append closeout note to PRD: Phase 2 sub-project 1 done, next sub-project (product-manager agent) starts
- Update `~/apps/dataStructured/CLAUDE.md`: add storefront paragraph + the new engineer smoke-test step

---

## Next sub-project

Once this ships green, **Phase 2 sub-project 2: product-manager agent** brainstorming begins. That agent's purpose: draft richer product specs than CEO's current ad-hoc drafting, propose A/B-test variants per niche, pick the first subscription candidate for sub-project 3 (recurring billing).
