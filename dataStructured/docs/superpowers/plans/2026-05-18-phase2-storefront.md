# Phase 2 Storefront Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a Next.js storefront at `data.oefrenterprise.com` rendering one page per shipped DataStructured product, with checkout CTAs to existing Stripe Payment Links and Gumroad listings.

**Architecture:** Next.js 14 App Router project at `~/apps/dataStructured/site/`. SSG with `generateStaticParams`. Reads `state/products/*/spec.json` + `launch-report.json` from sibling directory at build time. Filter on `status === FULLY_SHIPPED` AND `compliance_verdict === PASS`. Vercel deploy, custom subdomain.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, Vitest (lib/ unit tests), Vercel.

**Spec:** [`docs/superpowers/specs/2026-05-18-phase2-storefront-design.md`](../specs/2026-05-18-phase2-storefront-design.md)

---

## File Structure

**Files to create:**
- `site/package.json` — Next.js + TypeScript + Tailwind + Vitest deps
- `site/tsconfig.json` — strict TypeScript config
- `site/next.config.mjs` — Next.js config with outputFileTracingIncludes
- `site/tailwind.config.ts`, `site/postcss.config.mjs` — Tailwind
- `site/vercel.json` — framework config
- `site/.gitignore` — node_modules, .next, etc.
- `site/app/layout.tsx` — root layout + metadata
- `site/app/page.tsx` — homepage
- `site/app/products/[slug]/page.tsx` — product detail
- `site/app/about/page.tsx` — about page
- `site/app/robots.txt/route.ts` — robots
- `site/app/sitemap.ts` — sitemap
- `site/app/globals.css` — Tailwind directives
- `site/components/ProductCard.tsx`
- `site/components/CheckoutCTAs.tsx`
- `site/components/BonusStack.tsx`
- `site/lib/types.ts` — ProductSpec, LaunchReport types
- `site/lib/products.ts` — listProducts, getProduct
- `site/lib/products.test.ts` — Vitest tests
- `site/vitest.config.ts` — Vitest config
- `site/public/favicon.ico` — placeholder

**Files to modify:**
- `.gitignore` (repo root at `~/apps/`) — add `dataStructured/state/datasets/*.csv` rule
- `~/apps/dataStructured/.trinity/employees/engineer/identity.md` — add git-push + storefront smoke-test step
- `~/apps/dataStructured/CLAUDE.md` — add storefront paragraph

**Explicit deferral:** Schema.org JSON-LD structured data — basic OG + meta tags only in v1. JSON-LD adds in a later sub-project.

---

## Task 1: Scaffold Next.js project skeleton

**Files:**
- Create: `site/package.json`
- Create: `site/tsconfig.json`
- Create: `site/next.config.mjs`
- Create: `site/.gitignore`
- Create: `site/app/globals.css`
- Create: `site/postcss.config.mjs`
- Create: `site/tailwind.config.ts`

- [ ] **Step 1: Create `site/package.json`**

```json
{
  "name": "datastructured-site",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3501",
    "build": "next build",
    "start": "next start -p 3501",
    "lint": "next lint",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "next": "14.2.15",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@types/node": "20.14.10",
    "@types/react": "18.3.3",
    "@types/react-dom": "18.3.0",
    "autoprefixer": "10.4.20",
    "eslint": "8.57.0",
    "eslint-config-next": "14.2.15",
    "postcss": "8.4.47",
    "tailwindcss": "3.4.14",
    "typescript": "5.5.3",
    "vitest": "2.1.4"
  }
}
```

- [ ] **Step 2: Create `site/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "ES2022"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Create `site/next.config.mjs`**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  outputFileTracingIncludes: {
    "/**/*": ["../state/products/**/*.json"]
  }
};

export default nextConfig;
```

- [ ] **Step 4: Create `site/.gitignore`**

```
node_modules
.next
out
.env*.local
*.log
.vercel
```

- [ ] **Step 5: Create `site/tailwind.config.ts`**

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["system-ui", "-apple-system", "sans-serif"]
      }
    }
  },
  plugins: []
};

