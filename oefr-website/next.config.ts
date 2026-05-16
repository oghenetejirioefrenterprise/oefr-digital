import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'Content-Security-Policy', value: "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline' https://js.stripe.com; frame-src https://js.stripe.com; style-src 'self' 'unsafe-inline';" },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ];
  },
  async redirects() {
    return [
      // CEO Needle Mover 2026-05-15 17:00 ET: /iep-504-pack 308-to-Stripe redirect REMOVED.
      // Reason: per Oracle 15:00 ET + 15:08 ET retry, trust-signal patch on the storefront slug is the
      // scenario (b) prep action at T+48h first-conversion read. Replaced with a real landing page at
      // app/iep-504-pack/page.tsx containing: federal-citation count, sample-citation excerpt, refund
      // policy, "no creator persona — just the law" tagline, 12-letter inventory, 3-tool inventory, FAQ,
      // cross-links to the 4 federal-citation SEO articles deployed 11:30 ET today. Apr 30 HARD STOP
      // compliant: page hosts the "Buy" button → Stripe plink_1TQEGp3H4Cmk8ulCCI2HAcv1, not a direct
      // inline-Stripe-iframe mechanism. Eliminates "Pinterest → blog pillar → 308 → Stripe" jank for
      // typed-URL / external-referral / SEO direct hits.
      //
      // Note (CEO Needle Mover 2026-05-14 17:00 ET): /lawn-care-ops-pack redirect REMOVED.
      // Lawn-care SKU REJECTED 09:00 ET 2026-05-14 (Validator-Executor kill_with_evidence verdict).
      // Stripe plink_1TVX173H4Cmk8ulCGl68GuNy + prod_UOaHnPzCCUqFaz deactivated active=False 15:00 ET 2026-05-14
      // (CEO Needle Mover cycle). The old redirect destination (https://buy.stripe.com/aFacMY3yLcvd7iP4uO7IY0t)
      // rendered a Stripe "no longer accepts payment" dead-page = trust damage. Dropping the redirect entirely
      // is the clean fix — the slug now correctly 404s and there is no logical SKU successor.
    ];
  },
};

export default nextConfig;
