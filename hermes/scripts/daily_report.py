#!/usr/bin/env python3
"""
Talos Engine - Daily Report Generator

Generates a comprehensive daily briefing covering:
- Token usage from Hermes Agent state.db
- System health snapshot
- Error summary from error logs
- Income pipeline statistics

Outputs Telegram-formatted markdown for daily cron delivery.

Usage:
    python scripts/daily_report.py
    python scripts/daily_report.py --webhook URL
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.error_log import _default_log, ErrorLevel
try:
    import psutil
except ImportError:
    psutil = None

# ─── Configuration ───────────────────────────────────────────────────────────
HERMES_STATE_DB = os.path.expanduser("~/.hermes/state.db")
ERROR_LOG_FILE = "data/errors.jsonl"


def get_token_usage(db_path: str) -> dict:
    """Extract token usage from Hermes Agent state database."""
    usage = {
        "total_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_requests": 0,
        "total_cost_usd": 0.0,
        "sessions_today": 0,
    }

    if not os.path.exists(db_path):
        return usage

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()

        # Get token totals from conversations table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        # Try common table structures
        today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()

        if "conversations" in tables:
            try:
                cursor.execute(
                    "SELECT SUM(prompt_tokens), SUM(completion_tokens), COUNT(*) "
                    "FROM conversations WHERE created_at >= ?",
                    (today_start,),
                )
                row = cursor.fetchone()
                if row and row[0]:
                    usage["prompt_tokens"] = row[0] or 0
                    usage["completion_tokens"] = row[1] or 0
                    usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
                    usage["total_requests"] = row[2] or 0
            except sqlite3.OperationalError:
                pass

        if "messages" in tables:
            try:
                cursor.execute(
                    "SELECT COUNT(*) FROM messages WHERE created_at >= ?",
                    (today_start,),
                )
                row = cursor.fetchone()
                if row:
                    usage["sessions_today"] = row[0] or 0
            except sqlite3.OperationalError:
                pass

        conn.close()
    except Exception as e:
        print(f"DB read error (non-fatal): {e}")

    return usage


def get_system_health() -> dict:
    """Quick system health snapshot."""
    if not psutil:
        return {"available": False}

    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    cpu = psutil.cpu_percent(interval=1)
    uptime = int(time.time() - psutil.boot_time())

    return {
        "ram_pct": ram.percent,
        "disk_pct": disk.percent,
        "cpu_pct": cpu,
        "uptime_hours": round(uptime / 3600, 1),
    }


def get_error_stats() -> dict:
    """Get error statistics from the error log."""
    _default_log.load_from_file()
    yesterday = (datetime.now() - timedelta(days=1)).timestamp()
    summary = _default_log.summarize(since=yesterday)

    total_errors = sum(
        sum(levels.values()) for levels in summary.values()
    )
    return {
        "total_errors_24h": total_errors,
        "sources": summary,
    }


def format_daily_report(usage: dict, health: dict, errors: dict) -> str:
    """Format the full daily briefing as Telegram Markdown."""
    today = datetime.now().strftime("%A, %B %d %Y")
    lines = [f"📋 *Talos Engine Daily Briefing*", f"📅 {today}", ""]

    # ─── Token Usage ───────────────────────────────────────────────
    lines.append("🤖 *Hermes Agent Usage*")
    if usage["total_tokens"] > 0:
        lines.append(f"• Tokens today: {usage['total_tokens']:,}")
        lines.append(f"  - Prompt: {usage['prompt_tokens']:,}")
        lines.append(f"  - Completion: {usage['completion_tokens']:,}")
        lines.append(f"• Requests today: {usage['total_requests']}")
        if usage["total_cost_usd"] > 0:
            lines.append(f"• Est. cost: ${usage['total_cost_usd']:.3f}")
    else:
        lines.append("• No token data available (Hermes Agent may be offline)")
    lines.append("")

    # ─── System Health ─────────────────────────────────────────────
    lines.append("🖥 *System Health*")
    if health.get("available", True):
        lines.append(f"• RAM: {health['ram_pct']:.1f}%")
        lines.append(f"• Disk: {health['disk_pct']:.1f}%")
        lines.append(f"• CPU: {health['cpu_pct']:.1f}%")
        lines.append(f"• Uptime: {health['uptime_hours']}h")
    else:
        lines.append("• psutil not available")
    lines.append("")

    # ─── Error Summary ─────────────────────────────────────────────
    lines.append("⚠️ *Errors (24h)*")
    if errors["total_errors_24h"] > 0:
        lines.append(f"• Total: {errors['total_errors_24h']}")
        for source, counts in errors.get("sources", {}).items():
            count_str = ", ".join(f"{lvl}: {n}" for lvl, n in counts.items())
            lines.append(f"  - {source}: {count_str}")
    else:
        lines.append("• No errors — clean day! ✅")
    lines.append("")

    # ─── Footer ────────────────────────────────────────────────────
    lines.append("---")
    lines.append("🤖 _Talos Engine — Automation Framework_")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Talos Engine - Daily Report Generator"
    )
    parser.add_argument(
        "--webhook", type=str, default="",
        help="Telegram webhook URL to send the report",
    )
    parser.add_argument(
        "--state-db", type=str, default=HERMES_STATE_DB,
        help="Path to Hermes Agent state.db",
    )
    args = parser.parse_args()

    print("📋 Generating Talos Engine daily report...")

    usage = get_token_usage(args.state_db)
    health = get_system_health()
    errors = get_error_stats()

    report = format_daily_report(usage, health, errors)
    print(report)
    print()

    if args.webhook:
        # Simple Telegram send (same pattern as monitor.py)
        import urllib.request
        import urllib.parse
        try:
            data = urllib.parse.urlencode({
                "chat_id": os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID"),
                "text": report,
                "parse_mode": "Markdown",
            }).encode()
            url = f"https://api.telegram.org/bot{os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN')}/sendMessage"
            urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=10)
            print("✅ Report sent to Telegram")
        except Exception as e:
            print(f"❌ Telegram send failed: {e}")


if __name__ == "__main__":
    main()
