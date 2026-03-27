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
        if not self.enabled:
            log.warning("Telegram not configured — notifications disabled")

    def send(self, message: str):
        if not self.enabled:
            log.info(f"[NOTIFY] {message}")
            return
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
        strat = position["strategy"]
        exp = position.get("expiration", "")
        credit = position.get("net_credit", 0)
        if strat == "BWB":
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
        else:
            msg = (
                f"🟢 <b>CONDOR Entered (0DTE)</b>\n"
                f"Exp: {exp}\n"
                f"Put spread: {position.get('long_put_strike','?')}/{position.get('short_put_strike','?')}\n"
                f"Call spread: {position.get('short_call_strike','?')}/{position.get('long_call_strike','?')}\n"
                f"Net Credit: ${credit*100:.0f}"
            )
        self.send(msg)

    def trade_exited(self, position: dict, reason: str, pnl: float):
        strat = position.get("strategy", "?")
        emoji = "\u2705" if pnl > 0 else "\U0001f534"
        strikes = ""
        if strat == "BWB":
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
        msg = (
            f"{emoji} <b>{strat} Closed</b>\n"
            f"{strikes}"
            f"Reason: {reason}\n"
            f"P&L: ${pnl:+.2f}\n"
            f"Exp: {position.get('expiration', '')}"
        )
        self.send(msg)

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
