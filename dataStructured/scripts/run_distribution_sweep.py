#!/usr/bin/env python3
"""Run full distribution sweep — post all unposted (item, channel) pairs.

Reads distribution-queue.json and distribution-log.json, identifies unposted items,
and posts them via browser-use scripts (Twitter + Reddit).

Writes cycle report to state/distribution-report-{today}.md.
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from scripts.lib.distribution_log import already_posted

VENV_PYTHON = Path.home() / "venvs" / "oefr" / "bin" / "python3"
QUEUE_PATH = BASE / "state" / "distribution-queue.json"
LOG_PATH = BASE / "state" / "distribution-log.json"


# Map products to relevant subreddits
SUBREDDIT_MAP = {
    "fmcsa": ["r/Truckers", "r/FreightBrokers"],
    "florida.*llc|business.*formation": ["r/smallbusiness", "r/Entrepreneur"],
    "samgov|contractor": ["r/govcontracting", "r/Entrepreneur"],
    "real.*estate": ["r/realtors", "r/RealEstate"],
    "home.*health": ["r/homehealth", "r/HealthIT"],
    "aircraft": ["r/aviation"],
    "alcohol|beverage|bar": ["r/bartenders", "r/restaurateur"],
    "physical.*therapist": ["r/physicaltherapy"],
    "electrician": ["r/electricians"],
    "hvac": ["r/HVAC"],
    "contractor.*california": ["r/Construction"],
    "dentist": ["r/Dentistry"],
    "ria|investment.*adviser": ["r/FinancialPlanning", "r/personalfinance"],
}


def get_target_subreddits(product: dict) -> list[str]:
    """Return target subreddits for a product based on name/slug."""
    import re
    name = product.get("name", "").lower()
    slug = product.get("slug", "").lower()
    text = f"{name} {slug}"

    subreddits = []
    for pattern, subs in SUBREDDIT_MAP.items():
        if re.search(pattern, text):
            subreddits.extend(subs)

    # Always add r/Entrepreneur as a fallback
    if not subreddits:
        subreddits.append("r/Entrepreneur")
    elif "r/Entrepreneur" not in subreddits:
        subreddits.append("r/Entrepreneur")

    return list(set(subreddits))  # dedupe


def post_twitter(item_id: str) -> dict:
    """Post to Twitter. Returns result dict."""
    print(f"  [Twitter] Posting {item_id}...")
    result = subprocess.run(
        [str(VENV_PYTHON), "scripts/post_twitter_browseruse.py", item_id],
        cwd=str(BASE),
        capture_output=True,
        text=True,
        timeout=180,
    )
    return {
        "channel": "twitter",
        "status": "posted" if result.returncode == 0 else "failed",
        "output": result.stdout + result.stderr,
    }


def post_reddit(item_id: str, subreddit: str) -> dict:
    """Post to Reddit. Returns result dict."""
    print(f"  [Reddit {subreddit}] Posting {item_id}...")
    result = subprocess.run(
        [str(VENV_PYTHON), "scripts/post_reddit_browseruse.py", item_id, subreddit],
        cwd=str(BASE),
        capture_output=True,
        text=True,
        timeout=180,
    )
    return {
        "channel": f"reddit:{subreddit}",
        "status": "posted" if result.returncode == 0 else "failed",
        "output": result.stdout + result.stderr,
    }


def main():
    print("\n" + "="*80)
    print("DATASTRUCTURED DISTRIBUTION SWEEP")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    # Load queue
    if not QUEUE_PATH.exists():
        print(f"ERROR: distribution queue not found at {QUEUE_PATH}", file=sys.stderr)
        sys.exit(1)

    queue = json.loads(QUEUE_PATH.read_text())
    products = queue.get("items", [])

    sweep_results = []
    total_attempts = 0
    total_posted = 0
    total_failed = 0
    total_skipped = 0

    for product in products:
        item_id = product.get("id")
        name = product.get("name", "")
        if not item_id or not product.get("slug"):
            print(f"   ⚠️  Skipping malformed queue item (missing id/slug): {item_id or name[:40] or '?'}")
            continue

        print(f"\n📦 {name[:70]}")
        print(f"   ID: {item_id}")

        product_results = []

        # Twitter
        if not already_posted(BASE, item_id, "twitter"):
            try:
                result = post_twitter(item_id)
                product_results.append(result)
                total_attempts += 1
                if result["status"] == "posted":
                    print("   ✓ Twitter posted")
                    total_posted += 1
                else:
                    print(f"   ✗ Twitter failed: {result['output'][:100]}")
                    total_failed += 1
            except Exception as exc:
                print(f"   ✗ Twitter error: {exc}")
                product_results.append({"channel": "twitter", "status": "failed", "output": str(exc)})
                total_attempts += 1
                total_failed += 1
        else:
            print("   ○ Twitter already posted")
            total_skipped += 1

        # Reddit
        target_subs = get_target_subreddits(product)
        for sub in target_subs:
            channel = f"reddit:{sub}"
            if not already_posted(BASE, item_id, channel):
                try:
                    result = post_reddit(item_id, sub)
                    product_results.append(result)
                    total_attempts += 1
                    if result["status"] == "posted":
                        print(f"   ✓ {sub} posted")
                        total_posted += 1
                    else:
                        print(f"   ✗ {sub} failed: {result['output'][:100]}")
                        total_failed += 1
                except Exception as exc:
                    print(f"   ✗ {sub} error: {exc}")
                    product_results.append({"channel": channel, "status": "failed", "output": str(exc)})
                    total_attempts += 1
                    total_failed += 1
            else:
                print(f"   ○ {sub} already posted")
                total_skipped += 1

        sweep_results.append({
            "product": name,
            "item_id": item_id,
            "results": product_results,
        })

    # Write cycle report
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = BASE / "state" / f"distribution-report-{today}.md"

    report = f"""# Distribution Cycle Report — {today}

## Summary

- **Total attempts:** {total_attempts}
- **Posted:** {total_posted}
- **Failed:** {total_failed}
- **Skipped (already posted):** {total_skipped}

## Results by Product

"""

    for item in sweep_results:
        report += f"\n### {item['product']}\n\n"
        report += f"**ID:** `{item['item_id']}`\n\n"

        if not item['results']:
            report += "All channels already posted.\n\n"
            continue

        for r in item['results']:
            status_icon = "✓" if r['status'] == "posted" else "✗"
            report += f"- {status_icon} **{r['channel']}**: {r['status']}\n"
            if r['status'] == "failed" and r['output']:
                report += f"  ```\n  {r['output'][:200]}...\n  ```\n"

    report += f"\n\n---\n\n**Generated:** {datetime.now().isoformat()}\n"

    report_path.write_text(report)
    print(f"\n\n{'='*80}")
    print(f"Cycle complete. Report written to: {report_path}")
    print(f"Posted: {total_posted} | Failed: {total_failed} | Skipped: {total_skipped}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
