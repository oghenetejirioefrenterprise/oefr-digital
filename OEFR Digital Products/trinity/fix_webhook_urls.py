"""One-shot repair: re-point misrouted Stripe webhook endpoints.

Five webhook endpoints were registered against generic *.vercel.app URLs
that are dead or owned by third parties (found 2026-07-02). Fulfillment
for those products can never fire until these point at the canonical
production domains. Updating the URL preserves each endpoint's signing
secret, so app-side STRIPE_WEBHOOK_SECRET values stay valid.

Run:  source ~/.profile && python trinity/fix_webhook_urls.py
"""

import os
import sys

import requests

REMAP = {
    "https://meal-planner.vercel.app/api/webhooks/stripe":
        "https://meals.oefrenterprise.com/api/webhooks/stripe",
    "https://subscription-tracker.vercel.app/api/webhooks/stripe":
        "https://subs.oefrenterprise.com/api/webhooks/stripe",
    "https://resume-builder.vercel.app/api/webhooks/stripe":
        "https://resume.oefrenterprise.com/api/webhooks/stripe",
    "https://content-calendar.vercel.app/api/webhooks/stripe":
        "https://calendar.oefrenterprise.com/api/webhooks/stripe",
    "https://password-vault.vercel.app/api/webhooks/stripe":
        "https://vault.oefrenterprise.com/api/webhooks/stripe",
}


def main() -> int:
    key = os.environ.get("STRIPE_SECRET") or os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        print("STRIPE_SECRET not set — source ~/.profile first")
        return 1

    eps = requests.get(
        "https://api.stripe.com/v1/webhook_endpoints?limit=100",
        auth=(key, ""), timeout=20,
    ).json()["data"]

    fixed = 0
    for e in eps:
        new = REMAP.get(e["url"])
        if not new:
            continue
        r = requests.post(
            f"https://api.stripe.com/v1/webhook_endpoints/{e['id']}",
            auth=(key, ""), data={"url": new}, timeout=20,
        )
        if r.ok:
            print(f"UPDATED {e['id']}: {e['url']} -> {new}")
            fixed += 1
        else:
            print(f"FAILED {e['id']}: {r.status_code} {r.text[:200]}")

    print(f"\n{fixed}/{len(REMAP)} endpoints re-pointed.")
    if fixed:
        print("Re-run the verifier to confirm: python trinity/verifier.py")
    return 0 if fixed == len(REMAP) else 1


if __name__ == "__main__":
    sys.exit(main())
