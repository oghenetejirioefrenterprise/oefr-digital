#!/usr/bin/env python3
"""
Scrape the current BTC Balanced Price from bitcoinmagazinepro.com.
Uses Playwright to render the Dash/Plotly chart and extract the last data point.
Falls back to cached value if scraping fails.

Usage:
  python3 scrape_balanced_price.py          # scrape and print
  python3 scrape_balanced_price.py --save   # scrape and save to balanced_price.json
"""
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone

CACHE_FILE = Path(__file__).parent / "balanced_price_cache.json"


def scrape_with_playwright():
    """Use Playwright headless to extract balanced price from Plotly chart."""
    script = """
    const { chromium } = require('playwright');
    (async () => {
        const browser = await chromium.launch({ headless: true });
        const page = await browser.newPage();
        await page.goto('https://www.bitcoinmagazinepro.com/charts/balanced-price/', {
            waitUntil: 'networkidle',
            timeout: 30000
        });
        // Wait for Plotly chart to render
        await page.waitForSelector('.js-plotly-plot', { timeout: 15000 });
        await page.waitForTimeout(3000);
        // Extract last data point from Balanced Price trace
        const data = await page.evaluate(() => {
            const graphs = document.querySelectorAll('.js-plotly-plot');
            if (graphs.length === 0) return null;
            const plotData = graphs[0].data;
            for (const trace of plotData) {
                if (trace.name === 'Balanced Price' && trace.y && trace.y.length > 0) {
                    const lastIdx = trace.y.length - 1;
                    return {
                        balanced_price: trace.y[lastIdx],
                        date: trace.x[lastIdx]
                    };
                }
            }
            return null;
        });
        await browser.close();
        console.log(JSON.stringify(data));
    })();
    """
    try:
        result = subprocess.run(
            ['node', '-e', script],
            capture_output=True, text=True, timeout=45,
            env={**__import__('os').environ}
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            if data and data.get('balanced_price'):
                return float(data['balanced_price']), data.get('date', 'unknown')
    except Exception as e:
        print(f"[WARN] Playwright scrape failed: {e}", file=sys.stderr)
    return None, None


def scrape_with_firecrawl():
    """Fallback: try to extract from firecrawl scrape (may not work for JS-rendered content)."""
    try:
        # This won't work for Plotly charts but worth a try
        import requests
        r = requests.get(
            'https://www.bitcoinmagazinepro.com/charts/balanced-price/',
            timeout=15,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        # Look for any inline data with balanced price values
        import re
        # Search for JSON data in script tags
        matches = re.findall(r'"Balanced Price".*?"y":\s*([\d.]+)', r.text)
        if matches:
            return float(matches[-1]), 'from-html'
    except Exception:
        pass
    return None, None


def load_cache():
    """Load cached balanced price."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass
    return None


def save_cache(price, date_str):
    """Save balanced price to cache."""
    data = {
        "balanced_price": round(price, 2),
        "date": date_str,
        "scraped_at": datetime.now(tz=timezone.utc).isoformat()
    }
    CACHE_FILE.write_text(json.dumps(data, indent=2))


def get_balanced_price():
    """Get balanced price: try scraping, fall back to cache."""
    # Try Playwright first
    price, date_str = scrape_with_playwright()
    if price:
        print(f"[*] Scraped balanced price: ${price:,.2f} (date: {date_str})")
        save_cache(price, date_str)
        return price, date_str

    # Try firecrawl fallback
    price, date_str = scrape_with_firecrawl()
    if price:
        print(f"[*] Scraped balanced price (fallback): ${price:,.2f}")
        save_cache(price, date_str)
        return price, date_str

    # Fall back to cache
    cache = load_cache()
    if cache:
        age = datetime.now(tz=timezone.utc) - datetime.fromisoformat(cache['scraped_at'])
        print(f"[*] Using cached balanced price: ${cache['balanced_price']:,.2f} (age: {age.days}d)")
        return cache['balanced_price'], cache.get('date', 'cached')

    print("[WARN] No balanced price available", file=sys.stderr)
    return None, None


if __name__ == '__main__':
    price, date_str = get_balanced_price()
    if price:
        save = '--save' in sys.argv
        print(json.dumps({
            "balanced_price": round(price, 2),
            "date": date_str,
            "saved": save
        }, indent=2))
    else:
        sys.exit(1)