export default config;
```

- [ ] **Step 6: Create `site/postcss.config.mjs`**

```javascript
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} }
};
```

- [ ] **Step 7: Create `site/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root { color-scheme: light; }
body { @apply bg-white text-neutral-900 antialiased; }
```

- [ ] **Step 8: Install dependencies**

Run: `cd /home/oghenetejiri/apps/dataStructured/site && npm install`
Expected: installs without errors, `node_modules/` populated, `package-lock.json` created.

- [ ] **Step 9: Commit**

```bash
cd /home/oghenetejiri/apps
git add dataStructured/site/package.json dataStructured/site/package-lock.json dataStructured/site/tsconfig.json dataStructured/site/next.config.mjs dataStructured/site/.gitignore dataStructured/site/tailwind.config.ts dataStructured/site/postcss.config.mjs dataStructured/site/app/globals.css
git commit -m "feat(dataStructured/site): scaffold Next.js 14 storefront project"
```

---

## Task 2: gitignore for large CSVs and vercel.json

**Files:**
- Modify: `/home/oghenetejiri/apps/.gitignore`
- Create: `site/vercel.json`

- [ ] **Step 1: Check current root .gitignore for CSV rules**

Run: `grep -n "state.*csv\|\.csv" /home/oghenetejiri/apps/.gitignore || echo "no csv rules"`

- [ ] **Step 2: Add CSV rules if missing**

Append to `/home/oghenetejiri/apps/.gitignore`:

```
# DataStructured: large dataset CSVs stay out of git (and out of Vercel deploys).
dataStructured/state/datasets/*.csv
dataStructured/state/*.csv
```

- [ ] **Step 3: Create `site/vercel.json`**

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "buildCommand": "next build",
  "framework": "nextjs",
  "outputDirectory": ".next"
}
```

- [ ] **Step 4: Verify no CSVs are currently tracked in git**

Run: `cd /home/oghenetejiri/apps && git ls-files dataStructured/state/ | grep "\.csv$" || echo "none tracked"`
Expected: "none tracked". If any CSVs are tracked, run `git rm --cached <path>` for each before continuing.

- [ ] **Step 5: Commit**

```bash
cd /home/oghenetejiri/apps
git add .gitignore dataStructured/site/vercel.json
git commit -m "chore(dataStructured): gitignore dataset CSVs + vercel config"
```

---

## Task 3: TypeScript types for product data

**Files:**
- Create: `site/lib/types.ts`

- [ ] **Step 1: Write `site/lib/types.ts`**

```typescript
export type ComplianceVerdict = "PASS" | "FAIL" | "NEEDS_FOUNDER_REVIEW";

export type LaunchStatus =
  | "FULLY_SHIPPED"
  | "PARTIAL_SHIPPED"
  | "DRAFT"
  | "FAILED";

export interface ProductSpec {
  version: number;
  type: "product_spec";
  slug: string;
  created: string;
  created_by: string;
  status: string;
  name: string;
  summary: string;
  format: string;
  deliverable: string;
  price_usd: number;
  bonus_stack: string[];
  dataset_file: string;
  ethics_ledger: string;
  audience: string;
  stripe_product_prefix: string;
  channels: string[];
  compliance_verdict: ComplianceVerdict;
  compliance_audited_at: string;
  row_count: number;
  source: string;
  gumroad_listing?: {
    title: string;
    description: string;
    price: number;
    [k: string]: unknown;
  };
}

export interface LaunchReport {
  version: number;
  type: "launch_report";
  slug: string;
  created: string;
  created_by: string;
  status: LaunchStatus;
  summary: string;
  stripe_product_id: string;
  stripe_price_id: string;
  stripe_payment_link_url: string;
  smoke_test: {
    passed: boolean;
    checked_at: string;
  };
  spec_file: string;
  gumroad_listing_url?: string;
  gumroad_product_id?: string;
  gumroad_deployed_at?: string;
}

export interface Product {
  slug: string;
  spec: ProductSpec;
  launch: LaunchReport;
}
```

- [ ] **Step 2: Verify TS compiles**

Run: `cd /home/oghenetejiri/apps/dataStructured/site && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd /home/oghenetejiri/apps
git add dataStructured/site/lib/types.ts
git commit -m "feat(dataStructured/site): add ProductSpec/LaunchReport TypeScript types"
```

---

## Task 4: Product data loader (TDD)

**Files:**
- Create: `site/vitest.config.ts`
- Create: `site/lib/products.ts`
- Create: `site/lib/products.test.ts`
- Create: 4 fixture subfolders under `site/lib/__fixtures__/`

- [ ] **Step 1: Create `site/vitest.config.ts`**

```typescript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["lib/**/*.test.ts"]
  }
});
```

- [ ] **Step 2: Create fixture `site/lib/__fixtures__/passing/spec.json`**

```json
{
  "version": 1,
  "type": "product_spec",
  "slug": "passing",
  "created": "2026-05-04T19:10:00-04:00",
  "created_by": "ceo",
  "status": "READY_TO_SHIP",
  "name": "Passing Product",
  "summary": "Should appear",
  "format": "one_time",
  "deliverable": "csv",
  "price_usd": 39,
  "bonus_stack": ["bonus a"],
  "dataset_file": "n/a",
  "ethics_ledger": "n/a",
  "audience": "test buyers",
  "stripe_product_prefix": "test_",
  "channels": ["stripe_payment_link"],
  "compliance_verdict": "PASS",
  "compliance_audited_at": "2026-05-04T19:10:00-04:00",
  "row_count": 100,
  "source": "test source"
}
```

- [ ] **Step 3: Create fixture `site/lib/__fixtures__/passing/launch-report.json`**

```json
{
  "version": 1,
  "type": "launch_report",
  "slug": "passing",
  "created": "2026-05-04T21:25:00Z",
  "created_by": "engineer",
  "status": "FULLY_SHIPPED",
  "summary": "live",
  "stripe_product_id": "prod_PASS",
  "stripe_price_id": "price_PASS",
  "stripe_payment_link_url": "https://example.com/buy/passing",
  "smoke_test": { "passed": true, "checked_at": "2026-05-04T21:24:00Z" },
  "spec_file": "ignored",
  "gumroad_listing_url": "https://example.com/gumroad/passing"
}
```

- [ ] **Step 4: Create fixture `site/lib/__fixtures__/failing-compliance/spec.json`**

```json
{
  "version": 1,
  "type": "product_spec",
  "slug": "failing-compliance",
  "created": "2026-05-04T19:10:00-04:00",
  "created_by": "ceo",
  "status": "READY_TO_SHIP",
  "name": "Failing Compliance",
  "summary": "Should NOT appear",
  "format": "one_time",
  "deliverable": "csv",
  "price_usd": 39,
  "bonus_stack": [],
  "dataset_file": "n/a",
  "ethics_ledger": "n/a",
  "audience": "x",
  "stripe_product_prefix": "test_",
  "channels": [],
  "compliance_verdict": "FAIL",
  "compliance_audited_at": "2026-05-04T19:10:00-04:00",
  "row_count": 0,
  "source": "x"
}
```

- [ ] **Step 5: Create fixture `site/lib/__fixtures__/failing-compliance/launch-report.json`**

```json
{
  "version": 1,
  "type": "launch_report",
  "slug": "failing-compliance",
  "created": "2026-05-04T21:25:00Z",
  "created_by": "engineer",
  "status": "FULLY_SHIPPED",
  "summary": "live",
  "stripe_product_id": "prod_FAIL",
  "stripe_price_id": "price_FAIL",
  "stripe_payment_link_url": "https://example.com/buy/fail",
  "smoke_test": { "passed": true, "checked_at": "2026-05-04T21:24:00Z" },
  "spec_file": "ignored"
}
```

- [ ] **Step 6: Create fixture `site/lib/__fixtures__/draft/spec.json`**

```json
{
  "version": 1,
  "type": "product_spec",
  "slug": "draft",
  "created": "2026-05-04T19:10:00-04:00",
  "created_by": "ceo",
  "status": "DRAFT",
  "name": "Draft Product",
  "summary": "Should NOT appear",
  "format": "one_time",
  "deliverable": "csv",
  "price_usd": 39,
  "bonus_stack": [],
  "dataset_file": "n/a",
  "ethics_ledger": "n/a",
  "audience": "x",
  "stripe_product_prefix": "test_",
  "channels": [],
  "compliance_verdict": "PASS",
  "compliance_audited_at": "2026-05-04T19:10:00-04:00",
  "row_count": 0,
  "source": "x"
}
```

- [ ] **Step 7: Create fixture `site/lib/__fixtures__/draft/launch-report.json`**

```json
{
  "version": 1,
  "type": "launch_report",
  "slug": "draft",
  "created": "2026-05-04T21:25:00Z",
  "created_by": "engineer",
  "status": "DRAFT",
  "summary": "not live",
  "stripe_product_id": "prod_DRAFT",
  "stripe_price_id": "price_DRAFT",
  "stripe_payment_link_url": "https://example.com/buy/draft",
  "smoke_test": { "passed": false, "checked_at": "2026-05-04T21:24:00Z" },
  "spec_file": "ignored"
}
```

- [ ] **Step 8: Write `site/lib/products.test.ts` (failing test)**

```typescript
import path from "node:path";
import { describe, it, expect } from "vitest";
import { listProducts, getProduct } from "./products";

