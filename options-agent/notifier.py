"""
notifier.py — Telegram notifications
Sends trade alerts, daily P&L summaries, and error reports to TJ.
"""

import logging
import requests
import config

log = logging.getLogger("notifier")


class Notifier:
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)
        self._last_send_time = 0
        self._min_interval = 1.0  # minimum seconds between messages
        if not self.enabled:
            log.warning("Telegram not configured — notifications disabled")

    def send(self, message: str):
        if not self.enabled:
            log.info(f"[NOTIFY] {message}")
            return
        import time
        now = time.time()
        elapsed = now - self._last_send_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_send_time = time.time()
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            requests.post(url, json={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
            }, timeout=10)
        except Exception as e:
            log.warning(f"Telegram send failed: {e}")

    def trade_entered(self, position: dict):
        strat = position.get("strategy", "UNKNOWN")
        exp = position.get("expiration", "")
        qty = position.get("qty", 1)

        try:
            if strat == "BWB":
                # BWB uses: strike_high, strike_mid, strike_low
                credit = position.get("net_credit", 0)
                strike_h = position.get("strike_high", "?")
                strike_m = position.get("strike_mid", "?")
                strike_l = position.get("strike_low", "?")
                max_prof = position.get("max_profit", 0)
                msg = (
                    f"\U0001f7e2 <b>BWB Entered</b>\n"
                    f"Exp: {exp}\n"
                    f"Long: {strike_h}P | Short: {strike_m}Px2 | Wing: {strike_l}P\n"
                    f"Net Credit: ${credit*100:.0f}\n"
                    f"Max Profit: ${max_prof*100:.0f}"
                )
            elif strat == "CONDOR":
                credit = position.get("net_credit", 0)
                msg = (
                    f"🟢 <b>CONDOR Entered (0DTE)</b>\n"
                    f"Exp: {exp}\n"
                    f"Put spread: {position.get('long_put_strike','?')}/{position.get('short_put_strike','?')}\n"
                    f"Call spread: {position.get('short_call_strike','?')}/{position.get('long_call_strike','?')}\n"
                    f"Net Credit: ${credit*100:.0f}"
                )
            elif strat == "CALL_SPREAD":
                debit = position.get("net_debit", 0)
                max_prof = position.get("max_profit", 0)
                msg = (
                    f"🟢 <b>CALL_SPREAD Entered</b>\n"
                    f"Exp: {exp} | Qty: {qty}\n"
                    f"Long: {position.get('long_strike','?')}C | Short: {position.get('short_strike','?')}C\n"
                    f"Net Debit: ${debit*100:.0f}\n"
                    f"Max Profit: ${max_prof*100:.0f}"
                )
            elif strat == "LONG_CALL":
                premium = position.get("premium", 0)
                msg = (
                    f"🚀 <b>LONG_CALL Entered</b>\n"
                    f"Exp: {exp} | Qty: {qty}\n"
                    f"Strike: {position.get('strike','?')}C\n"
                    f"Premium: ${premium*100:.0f}\n"
                    f"Target: 75% gain (${premium*175:.0f})"
                )
            elif strat == "PUT_CREDIT_SPREAD":
                # PUT_CREDIT_SPREAD uses: short_strike, long_strike (NOT BWB keys)
                credit = position.get("net_credit", 0)
                msg = (
                    f"🟢 <b>PUT_CREDIT_SPREAD Entered</b>\n"
                    f"Exp: {exp} | Qty: {qty}\n"
                    f"Sell: {position.get('short_strike','?')}P | Buy: {position.get('long_strike','?')}P\n"
                    f"Net Credit: ${credit*100:.0f}\n"
                    f"Max Loss: ${position.get('max_loss', 0)*100:.0f}"
                )
            elif strat == "CALENDAR_SPREAD":
                debit = position.get("net_debit", 0)
                msg = (
                    f"🟢 <b>CALENDAR_SPREAD Entered</b>\n"
                    f"Front: {position.get('front_exp','?')} | Back: {position.get('back_exp','?')}\n"
                    f"Strike: {position.get('strike','?')}{position.get('right','P')} | Qty: {qty}\n"
                    f"Net Debit: ${debit*100:.0f}"
                )
            elif strat == "JADE_LIZARD":
                credit = position.get("net_credit", 0)
                msg = (
                    f"🟢 <b>JADE_LIZARD Entered</b>\n"
                    f"Exp: {exp} | Qty: {qty}\n"
                    f"Sell: {position.get('short_put_strike','?')}P + {position.get('short_call_strike','?')}C\n"
                    f"Buy: {position.get('long_call_strike','?')}C\n"
                    f"Total Credit: ${credit*100:.0f}\n"
                    f"No Upside Risk: {position.get('no_upside_risk', False)}"
                )
            else:
                msg = (
                    f"🟢 <b>{strat} Entered</b>\n"
                    f"Exp: {exp} | Qty: {qty}"
                )
            self.send(msg)
        except Exception as e:
            # Defensive fallback - log error but still notify
            log.warning(f"Notifier trade_entered formatting error for {strat}: {e}")
            fallback_msg = (
                f"🟢 <b>{strat} Entered</b>\n"
                f"Exp: {exp} | Qty: {qty}\n"
                f"(details unavailable)"
            )
            self.send(fallback_msg)

    def trade_exited(self, position: dict, reason: str, pnl: float):
        strat = position.get("strategy", "UNKNOWN")
        emoji = "\u2705" if pnl > 0 else "\U0001f534"

        try:
            strikes = ""
            if strat == "BWB":
                # BWB keys: strike_high, strike_mid, strike_low
                strikes = (
                    f"Strikes: {position.get('strike_high', '?')}/"
                    f"{position.get('strike_mid', '?')}x2/"
                    f"{position.get('strike_low', '?')}\n"
                )
            elif strat == "CONDOR":
                strikes = (
                    f"Put: {position.get('long_put_strike', '?')}/{position.get('short_put_strike', '?')} "
                    f"Call: {position.get('short_call_strike', '?')}/{position.get('long_call_strike', '?')}\n"
                )
            elif strat == "CALL_SPREAD":
                strikes = (
                    f"Spread: {position.get('long_strike', '?')}C/"
                    f"{position.get('short_strike', '?')}C\n"
                )
            elif strat == "LONG_CALL":
                strikes = f"Strike: {position.get('strike', '?')}C\n"
            elif strat == "PUT_CREDIT_SPREAD":
                # PUT_CREDIT_SPREAD keys: short_strike, long_strike
                strikes = (
                    f"Spread: sell {position.get('short_strike', '?')}P / "
                    f"buy {position.get('long_strike', '?')}P\n"
                )
            elif strat == "CALENDAR_SPREAD":
                strikes = (
                    f"Strike: {position.get('strike', '?')}{position.get('right', 'P')}\n"
                    f"Front: {position.get('front_exp', '?')} Back: {position.get('back_exp', '?')}\n"
                )
            elif strat == "JADE_LIZARD":
                strikes = (
                    f"Put: {position.get('short_put_strike', '?')}P "
                    f"Call: {position.get('short_call_strike', '?')}C/"
                    f"{position.get('long_call_strike', '?')}C\n"
                )
            msg = (
                f"{emoji} <b>{strat} Closed</b>\n"
                f"{strikes}"
                f"Reason: {reason}\n"
                f"P&L: ${pnl:+.2f}\n"
                f"Exp: {position.get('expiration', '')}"
            )
            self.send(msg)
        except Exception as e:
            log.warning(f"Notifier trade_exited formatting error for {strat}: {e}")
            fallback_msg = (
                f"{emoji} <b>{strat} Closed</b>\n"
                f"Reason: {reason}\n"
                f"P&L: ${pnl:+.2f}"
            )
            self.send(fallback_msg)

    def daily_summary(self, daily_pnl: float, trades_today: int, wins: int, losses: int):
        emoji = "📈" if daily_pnl > 0 else "📉"
        msg = (
            f"{emoji} <b>Daily Summary</b>\n"
            f"P&L: ${daily_pnl:+.2f}\n"
            f"Trades: {trades_today} ({wins}W / {losses}L)\n"
            f"{'🎯 Target range hit!' if daily_pnl > 0 else '📊 Live to trade tomorrow'}"
        )
        self.send(msg)

    def error(self, message: str):
        self.send(f"⚠️ <b>Agent Error</b>\n{message}")

    def risk_breach(self, message: str):
        self.send(f"🚨 <b>RISK BREACH</b>\n{message}\nTrading halted for today.")

    def heartbeat(self, status: str):
        self.send(f"💓 Agent alive | {status}")

    def smb_score(self, score: int, regime: str, checks: dict):
        regime_emoji = {"BREAKOUT": "🚀", "MODERATE": "📈", "RANGE": "📊", "FLAT": "😴"}.get(regime, "📊")
        bar = "█" * score + "░" * (10 - score)
        checks_fmt = "\n".join(
            f"  {'✅' if v >= 1 else ('🟡' if v >= 0.5 else '❌')} {k.replace('_', ' ').title()}"
            for k, v in checks.items()
        )
        msg = (
            f"{regime_emoji} <b>SMB Score: {score}/10 — {regime}</b>\n"
            f"[{bar}]\n\n"
            f"{checks_fmt}"
        )
        self.send(msg)
