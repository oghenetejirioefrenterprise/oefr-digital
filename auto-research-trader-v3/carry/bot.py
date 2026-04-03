#!/usr/bin/env python3
"""Standalone Funding Rate Carry Bot.

Runs independently from directional strategies.
Checks funding rates hourly, enters carry positions when funding is extreme.
"""
import json
import sys
import time
import logging
import signal
import requests
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / 'carry' / 'state.json'
LOG_DIR = ROOT / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

HL_API = 'https://api.hyperliquid.xyz/info'

logger = logging.getLogger('carry_bot')


def setup_logging():
    handler = logging.FileHandler(LOG_DIR / 'carry.jsonl')
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logger.addHandler(console)


def log_event(event, **kwargs):
    entry = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'component': 'carry_bot',
        'event': event,
        **kwargs,
    }
    logger.info(json.dumps(entry))


class CarryBot:
    def __init__(self, dry_run=True, capital=1000):
        self.dry_run = dry_run
        self.capital = capital
        self.position_pct = 0.05  # 5% of equity per carry position
        self.entry_threshold = 30  # 30% annualized
        self.exit_threshold = 5   # +/-5% annualized
        self.max_hold_hours = 168  # 7 days
        self.adverse_reduce_pct = 3.0
        self.adverse_close_pct = 5.0

        # Load config
        config_path = ROOT / 'config' / 'intervals.json'
        with open(config_path) as f:
            config = json.load(f)
        self.coins = config['coins']

        # DB
        from db.store import Store
        self.store = Store()

        self.running = True
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _shutdown(self, signum, frame):
        log_event('shutdown', signal=signum)
        self.running = False

    def _api_call(self, payload):
        for attempt in range(3):
            try:
                resp = requests.post(HL_API, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError):
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)

    def get_funding_rates(self):
        """Get current funding rates from Hyperliquid."""
        data = self._api_call({"type": "metaAndAssetCtxs"})
        if not data or len(data) < 2:
            return {}

        meta = data[0]
        ctxs = data[1]

        rates = {}
        if 'universe' in meta:
            for i, asset in enumerate(meta['universe']):
                if i < len(ctxs):
                    coin = asset['name']
                    if coin in self.coins:
                        rates[coin] = {
                            'funding': float(ctxs[i].get('funding', 0)),
                            'mark_price': float(ctxs[i].get('markPx', 0)),
                            'open_interest': float(ctxs[i].get('openInterest', 0)),
                        }
        return rates

    def get_recent_funding_avg(self, coin, hours=8):
        """Get rolling average funding from stored data."""
        import csv
        path = ROOT / 'data' / 'funding' / f'{coin}_funding.csv'
        if not path.exists():
            return None

        rates = []
        with open(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                rates.append(float(row['funding_rate']))

        if len(rates) < hours:
            return None

        return sum(rates[-hours:]) / hours

    def annualize(self, hourly_rate):
        """Convert hourly funding rate to annualized %."""
        return hourly_rate * 24 * 365 * 100

    def check_entries(self, rates):
        """Check for new carry entry opportunities."""
        open_trades = self.store.get_open_carry_trades()
        open_coins = {dict(t)['coin'] for t in open_trades}

        for coin, data in rates.items():
            if coin in open_coins:
                continue  # Already have a position

            avg_rate = self.get_recent_funding_avg(coin, hours=8)
            if avg_rate is None:
                avg_rate = data['funding']

            ann_funding = self.annualize(avg_rate)

            if abs(ann_funding) > self.entry_threshold:
                direction = 'SHORT' if ann_funding > 0 else 'LONG'
                entry_price = data['mark_price']
                size = self.capital * self.position_pct

                log_event('entry_signal', coin=coin, direction=direction,
                         ann_funding=round(ann_funding, 2), entry_price=entry_price)

                if self.dry_run:
                    trade_id = self.store.log_carry_open(
                        coin, direction, entry_price, size)
                    log_event('carry_opened', trade_id=trade_id, coin=coin,
                             direction=direction, size=round(size, 2))
                else:
                    log_event('would_enter', coin=coin, direction=direction,
                             note='live trading not implemented yet')

    def check_exits(self, rates):
        """Check exit conditions for open carry positions."""
        open_trades = self.store.get_open_carry_trades()

        for trade in open_trades:
            trade = dict(trade)
            coin = trade['coin']

            if coin not in rates:
                continue

            data = rates[coin]
            current_price = data['mark_price']
            entry_price = trade['entry_price']

            avg_rate = self.get_recent_funding_avg(coin, hours=8)
            if avg_rate is None:
                avg_rate = data['funding']

            ann_funding = self.annualize(avg_rate)

            # Track funding collected (approximate)
            hourly_funding = data['funding'] * trade['position_size']
            if trade['direction'] == 'SHORT':
                funding = trade['funding_collected'] + hourly_funding
            else:
                funding = trade['funding_collected'] - hourly_funding

            # Adverse price movement
            if trade['direction'] == 'SHORT':
                adverse_pct = (current_price - entry_price) / entry_price * 100
            else:
                adverse_pct = (entry_price - current_price) / entry_price * 100

            # Update tracking
            self.store.update_carry(trade['id'], funding, max(adverse_pct, 0))

            # Check exit conditions
            exit_reason = None

            if abs(ann_funding) < self.exit_threshold:
                exit_reason = 'funding_normalized'

            # Hold time check (approximate from opened_at)
            if trade.get('opened_at'):
                ts_str = trade['opened_at']
                if 'Z' in ts_str:
                    ts_str = ts_str.replace('Z', '+00:00')
                opened = datetime.fromisoformat(ts_str)
                # Ensure timezone-aware — if naive, assume UTC (SQLite CURRENT_TIMESTAMP)
                if opened.tzinfo is None:
                    opened = opened.replace(tzinfo=timezone.utc)
                hours_held = (datetime.now(timezone.utc) - opened).total_seconds() / 3600
                if hours_held >= self.max_hold_hours:
                    exit_reason = 'max_hold'

            if adverse_pct > self.adverse_close_pct:
                exit_reason = 'adverse_close'

            if exit_reason:
                self.store.close_carry(trade['id'], exit_reason)
                log_event('carry_closed', trade_id=trade['id'], coin=coin,
                         exit_reason=exit_reason, funding=round(funding, 4),
                         adverse_pct=round(adverse_pct, 2))

    def run_once(self):
        """Run one cycle of carry bot."""
        try:
            rates = self.get_funding_rates()
            if not rates:
                log_event('no_rates')
                return

            self.check_exits(rates)
            self.check_entries(rates)

            # Log status
            open_trades = self.store.get_open_carry_trades()
            total_funding = sum(dict(t).get('funding_collected', 0) for t in open_trades)
            log_event('cycle_complete', open_positions=len(open_trades),
                     total_funding=round(total_funding, 4))

        except Exception as e:
            log_event('error', error=str(e))

    def run_loop(self, interval_seconds=3600):
        """Run carry bot continuously."""
        log_event('start', dry_run=self.dry_run, capital=self.capital)

        while self.running:
            self.run_once()

            # Sleep until next hour
            for _ in range(interval_seconds):
                if not self.running:
                    break
                time.sleep(1)

        log_event('stopped')


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--capital', type=float, default=1000)
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    args = parser.parse_args()

    setup_logging()
    bot = CarryBot(dry_run=args.dry_run, capital=args.capital)

    if args.once:
        bot.run_once()
    else:
        bot.run_loop()


if __name__ == '__main__':
    main()