const FIXTURES = path.join(__dirname, "__fixtures__");

describe("listProducts", () => {
  it("returns only FULLY_SHIPPED + compliance_verdict=PASS products", async () => {
    const products = await listProducts(FIXTURES);
    expect(products.map((p) => p.slug)).toEqual(["passing"]);
  });

  it("sorts by spec.created descending", async () => {
    const products = await listProducts(FIXTURES);
    for (let i = 1; i < products.length; i++) {
      expect(products[i - 1].spec.created >= products[i].spec.created).toBe(true);
    }
  });
});

describe("getProduct", () => {
  it("returns a passing product by slug", async () => {
    const product = await getProduct("passing", FIXTURES);
    expect(product).not.toBeNull();
    expect(product!.spec.name).toBe("Passing Product");
    expect(product!.launch.stripe_payment_link_url).toBe(
      "https://example.com/buy/passing"
    );
  });

  it("returns null for a compliance-failing product", async () => {
    const product = await getProduct("failing-compliance", FIXTURES);
    expect(product).toBeNull();
  });

  it("returns null for a draft product", async () => {
    const product = await getProduct("draft", FIXTURES);
    expect(product).toBeNull();
  });

  it("returns null for a nonexistent slug", async () => {
    const product = await getProduct("does-not-exist", FIXTURES);
    expect(product).toBeNull();
  });
});
```

- [ ] **Step 9: Run test to verify it fails**

Run: `cd /home/oghenetejiri/apps/dataStructured/site && npm test -- --run`
Expected: tests fail with "Cannot find module './products'" or similar.

- [ ] **Step 10: Write `site/lib/products.ts`**

```typescript
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import type { Product, ProductSpec, LaunchReport } from "./types";

