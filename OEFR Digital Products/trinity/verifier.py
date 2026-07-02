"""Funnel verifier — deterministic end-to-end product verification.

Walks every revenue surface a buyer would touch and fails loudly when any
link in the chain breaks: landing page -> CTA -> checkout -> webhook route
-> fulfillment gate. Pure Python, no LLM. Run via:

    python trinity/cron_runner.py funnel-verifier

Checks driven by verifier_manifest.json plus two automatic sweeps pulled
live from the Stripe API (active payment links, webhook endpoint health).

Exit code 0 = all green, 1 = at least one FAIL (cron-friendly).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import requests

TRINITY_DIR = Path(__file__).parent
MANIFEST_PATH = TRINITY_DIR / "verifier_manifest.json"
REPORT_PATH = TRINITY_DIR / "knowledge" / "funnel-verifier-latest.json"

TIMEOUT = 20
UA = {"User-Agent": "Mozilla/5.0 (OEFR funnel-verifier; +https://oefrenterprise.com)"}

# Hosts we own. A Stripe webhook endpoint pointing anywhere else is a P1:
# payments would fulfil into a stranger's server.
OWNED_HOSTS = (
    ".oefrenterprise.com",
    "netarch-pro.vercel.app",
    "habitforge-nu.vercel.app",
)


@dataclass
class Result:
    name: str
    check: str
    ok: bool
    detail: str = ""


@dataclass
class Report:
    results: list[Result] = field(default_factory=list)

    def add(self, name: str, check: str, ok: bool, detail: str = "") -> None:
        self.results.append(Result(name, check, ok, detail))

    @property
    def failures(self) -> list[Result]:
        return [r for r in self.results if not r.ok]


def _get(url: str) -> requests.Response | None:
    try:
        return requests.get(url, timeout=TIMEOUT, headers=UA, allow_redirects=True)
    except requests.RequestException:
        return None


def check_page(report: Report, name: str, url: str, must_contain: list[str]) -> None:
    r = _get(url)
    if r is None or r.status_code != 200:
        code = r.status_code if r is not None else "unreachable"
        report.add(name, f"page {url}", False, f"HTTP {code}")
        return
    missing = [s for s in must_contain if s not in r.text]
    if missing:
        report.add(name, f"page {url}", False, f"missing content: {missing}")
    else:
        report.add(name, f"page {url}", True)


def check_gumroad_product(report: Report, name: str, url: str, price: str) -> None:
    """Gumroad renders the buy UI client-side; the server HTML carries
    og meta tags. product:price:amount + the Products/Show component
    prove a live, purchasable listing at the expected price."""
    r = _get(url)
    if r is None or r.status_code != 200:
        code = r.status_code if r is not None else "unreachable"
        report.add(name, f"gumroad {url}", False, f"HTTP {code}")
        return
    problems = []
    if f'property="product:price:amount" content="{price}"' not in r.text:
        problems.append(f"price meta != {price}")
    if "Products/Show" not in r.text:
        problems.append("not a live product page")
    report.add(name, f"gumroad {url}", not problems, "; ".join(problems))


def check_webhook_route(report: Report, name: str, url: str) -> None:
    """POST an unsigned body. Our Next.js routes reject with 400 +
    'Webhook configuration error' / signature error. A 404, 5xx, or a
    foreign HTML page means fulfillment is broken for this product."""
    try:
        r = requests.post(url, json={}, timeout=TIMEOUT, headers=UA)
    except requests.RequestException as e:
        report.add(name, f"webhook {url}", False, f"unreachable: {e}")
        return
    ours = r.status_code in (400, 401, 403, 405) and "<html" not in r.text[:200].lower()
    detail = f"HTTP {r.status_code}: {r.text[:80]}"
    report.add(name, f"webhook {url}", ours, "" if ours else detail)


def check_download_gate(report: Report, name: str, url: str) -> None:
    """Fulfillment/download route must exist and be gated: 401/403/400/405.
    404 = route missing (nothing to deliver), 5xx = broken."""
    r = _get(url)
    if r is None:
        report.add(name, f"download-gate {url}", False, "unreachable")
        return
    ok = r.status_code in (200, 400, 401, 403, 405)
    report.add(name, f"download-gate {url}", ok, "" if ok else f"HTTP {r.status_code}")


def _stripe_key() -> str:
    key = os.environ.get("STRIPE_SECRET") or os.environ.get("STRIPE_SECRET_KEY", "")
    return key


def check_stripe_webhooks(report: Report) -> None:
    key = _stripe_key()
    if not key:
        report.add("stripe", "webhook-endpoints", False, "STRIPE_SECRET not in env")
        return
    try:
        r = requests.get(
            "https://api.stripe.com/v1/webhook_endpoints?limit=100",
            auth=(key, ""), timeout=TIMEOUT,
        )
        eps = r.json()["data"]
    except Exception as e:
        report.add("stripe", "webhook-endpoints", False, f"API error: {e}")
        return
    for e in eps:
        url = e["url"]
        owned = any(h in url for h in OWNED_HOSTS)
        enabled = e["status"] == "enabled"
        ok = owned and enabled
        detail = "" if ok else f"status={e['status']}, owned_host={owned}"
        report.add("stripe", f"webhook-endpoint {url}", ok, detail)


def check_stripe_payment_links(report: Report) -> None:
    key = _stripe_key()
    if not key:
        return
    try:
        r = requests.get(
            "https://api.stripe.com/v1/payment_links?limit=100&active=true",
            auth=(key, ""), timeout=TIMEOUT,
        )
        links = r.json()["data"]
    except Exception as e:
        report.add("stripe", "payment-links", False, f"API error: {e}")
        return
    for link in links:
        # Plain GET of the hosted page; a dead/deactivated link 404s.
        # Without JS no checkout session is created, so metrics stay clean.
        resp = _get(link["url"])
        ok = resp is not None and resp.status_code == 200
        detail = "" if ok else f"HTTP {resp.status_code if resp else 'unreachable'}"
        report.add("stripe", f"plink {link['id']} {link['url']}", ok, detail)


def run() -> Report:
    report = Report()
    manifest = json.loads(MANIFEST_PATH.read_text())

    for item in manifest["checks"]:
        kind = item["type"]
        name = item["name"]
        if kind == "page":
            check_page(report, name, item["url"], item.get("must_contain", []))
        elif kind == "gumroad_product":
            check_gumroad_product(report, name, item["url"], item["price"])
        elif kind == "webhook_route":
            check_webhook_route(report, name, item["url"])
        elif kind == "download_gate":
            check_download_gate(report, name, item["url"])

    check_stripe_webhooks(report)
    check_stripe_payment_links(report)

    REPORT_PATH.write_text(json.dumps(
        [r.__dict__ for r in report.results], indent=2))
    return report


def main() -> int:
    report = run()
    passed = sum(1 for r in report.results if r.ok)
    print(f"[funnel-verifier] {passed}/{len(report.results)} checks passed")
    for f in report.failures:
        print(f"  FAIL [{f.name}] {f.check} — {f.detail}")
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
