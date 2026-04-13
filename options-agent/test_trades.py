"""
test_trades.py — End-to-end trade test on paper account.
Opens one position per strategy, waits 5 minutes, closes all.
"""
import os
import sys
import time
import logging

os.environ.setdefault("DATA_DIR", "/tmp/test_data")
os.environ.setdefault("LOG_DIR", "/tmp/test_logs")
os.environ.setdefault("DRY_RUN", "false")
os.environ.setdefault("MARKET_DATA_TYPE", "3")
os.makedirs("/tmp/test_data", exist_ok=True)
os.makedirs("/tmp/test_logs", exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("test_trades")

import config
from broker import IBKRBroker

# Override config for test
config.DRY_RUN = False

def main():
    broker = IBKRBroker()

    log.info("=" * 60)
    log.info("TRADE TEST — Paper Account")
    log.info(f"DRY_RUN: {config.DRY_RUN}")
    log.info("=" * 60)

    # Connect
    log.info("Connecting to IBKR...")
    try:
        broker.connect(retries=3, delay=5)
    except Exception as e:
        log.error(f"Could not connect: {e}")
        sys.exit(1)

    log.info("Connected. Getting SPX price...")
    try:
        price = broker.get_underlying_price()
        log.info(f"SPX price: {price}")
    except Exception as e:
        log.error(f"Could not get price: {e}")
        broker.disconnect()
        sys.exit(1)

    # Get IV
    from pricing import get_broker_iv, black_scholes, get_strike_from_delta, dte_to_years
    iv = get_broker_iv(broker)
    log.info(f"IV: {iv*100:.1f}%")

    # Find 7 DTE expiration
    exps = broker.get_expirations(dte_min=5, dte_max=10)
    if not exps:
        log.error("No expirations found")
        broker.disconnect()
        sys.exit(1)
    exp = exps[0]
    log.info(f"Using expiration: {exp}")

    from datetime import datetime, date
    exp_date = datetime.strptime(exp, "%Y%m%d").date()
    dte = (exp_date - date.today()).days
    T = dte_to_years(dte)

    from ib_insync import Option

    positions = []

    # ── 1. PUT CREDIT SPREAD ──
    log.info("\n--- PUT CREDIT SPREAD ---")
    try:
        short_strike = get_strike_from_delta(broker, price, T, iv, -0.30, "P")
        short_strike = round(short_strike / 5) * 5
        long_strike = short_strike - 10

        opt_short = Option(config.UNDERLYING, exp, short_strike, "P", config.EXCHANGE)
        opt_long = Option(config.UNDERLYING, exp, long_strike, "P", config.EXCHANGE)
        broker.ib.qualifyContracts(opt_short)
        broker.ib.qualifyContracts(opt_long)

        p_s = black_scholes(price, short_strike, T, iv, right="P")["price"]
        p_l = black_scholes(price, long_strike, T, iv, right="P")["price"]
        credit = p_s - p_l

        from broker import _snap_to_tick
        limit = _snap_to_tick(-(credit - 0.05))

        legs = [(opt_short.conId, 1, "SELL"), (opt_long.conId, 1, "BUY")]
        log.info(f"PCS: sell {short_strike}P / buy {long_strike}P | credit=${credit*100:.0f} | limit={limit}")
        trade = broker.place_combo_order(legs=legs, limit_price=limit, qty=1, tag="TEST-PCS")
        positions.append({"name": "PCS", "legs": [(opt_short.conId, 1, "BUY"), (opt_long.conId, 1, "SELL")], "trade": trade})
        log.info(f"PCS order placed!")
    except Exception as e:
        log.error(f"PCS failed: {e}", exc_info=True)

    # ── 2. CALL SPREAD ──
    log.info("\n--- CALL SPREAD ---")
    try:
        long_call_strike = round(price / 5) * 5  # ATM
        short_call_strike = long_call_strike + 15

        opt_lc = Option(config.UNDERLYING, exp, long_call_strike, "C", config.EXCHANGE)
        opt_sc = Option(config.UNDERLYING, exp, short_call_strike, "C", config.EXCHANGE)
        broker.ib.qualifyContracts(opt_lc)
        broker.ib.qualifyContracts(opt_sc)

        c_l = black_scholes(price, long_call_strike, T, iv, right="C")["price"]
        c_s = black_scholes(price, short_call_strike, T, iv, right="C")["price"]
        debit = c_l - c_s

        limit = _snap_to_tick(debit + 0.05)

        legs = [(opt_lc.conId, 1, "BUY"), (opt_sc.conId, 1, "SELL")]
        log.info(f"CS: buy {long_call_strike}C / sell {short_call_strike}C | debit=${debit*100:.0f} | limit={limit}")
        trade = broker.place_combo_order(legs=legs, limit_price=limit, qty=1, tag="TEST-CS")
        positions.append({"name": "CS", "legs": [(opt_lc.conId, 1, "SELL"), (opt_sc.conId, 1, "BUY")], "trade": trade})
        log.info(f"CS order placed!")
    except Exception as e:
        log.error(f"CS failed: {e}", exc_info=True)

    # ── 3. BWB ──
    log.info("\n--- BWB ---")
    try:
        strike_mid = get_strike_from_delta(broker, price, T, iv, -0.20, "P")
        strike_mid = round(strike_mid / 5) * 5
        strike_high = strike_mid + 20
        strike_low = strike_mid - 25

        opt_h = Option(config.UNDERLYING, exp, strike_high, "P", config.EXCHANGE)
        opt_m = Option(config.UNDERLYING, exp, strike_mid, "P", config.EXCHANGE)
        opt_l = Option(config.UNDERLYING, exp, strike_low, "P", config.EXCHANGE)
        broker.ib.qualifyContracts(opt_h)
        broker.ib.qualifyContracts(opt_m)
        broker.ib.qualifyContracts(opt_l)

        p_h = black_scholes(price, strike_high, T, iv, right="P")["price"]
        p_m = black_scholes(price, strike_mid, T, iv, right="P")["price"]
        p_lo = black_scholes(price, strike_low, T, iv, right="P")["price"]
        credit = 2 * p_m - p_h - p_lo

        limit = _snap_to_tick(-(credit - 0.05))

        legs = [(opt_h.conId, 1, "BUY"), (opt_m.conId, 2, "SELL"), (opt_l.conId, 1, "BUY")]
        log.info(f"BWB: {strike_high}P / {strike_mid}Px2 / {strike_low}P | credit=${credit*100:.0f} | limit={limit}")
        trade = broker.place_combo_order(legs=legs, limit_price=limit, qty=1, tag="TEST-BWB")
        positions.append({"name": "BWB", "legs": [(opt_h.conId, 1, "SELL"), (opt_m.conId, 2, "BUY"), (opt_l.conId, 1, "SELL")], "trade": trade})
        log.info(f"BWB order placed!")
    except Exception as e:
        log.error(f"BWB failed: {e}", exc_info=True)

    # ── 4. JADE LIZARD ──
    log.info("\n--- JADE LIZARD ---")
    try:
        short_put = get_strike_from_delta(broker, price, T, iv, -0.20, "P")
        short_put = round(short_put / 5) * 5
        short_call = get_strike_from_delta(broker, price, T, iv, 0.15, "C")
        short_call = round(short_call / 5) * 5
        long_call = short_call + 10

        opt_sp = Option(config.UNDERLYING, exp, short_put, "P", config.EXCHANGE)
        opt_sc2 = Option(config.UNDERLYING, exp, short_call, "C", config.EXCHANGE)
        opt_lc2 = Option(config.UNDERLYING, exp, long_call, "C", config.EXCHANGE)
        broker.ib.qualifyContracts(opt_sp)
        broker.ib.qualifyContracts(opt_sc2)
        broker.ib.qualifyContracts(opt_lc2)

        p_put = black_scholes(price, short_put, T, iv, right="P")["price"]
        p_sc = black_scholes(price, short_call, T, iv, right="C")["price"]
        p_lc = black_scholes(price, long_call, T, iv, right="C")["price"]
        total_credit = p_put + (p_sc - p_lc)

        limit = _snap_to_tick(-(total_credit - 0.05))

        legs = [(opt_sp.conId, 1, "SELL"), (opt_sc2.conId, 1, "SELL"), (opt_lc2.conId, 1, "BUY")]
        log.info(f"JL: sell {short_put}P + sell {short_call}C / buy {long_call}C | credit=${total_credit*100:.0f} | limit={limit}")
        trade = broker.place_combo_order(legs=legs, limit_price=limit, qty=1, tag="TEST-JL")
        positions.append({"name": "JL", "legs": [(opt_sp.conId, 1, "BUY"), (opt_sc2.conId, 1, "BUY"), (opt_lc2.conId, 1, "SELL")], "trade": trade})
        log.info(f"JL order placed!")
    except Exception as e:
        log.error(f"JL failed: {e}", exc_info=True)

    log.info(f"\n{'=' * 60}")
    log.info(f"Opened {len(positions)} positions. Waiting 5 minutes...")
    log.info(f"{'=' * 60}")

    # Wait 5 minutes
    for i in range(5, 0, -1):
        log.info(f"  {i} minutes remaining...")
        time.sleep(60)

    # ── CLOSE ALL ──
    log.info(f"\n{'=' * 60}")
    log.info(f"Closing all {len(positions)} positions...")
    log.info(f"{'=' * 60}")

    for pos in positions:
        try:
            log.info(f"\nClosing {pos['name']}...")
            # Use market-ish price (0.05 limit for credits, generous for debits)
            close_trade = broker.place_combo_order(
                legs=pos["legs"],
                limit_price=_snap_to_tick(0.10),
                qty=1,
                tag=f"TEST-{pos['name']}-CLOSE",
            )
            log.info(f"{pos['name']} close order placed!")
        except Exception as e:
            log.error(f"Failed to close {pos['name']}: {e}")

    time.sleep(5)
    log.info("\nDone! Check IBKR paper account for orders.")
    broker.disconnect()


if __name__ == "__main__":
    main()