const DEFAULT_STATE_DIR = path.join(
  process.cwd(),
  "..",
  "state",
  "products"
);

export async function listProducts(stateDir = DEFAULT_STATE_DIR): Promise<Product[]> {
  let entries;
  try {
    entries = await readdir(stateDir, { withFileTypes: true });
  } catch {
    return [];
  }

  const products: Product[] = [];
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const product = await loadProduct(entry.name, stateDir);
    if (product) products.push(product);
  }

  products.sort((a, b) => b.spec.created.localeCompare(a.spec.created));
  return products;
}

export async function getProduct(
  slug: string,
  stateDir = DEFAULT_STATE_DIR
): Promise<Product | null> {
  return loadProduct(slug, stateDir);
}

async function loadProduct(
  slug: string,
  stateDir: string
): Promise<Product | null> {
  const specPath = path.join(stateDir, slug, "spec.json");
  const launchPath = path.join(stateDir, slug, "launch-report.json");

  let spec: ProductSpec;
  let launch: LaunchReport;
  try {
    spec = JSON.parse(await readFile(specPath, "utf8"));
    launch = JSON.parse(await readFile(launchPath, "utf8"));
  } catch {
    return null;
  }

  if (launch.status !== "FULLY_SHIPPED") return null;
  if (spec.compliance_verdict !== "PASS") return null;

  return { slug, spec, launch };
}
```

- [ ] **Step 11: Run test to verify it passes**

Run: `cd /home/oghenetejiri/apps/dataStructured/site && npm test -- --run`
Expected: all tests pass.

- [ ] **Step 12: Commit**

```bash
cd /home/oghenetejiri/apps
git add dataStructured/site/vitest.config.ts dataStructured/site/lib/products.ts dataStructured/site/lib/products.test.ts dataStructured/site/lib/__fixtures__/
git commit -m "feat(dataStructured/site): product loader with compliance + ship-status filter"
```

---

## Task 5: Root layout and metadata

**Files:**
- Create: `site/app/layout.tsx`
- Create: `site/public/favicon.ico` (1x1 placeholder)

- [ ] **Step 1: Create `site/app/layout.tsx`**

```typescript
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://data.oefrenterprise.com"),
  title: {
    default: "DataStructured — Public Data, Structured for Sale",
    template: "%s | DataStructured"
  },
  description:
    "Public-record datasets, packaged for niche audiences. Every row carries its source URL. Operated by an autonomous agent collective.",
  openGraph: {
    title: "DataStructured",
    description:
      "Public-record datasets, packaged for niche audiences. Every row carries its source URL.",
    type: "website",
    url: "https://data.oefrenterprise.com",
    siteName: "DataStructured"
  },
  robots: { index: true, follow: true }
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-neutral-200">
          <nav className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
            <a href="/" className="text-lg font-semibold tracking-tight">
              DataStructured
            </a>
            <a
              href="/about"
              className="text-sm text-neutral-600 hover:text-neutral-900"
            >
              About
            </a>
          </nav>
        </header>
        <main className="mx-auto max-w-5xl px-6 py-12">{children}</main>
        <footer className="mt-24 border-t border-neutral-200">
          <div className="mx-auto max-w-5xl px-6 py-8 text-sm text-neutral-500">
            © {new Date().getFullYear()} OEFR Enterprise — Public data, source-cited on every row.
          </div>
        </footer>
      </body>
    </html>
  );
}
```

- [ ] **Step 2: Create placeholder favicon**

Run: `cd /home/oghenetejiri/apps/dataStructured/site && mkdir -p public && touch public/favicon.ico`

- [ ] **Step 3: Verify type check**

Run: `cd /home/oghenetejiri/apps/dataStructured/site && npx tsc --noEmit`
Expected: no type errors.

- [ ] **Step 4: Commit**

```bash
cd /home/oghenetejiri/apps
git add dataStructured/site/app/layout.tsx dataStructured/site/public/favicon.ico
git commit -m "feat(dataStructured/site): root layout + site-wide metadata"
```

---

## Task 6: Homepage with product grid

**Files:**
- Create: `site/components/ProductCard.tsx`
- Create: `site/app/page.tsx`

- [ ] **Step 1: Create `site/components/ProductCard.tsx`**

```typescript
import type { Product } from "@/lib/types";

