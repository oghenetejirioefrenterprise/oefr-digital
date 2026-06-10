# 🥗 MealCraft Pro

> Premium weekly meal planner — one-time purchase ($27), lifetime access.

**Live stack:** Next.js 15+ · Tailwind CSS · @dnd-kit · Recharts · Stripe

---

## Features

- **Weekly Meal Grid** — Mon–Sun × Breakfast/Lunch/Dinner/Snacks. Drag-and-drop between slots.
- **Recipe Database** — 52 built-in recipes with full nutrition, tags, prep/cook times
- **Custom Recipes** — Create your own with ingredients, steps, nutrition, and an image URL
- **Auto Shopping List** — Ingredients aggregated by category (Produce, Dairy, Protein, Grains…)
- **Nutrition Overview** — Per-day calories, protein, carbs, fat with bar charts
- **Dietary Filters** — Vegetarian, Vegan, Keto, Gluten-Free, High-Protein
- **Save Plans** — Store multiple weekly plans, load/delete anytime
- **Print** — Print week plan and shopping list
- **100% Local** — All data in `localStorage`, nothing ever leaves your device

## Pages

| Path | Description |
|------|-------------|
| `/` | Landing page — hero, features, pricing, testimonials, FAQ |
| `/demo` | 3-day limited demo (no purchase required) |
| `/app` | Full 7-day planner (requires access) |
| `/app/recipes` | Recipe browser with filters + custom recipe builder |
| `/app/shopping` | Shopping list with checkboxes and quantity adjustment |
| `/app/settings` | Dietary restrictions, preferences |
| `/api/checkout` | Stripe checkout session ($27 one-time) |

## Setup

```bash
cd ~/apps/meal-planner
cp .env.local.example .env.local   # fill in your Stripe key
npm run dev
```

### Environment Variables

```env
STRIPE_SECRET_KEY=sk_live_...       # Required for payments
NEXT_PUBLIC_APP_URL=https://...     # Your deployed URL
```

## Development

```bash
npm run dev      # dev server on :3000
npm run build    # production build
npm run start    # serve production build
```

## Access Gate

- After purchase, Stripe redirects to `/api/checkout/success?session_id=...`
- Server verifies payment, redirects to `/app/success?verified=1`
- Client-side JS calls `grantAccess()` → sets `localStorage.mp_access = "granted"`

For testing/dev, visit `/app/gate` and click **[Dev: bypass gate]** or enter code `DEMO2025`.

## Tech Stack

- **Framework:** Next.js 15+ (App Router)
- **Styling:** Tailwind CSS v4 — dark navy theme with lime/green accents
- **Drag & Drop:** `@dnd-kit/core` + `@dnd-kit/sortable`
- **Payments:** Stripe (createFetchHttpClient for Edge compatibility)
- **Storage:** Browser `localStorage` — zero backend required
