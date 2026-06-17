#!/usr/bin/env python3
"""
📊 Daily Briefing — ringkasan harian VPS (token, sistem, peluang).
Format: RINGKAS, TABEL, bahasa Indonesia.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from telegram_ui import TelegramMessage, bar, fmt_num
from error_log import ErrorLog

HOME = os.path.expanduser("~")
HERMES_DIR = os.path.join(HOME, ".hermes")
STATE_DB = os.path.join(HERMES_DIR, "state.db")
log = ErrorLog("📊 Daily Briefing")


def run(cmd: str, timeout: int = 15) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def get_tokens() -> dict | None:
    if not os.path.exists(STATE_DB):
        return None
    try:
        conn = sqlite3.connect(STATE_DB)
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).timestamp()
        yesterday = conn.execute(
            """SELECT COUNT(*), COALESCE(SUM(input_tokens), 0),
                      COALESCE(SUM(output_tokens), 0), COALESCE(SUM(estimated_cost_usd), 0),
                      COALESCE(SUM(message_count), 0)
               FROM sessions WHERE started_at > ?""",
            (today_start - 86400,),
        ).fetchone()
        today = conn.execute(
            """SELECT COUNT(*), COALESCE(SUM(input_tokens), 0),
                      COALESCE(SUM(output_tokens), 0), COALESCE(SUM(estimated_cost_usd), 0)
               FROM sessions WHERE started_at > ?""",
            (today_start,),
        ).fetchone()
        conn.close()
        if yesterday[0] == 0:
            return None
        return {
            "ses_24h": yesterday[0], "msg_24h": yesterday[4],
            "in_24h": yesterday[1], "out_24h": yesterday[2], "cost_24h": yesterday[3],
            "today_ses": today[0], "today_total": today[1] + today[2], "today_cost": today[3],
        }
    except Exception as e:
        log.warning("Gagal baca token", f"{e}", "Cek state.db")
        return None


def get_sysinfo() -> dict:
    return {
        "uptime": run("uptime -p").replace("up ", "") or "?",
        "ram_pct": int(run("free | awk '/Mem:/ {printf \"%d\", $3*100/$2}'") or 0),
        "ram": run("free -h | awk '/Mem:/ {print $3\"/\"$2}'") or "?",
        "disk_pct": int(run("df / | awk 'NR==2 {gsub(\"%\",\"\"); print $5}'") or 0),
        "disk": run("df -h / | awk 'NR==2 {print $5\", \"$4\" free\"}'") or "?",
    }


def get_errors() -> str | None:
    cache = "/root/projects/bounty-output/error_summary_report.txt"
    if os.path.exists(cache):
        try:
            with open(cache) as f:
                content = f.read().strip()
            if content and "Bersih" not in content:
                return content
        except OSError:
            pass
    return None


def get_income() -> tuple[int, int] | None:
    cache = "/root/projects/bounty-output/pipeline_report.txt"
    if not os.path.exists(cache):
        return None
    try:
        with open(cache) as f:
            content = f.read()
        return (content.count("[slavelabour]"), content.count("[Freelancer]"))
    except OSError:
        return None


def main() -> int:
    sys_info = get_sysinfo()
    tokens = get_tokens()
    errors = get_errors()
    income = get_income()

    msg = TelegramMessage("DailyBriefing", "📊", level="OK")

    msg.add_table(["Sistem", "Status"], [
        ["Uptime", sys_info["uptime"]],
        ["RAM", f"`{bar(sys_info['ram_pct'])}` {sys_info['ram_pct']}% — {sys_info['ram']}"],
        ["Disk", f"`{bar(sys_info['disk_pct'])}` {sys_info['disk_pct']}% — {sys_info['disk']}"],
    ])

    if tokens:
        rows = [
            ["Sessions 24j", str(tokens["ses_24h"])],
            ["Messages 24j", str(tokens["msg_24h"])],
            ["Input 24j", f"{fmt_num(tokens['in_24h'])} tok"],
            ["Output 24j", f"{fmt_num(tokens['out_24h'])} tok"],
            ["Total 24j", f"{fmt_num(tokens['in_24h'] + tokens['out_24h'])} tok"],
            ["Cost 24j", f"${tokens['cost_24h']:.4f}"],
        ]
        if tokens["today_ses"] > 0:
            rows.append(["Today", f"{tokens['today_ses']} ses · {fmt_num(tokens['today_total'])} tok"])
        msg.add_table(["Token", "Value"], rows, caption="24 jam terakhir")

    if income:
        sl, fl = income
        if sl + fl > 0:
            msg.add_table(["Income", "Jumlah"], [
                ["Reddit Gigs", str(sl)],
                ["Freelancer", str(fl)],
            ], caption="scan")

    if errors:
        msg.add_separator()
        msg.add_text(f"⚠ <b>error log.</b>\n{errors[:400]}")
    else:
        msg.add_separator()
        msg.add_text("✅ <b>error log</b> bersih, all good")

    msg.add_table(["Airdrop", "Chain"], [
        ["Hypernova (Prop Firm)", "Arbitrum"],
        ["Interstate (Trading)", "Solana"],
        ["DeepBook (Liquidity)", "Sui"],
        ["ArcNova AI ($ROAM)", "BNB"],
        ["Roam (DePIN $ROAM)", "Solana"],
    ], caption="airdrop aktif")

    msg.add_table(["Chain", "URL"], [
        ["Sepolia ETH", "faucet.sepolia.dev"],
        ["zkSync", "portal.zksync.io/faucet"],
        ["Scroll", "scroll.io/faucet"],
        ["Base", "base.org/faucet"],
        ["Polygon", "faucet.polygon.technology"],
    ], caption="faucet")

    print(msg.render())
    log.persist()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log.exception("Daily Briefing error", "")
        report = log.format_report()
        if report:
            print(report)
        log.persist()
        sys.exit(1)