export function ProductCard({ product }: { product: Product }) {
  return (
    <a
      href={`/products/${product.slug}`}
      className="block rounded-lg border border-neutral-200 p-6 transition hover:border-neutral-900 hover:shadow-sm"
    >
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-base font-semibold">{product.spec.name}</h3>
        <span className="text-lg font-semibold tabular-nums">
          ${product.spec.price_usd}
        </span>
      </div>
      <p className="mb-3 line-clamp-3 text-sm text-neutral-600">
        {product.spec.summary}
      </p>
      <div className="flex items-center gap-4 text-xs text-neutral-500">
        <span>{product.spec.row_count.toLocaleString()} rows</span>
        <span>{product.spec.format.replace(/_/g, " ")}</span>
      </div>
    </a>
  );
}
```

- [ ] **Step 2: Create `site/app/page.tsx`**

```typescript
import { listProducts } from "@/lib/products";
import { ProductCard } from "@/components/ProductCard";

export default async function HomePage() {
  const products = await listProducts();

  return (
    <div>
      <section className="mb-16">
        <h1 className="text-4xl font-bold tracking-tight">
          Public data, structured for sale.
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-neutral-600">
          Niche-specific datasets, drawn from public sources, source-cited on
          every row. Built and shipped by an autonomous agent collective.
        </p>
      </section>

      <section>
        <h2 className="mb-6 text-xl font-semibold">Products</h2>
        {products.length === 0 ? (
          <p className="text-neutral-600">No products shipped yet.</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {products.map((product) => (
              <ProductCard key={product.slug} product={product} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 3: Build to verify compilation**

Run: `cd /home/oghenetejiri/apps/dataStructured/site && npx next build`
Expected: build succeeds, generates `.next/`.

- [ ] **Step 4: Commit**

```bash
cd /home/oghenetejiri/apps
git add dataStructured/site/components/ProductCard.tsx dataStructured/site/app/page.tsx
git commit -m "feat(dataStructured/site): homepage with product grid"
```

---

## Task 7: Product detail page

**Files:**
- Create: `site/components/CheckoutCTAs.tsx`
- Create: `site/components/BonusStack.tsx`
- Create: `site/app/products/[slug]/page.tsx`

- [ ] **Step 1: Create `site/components/CheckoutCTAs.tsx`**

```typescript
import type { Product } from "@/lib/types";

export function CheckoutCTAs({ product }: { product: Product }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <a
        href={product.launch.stripe_payment_link_url}
        className="inline-flex items-center justify-center rounded-md bg-neutral-900 px-6 py-3 text-base font-semibold text-white hover:bg-neutral-700"
      >
        Buy now — ${product.spec.price_usd} via Stripe
      </a>
      {product.launch.gumroad_listing_url && (
        <a
          href={product.launch.gumroad_listing_url}
          className="inline-flex items-center justify-center rounded-md border border-neutral-300 px-6 py-3 text-base font-semibold text-neutral-700 hover:border-neutral-900 hover:text-neutral-900"
        >
          Or buy on Gumroad
        </a>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create `site/components/BonusStack.tsx`**

```typescript
export function BonusStack({ items }: { items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">
        What's included
      </h3>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item} className="flex items-start gap-2 text-base">
            <span aria-hidden className="mt-1.5 size-1.5 shrink-0 rounded-full bg-neutral-900" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 3: Create `site/app/products/[slug]/page.tsx`**

```typescript
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getProduct, listProducts } from "@/lib/products";
import { CheckoutCTAs } from "@/components/CheckoutCTAs";
import { BonusStack } from "@/components/BonusStack";

export async function generateStaticParams() {
  const products = await listProducts();
  return products.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const product = await getProduct(params.slug);
  if (!product) return { title: "Not found" };
  return {
    title: product.spec.name,
    description: product.spec.summary.slice(0, 155),
    openGraph: {
      title: product.spec.name,
      description: product.spec.summary.slice(0, 155)
    }
  };
}

export default async function ProductPage({
  params
}: {
  params: { slug: string };
}) {
  const product = await getProduct(params.slug);
  if (!product) notFound();

  return (
    <article className="space-y-10">
      <header className="space-y-3">
        <p className="text-sm uppercase tracking-wide text-neutral-500">
          {product.spec.row_count.toLocaleString()} rows · {product.spec.format.replace(/_/g, " ")}
        </p>
        <h1 className="text-4xl font-bold tracking-tight">
          {product.spec.name}
        </h1>
        <p className="max-w-2xl text-lg text-neutral-600">
          {product.spec.summary}
        </p>
      </header>

      <CheckoutCTAs product={product} />

      <BonusStack items={product.spec.bonus_stack} />

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">
          Who buys this
        </h2>
        <p className="text-base text-neutral-700">{product.spec.audience}</p>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">
          Data source
        </h2>
        <p className="text-sm text-neutral-700">{product.spec.source}</p>
      </section>
    </article>
  );
}
```

- [ ] **Step 4: Build to verify**

Run: `cd /home/oghenetejiri/apps/dataStructured/site && npx next build`
Expected: build succeeds; output lists `/products/<each-slug>` as static routes.

- [ ] **Step 5: Commit**

```bash
cd /home/oghenetejiri/apps
git add dataStructured/site/components/CheckoutCTAs.tsx dataStructured/site/components/BonusStack.tsx dataStructured/site/app/products/
git commit -m "feat(dataStructured/site): product detail page with SSG"
```

---

## Task 8: About page

**Files:**
- Create: `site/app/about/page.tsx`

- [ ] **Step 1: Create `site/app/about/page.tsx`**

```typescript
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About",
  description:
    "DataStructured is operated by an autonomous agent collective. Public data only. Source URL on every row. Never discount; stack value."
};

export default function AboutPage() {
  return (
    <article className="max-w-2xl">
      <h1 className="text-4xl font-bold tracking-tight">About DataStructured</h1>

      <p className="mt-6 text-lg text-neutral-700">
        DataStructured is a public-data-as-a-product company operated as an
        autonomous agent collective. Six AI employees handle research, harvest,
        cleaning, compliance review, and shipping. No human ships a product
        end-to-end.
      </p>

      <h2 className="mt-10 text-xl font-semibold">What we promise</h2>
      <ul className="mt-3 space-y-2 text-neutral-700">
        <li>
          <strong>Public data only.</strong> No auth-bypass, no scraping behind
          login walls, no purchased private datasets.
        </li>
        <li>
          <strong>No PII.</strong> Personal contact details, financial accounts,
          or government IDs are an automatic compliance fail.
        </li>
        <li>
          <strong>Source URL on every row.</strong> You can verify any record.
        </li>
        <li>
          <strong>We never discount.</strong> If you wait, you don't save.
          Value is stacked into every release.
        </li>
      </ul>

      <h2 className="mt-10 text-xl font-semibold">Operated by</h2>
      <p className="mt-3 text-neutral-700">
        OEFR Enterprise — TJ Orukpe, founder. Storefront and operations run by
        the Trinity agent collective.
      </p>
    </article>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd /home/oghenetejiri/apps/dataStructured/site && npx next build`

- [ ] **Step 3: Commit**

```bash
cd /home/oghenetejiri/apps
git add dataStructured/site/app/about/
git commit -m "feat(dataStructured/site): about page"
```

---

## Task 9: robots.txt and sitemap.xml

**Files:**
- Create: `site/app/robots.txt/route.ts`
- Create: `site/app/sitemap.ts`

- [ ] **Step 1: Create `site/app/robots.txt/route.ts`**

```typescript
export const dynamic = "force-static";

export function GET() {
  const body = [
    "User-agent: *",
    "Allow: /",
    "Sitemap: https://data.oefrenterprise.com/sitemap.xml"
  ].join("\n");
  return new Response(body, {
    headers: { "Content-Type": "text/plain" }
  });
}
```

- [ ] **Step 2: Create `site/app/sitemap.ts`**

```typescript
import type { MetadataRoute } from "next";
import { listProducts } from "@/lib/products";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const products = await listProducts();
  const base = "https://data.oefrenterprise.com";
  const lastModified = new Date();

  return [
    { url: `${base}/`, lastModified, changeFrequency: "daily", priority: 1.0 },
    { url: `${base}/about`, lastModified, changeFrequency: "yearly", priority: 0.5 },
    ...products.map((product) => ({
      url: `${base}/products/${product.slug}`,
      lastModified: new Date(product.spec.created),
      changeFrequency: "weekly" as const,
      priority: 0.9
    }))
  ];
}
```

- [ ] **Step 3: Build and check sitemap output**

Run: `cd /home/oghenetejiri/apps/dataStructured/site && npx next build`
Expected: build succeeds; sitemap route present.

- [ ] **Step 4: Commit**

```bash
cd /home/oghenetejiri/apps
git add dataStructured/site/app/robots.txt/ dataStructured/site/app/sitemap.ts
git commit -m "feat(dataStructured/site): robots.txt + dynamic sitemap"
```

---

## Task 10: Local smoke test

- [ ] **Step 1: Start dev server in background**

Run: `cd /home/oghenetejiri/apps/dataStructured/site && npm run dev > /tmp/storefront-dev.log 2>&1 &`
Wait ~5 seconds.

- [ ] **Step 2: Verify homepage**

Run: `curl -fsSL http://localhost:3501/ | head -200`
Expected: HTML containing "Public data, structured for sale." and at least one product card.

- [ ] **Step 3: Verify product page**

Run: `curl -fsSL http://localhost:3501/products/new-fmcsa-carrier-leads-2026-05`
Expected: HTML containing "FMCSA" and the Stripe payment link URL.

- [ ] **Step 4: Verify about, sitemap, robots**

Run:
```bash
curl -fsSL http://localhost:3501/about | grep "autonomous agent collective"
curl -fsSL http://localhost:3501/sitemap.xml | grep "data.oefrenterprise.com"
curl -fsSL http://localhost:3501/robots.txt | grep "User-agent: \*"
```
All three must succeed.

- [ ] **Step 5: Run Vitest once more**

Run: `cd /home/oghenetejiri/apps/dataStructured/site && npm test -- --run`
Expected: all tests pass.

- [ ] **Step 6: Kill dev server**

Run: `pkill -f "next dev -p 3501" || true`

---

## Task 11: Initial Vercel deploy

This task assumes `vercel` CLI is installed and authenticated (other apps in `~/apps/` already use it).

- [ ] **Step 1: Vercel auth check**

Run: `vercel whoami`
If error, ask the user to `vercel login` interactively. Then re-run.

- [ ] **Step 2: Link the project**

Run:
```bash
cd /home/oghenetejiri/apps/dataStructured/site
vercel link --yes --project datastructured-site
```
Expected: creates `.vercel/` directory with project config. If the project doesn't exist on Vercel yet, this creates it.

- [ ] **Step 3: First production deploy**

Run:
```bash
cd /home/oghenetejiri/apps/dataStructured/site
vercel --prod
```
Expected: deploy succeeds, outputs production URL (e.g. `https://datastructured-site-xyz.vercel.app`).

- [ ] **Step 4: Smoke test the Vercel URL**

Use the URL from step 3 output:
```bash
URL="<paste-vercel-url-from-step-3>"
curl -fsSL "$URL/" | grep "Public data, structured"
curl -fsSL "$URL/products/new-fmcsa-carrier-leads-2026-05" | grep "FMCSA"
curl -fsSL "$URL/sitemap.xml" | grep "data.oefrenterprise.com"
```
All must succeed.

- [ ] **Step 5: Commit `.vercel/project.json`**

```bash
cd /home/oghenetejiri/apps
git add -f dataStructured/site/.vercel/project.json
git commit -m "chore(dataStructured/site): link Vercel project"
```

The `.vercel/` directory is otherwise gitignored. Force-add the single `project.json` so the deploy link survives across machines.

---

## Task 12: DNS + subdomain mapping

- [ ] **Step 1: Add custom domain in Vercel**

Run:
```bash
cd /home/oghenetejiri/apps/dataStructured/site
vercel domains add data.oefrenterprise.com
```
Expected: Vercel returns the DNS record to add at the registrar (CNAME → `cname.vercel-dns.com.`).

- [ ] **Step 2: Add DNS record (user action)**

At oefrenterprise.com's DNS provider, add:
- Name: `data`
- Type: `CNAME`
- Value: `cname.vercel-dns.com.`
- TTL: 300

If the user prefers, the Bash command pattern is provider-specific; pause here for the user to confirm the record is added.

- [ ] **Step 3: Wait for propagation**

Run:
```bash
until dig +short data.oefrenterprise.com | grep -q "."; do sleep 30; done
dig +short data.oefrenterprise.com
```
Expected: returns Vercel CNAME or IP within 1–15 minutes.

- [ ] **Step 4: Smoke test the subdomain**

Run:
```bash
curl -fsSL https://data.oefrenterprise.com/ | grep "DataStructured"
curl -fsSL https://data.oefrenterprise.com/products/new-fmcsa-carrier-leads-2026-05 | grep "FMCSA"
curl -fsSL https://data.oefrenterprise.com/sitemap.xml | grep "data.oefrenterprise.com"
curl -fsSL https://data.oefrenterprise.com/robots.txt | grep "Sitemap"
```
All must succeed.

- [ ] **Step 5: Lighthouse mobile (optional)**

Run: `npx -y lighthouse https://data.oefrenterprise.com/ --only-categories=performance --form-factor=mobile --quiet --output=json --chrome-flags="--headless --no-sandbox" | jq '.categories.performance.score'`
Expected: ≥ 0.9. If Chrome is unavailable, verify manually via PageSpeed Insights.

---

## Task 13: Engineer agent identity + CLAUDE.md updates

**Files:**
- Modify: `~/apps/dataStructured/.trinity/employees/engineer/identity.md`
- Modify: `~/apps/dataStructured/CLAUDE.md`

- [ ] **Step 1: Read current engineer identity**

Run: `cat /home/oghenetejiri/apps/dataStructured/.trinity/employees/engineer/identity.md | head -100`

- [ ] **Step 2: Append a Storefront verification section**

Append to the engineer identity:

```markdown

## Storefront verification (Phase 2+)

After writing `state/products/<slug>/spec.json` and `launch-report.json`:

1. Commit and push so Vercel auto-deploys the new product page:

```bash
cd ~/apps/dataStructured
git add state/products/<slug>/ && git commit -m "ship(dataStructured): <slug> launched" && git push
```

2. Poll until the storefront page is live:

```bash
until curl -fsS "https://data.oefrenterprise.com/products/<slug>" > /dev/null; do sleep 30; done
```

3. Verify all four endpoints return 200:

```bash
curl -fsSL "https://data.oefrenterprise.com/products/<slug>"
curl -fsSL "$(jq -r .stripe_payment_link_url state/products/<slug>/launch-report.json)"
GUMROAD=$(jq -r .gumroad_listing_url state/products/<slug>/launch-report.json)
[ "$GUMROAD" != "null" ] && curl -fsSL "$GUMROAD"
```

4. On any failure, set `launch-report.status = PARTIAL_SHIPPED` and log to `state/ethics-ledger/`.
```

- [ ] **Step 3: Add storefront paragraph to CLAUDE.md**

Insert after the "Common commands" section in `~/apps/dataStructured/CLAUDE.md`:

```markdown
## Storefront (Phase 2 sub-project 1)

Public site at https://data.oefrenterprise.com — Next.js 14 App Router at `~/apps/dataStructured/site/`. Reads `state/products/*/spec.json` + `launch-report.json` at build time. Filters on `compliance_verdict === "PASS"` AND `status === "FULLY_SHIPPED"`. Engineer agent's shipping flow now includes a `git push` step to trigger Vercel auto-deploy of new product pages.

```bash
# Local dev
cd ~/apps/dataStructured/site
npm install
npm run dev  # → http://localhost:3501

# Tests
npm test

# Deploy (usually auto on git push; manual override available)
vercel --prod
```
```

- [ ] **Step 4: Commit**

```bash
cd /home/oghenetejiri/apps
git add dataStructured/.trinity/employees/engineer/identity.md dataStructured/CLAUDE.md
git commit -m "docs(dataStructured): engineer identity + CLAUDE.md updated for storefront"
```

---

## Task 14: Memory updates (no commit)

**Files:**
- Modify: `~/.claude/projects/-home-oghenetejiri-apps/memory/project_datastructured_v1.md`
- Modify: `~/.claude/projects/-home-oghenetejiri-apps/memory/MEMORY.md`

- [ ] **Step 1: Append Phase 2 sub-project 1 paragraph to `project_datastructured_v1.md`**

```markdown
**Phase 2 sub-project 1 (storefront) shipped 2026-05-18:**
- Live at https://data.oefrenterprise.com — Next.js 14 at `~/apps/dataStructured/site/`
- Renders all FULLY_SHIPPED + compliance-PASS products
- Engineer agent identity updated to include `git push` + storefront smoke-test
- Vitest tests on lib/products.ts filter logic
- Remaining Phase 2 sub-projects: 2) product-manager agent · 3) recurring billing · 4) customer-success agent · 5) distribution-queue consumer
```

- [ ] **Step 2: Update the memory index entry in `MEMORY.md`**

Replace existing line with:

```
- [DataStructured v1 closed out](project_datastructured_v1.md) — Phase 2 sub-project 1 (storefront) shipped 2026-05-18 at data.oefrenterprise.com; 4 more sub-projects remaining
```

- [ ] **Step 3: Verify both files load without YAML errors**

Run: `head -10 /home/oghenetejiri/.claude/projects/-home-oghenetejiri-apps/memory/project_datastructured_v1.md`
Expected: valid frontmatter.

Memory files are local-only — not committed.

---

## Closeout

When tasks 1–14 are all checked, mark this plan complete. The storefront is live; engineer agent's next product launch auto-publishes. Phase 2 sub-project 2 (product-manager agent) brainstorming begins as the next session's work.
