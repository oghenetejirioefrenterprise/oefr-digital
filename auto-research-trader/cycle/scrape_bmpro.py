#!/usr/bin/env python3
"""
Scrape BTC metrics from bitcoinmagazinepro.com via Playwright.
Fetches: MVRV-Z Score, Balanced Price, Realized Price.
Caches results to bmpro_cache.json.
"""
import json
import sys
import subprocess
import os
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).parent
CACHE_FILE = BASE_DIR / "bmpro_cache.json"

# Each chart: URL and trace names to extract (last data point)
CHARTS = [
    ("https://www.bitcoinmagazinepro.com/charts/balanced-price/", "balanced_price"),
    ("https://www.bitcoinmagazinepro.com/charts/mvrv-zscore/", "mvrv_zscore"),
    ("https://www.bitcoinmagazinepro.com/charts/realized-price/", "realized_price"),
]


def scrape_chart(url, key):
    """Scrape all traces from a Plotly chart, return dict of {trace_name: last_value}."""
    # Build a self-contained Node script with no external variable injection
    script = """
const { chromium } = require('playwright');
(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.goto('""" + url + """', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('.js-plotly-plot', { timeout: 15000 });
    await page.waitForTimeout(3000);
    const data = await page.evaluate(() => {
        const graphs = document.querySelectorAll('.js-plotly-plot');
        if (graphs.length === 0) return null;
        const result = {};
        for (const trace of graphs[0].data) {
            if (trace.y && trace.y.length > 0 && !trace.name.startsWith('lower') && !trace.name.startsWith('upper')) {
                const lastIdx = trace.y.length - 1;
                result[trace.name] = { value: trace.y[lastIdx], date: trace.x[lastIdx] };
            }
        }
        return Object.keys(result).length > 0 ? result : null;
    });
    await browser.close();
    console.log(JSON.stringify(data));
})();
"""
    try:
        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True, text=True, timeout=60,
            env=os.environ.copy(),
            cwd=str(BASE_DIR),
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
        else:
            print(f"[WARN] {key} scrape failed: {result.stderr[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"[WARN] {key} scrape error: {e}", file=sys.stderr)
    return None


def load_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_cache(data):
    data["scraped_at"] = datetime.now(tz=timezone.utc).isoformat()
    data["source"] = "bitcoinmagazinepro.com"
    CACHE_FILE.write_text(json.dumps(data, indent=2))


def get_metrics():
    """Scrape all BM Pro charts, return dict of metrics. Falls back to cache."""
    cache = load_cache()
    metrics = {}
    updated = False

    for url, key in CHARTS:
        print(f"[*] Scraping {key}...")
        data = scrape_chart(url, key)
        if data:
            updated = True
            for trace_name, info in data.items():
                val = round(float(info["value"]), 4)
                metrics[trace_name] = val
                cache[f"{key}_{trace_name}"] = val
                cache[f"{key}_{trace_name}_date"] = info.get("date", "?")
            items = [f"{k}={v['value']:.2f}" for k, v in data.items()]
            print(f"    OK: {', '.join(items)}")
        else:
            print(f"    FAILED — using cache if available")

    if updated:
        save_cache(cache)

    # Fill missing from cache
    for url, key in CHARTS:
        for k, v in cache.items():
            if k.startswith(f"{key}_") and k.endswith("_date"):
                continue
            if k.startswith(f"{key}_") and k not in metrics:
                metrics[k.replace(f"{key}_", "")] = v

    return metrics


if __name__ == "__main__":
    metrics = get_metrics()
    if metrics:
        print(json.dumps(metrics, indent=2))
    else:
        print("[ERROR] No metrics available", file=sys.stderr)
        sys.exit(1)
