#!/usr/bin/env python3
"""
Talos Engine - Server Watchdog

Monitors RAM, Disk, CPU, and swap usage.
Silent when healthy, sends alerts on threshold breaches.
Outputs Telegram-formatted markdown tables.

Usage:
    python scripts/monitor.py                    # One-shot health check
    python scripts/monitor.py --loop 300          # Continuous monitoring
    python scripts/monitor.py --webhook URL       # With Telegram webhook
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add scripts/lib to path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.error_log import ErrorLog, ErrorLevel, log_error, get_error_summary

try:
    import psutil
except ImportError:
    print("ERROR: psutil required. Install: pip install psutil")
    sys.exit(1)

# ─── Thresholds ──────────────────────────────────────────────────────────────
RAM_WARN_PCT = 80       # Warning threshold (%)
RAM_CRIT_PCT = 90       # Critical threshold (%)
DISK_WARN_PCT = 80
DISK_CRIT_PCT = 90
CPU_WARN_PCT = 80
CPU_CRIT_PCT = 95
SWAP_WARN_PCT = 50
SWAP_CRIT_PCT = 80


def get_health_metrics() -> dict:
    """Collect current system health metrics."""
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    swap = psutil.swap_memory()
    cpu = psutil.cpu_percent(interval=1)
    load = psutil.getloadavg()
    uptime = int(time.time() - psutil.boot_time())

    return {
        "timestamp": time.time(),
        "ram": {
            "total_gb": round(ram.total / (1024**3), 2),
            "used_gb": round(ram.used / (1024**3), 2),
            "percent": ram.percent,
            "status": _level(ram.percent, RAM_WARN_PCT, RAM_CRIT_PCT),
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "percent": disk.percent,
            "status": _level(disk.percent, DISK_WARN_PCT, DISK_CRIT_PCT),
        },
        "cpu": {
            "percent": cpu,
            "cores": psutil.cpu_count(),
            "status": _level(cpu, CPU_WARN_PCT, CPU_CRIT_PCT),
        },
        "swap": {
            "total_gb": round(swap.total / (1024**3), 2),
            "used_gb": round(swap.used / (1024**3), 2),
            "percent": swap.percent,
            "status": _level(swap.percent, SWAP_WARN_PCT, SWAP_CRIT_PCT),
        },
        "load": {
            "1min": load[0],
            "5min": load[1],
            "15min": load[2],
        },
        "uptime_hours": round(uptime / 3600, 1),
    }


def _level(value: float, warn: float, crit: float) -> str:
    if value >= crit:
        return "🔴 CRIT"
    if value >= warn:
        return "🟡 WARN"
    return "🟢 OK"


def format_telegram(m: dict) -> str:
    """Format health metrics as a Telegram MarkdownV2 table."""
    lines = ["🖥 *Server Health Report*", ""]
    lines.append(f"📅 `{time.strftime('%Y-%m-%d %H:%M:%S')}`")
    lines.append(f"⏱ Uptime: {m['uptime_hours']}h")
    lines.append("")

    # RAM
    ram = m["ram"]
    lines.append(f"🧠 *RAM*: {ram['percent']:.1f}% ({ram['used_gb']} / {ram['total_gb']} GB) {ram['status']}")

    # Disk
    disk = m["disk"]
    lines.append(f"💾 *Disk*: {disk['percent']:.1f}% ({disk['used_gb']} / {disk['total_gb']} GB) {disk['status']}")

    # CPU
    cpu = m["cpu"]
    lines.append(f"⚙️ *CPU*: {cpu['percent']:.1f}% ({cpu['cores']} cores) {cpu['status']}")

    # Swap
    swap = m["swap"]
    if swap["total_gb"] > 0:
        lines.append(f"🔄 *Swap*: {swap['percent']:.1f}% ({swap['used_gb']} / {swap['total_gb']} GB) {swap['status']}")

    # Load
    load = m["load"]
    lines.append(f"📊 *Load*: {load['1min']:.2f} / {load['5min']:.2f} / {load['15min']:.2f}")

    return "\n".join(lines)


def send_telegram(message: str, webhook_url: str):
    """Send a message via Telegram bot API."""
    import urllib.request
    import urllib.parse

    try:
        data = urllib.parse.urlencode({
            "chat_id": os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID"),
            "text": message,
            "parse_mode": "Markdown",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN')}/sendMessage",
            data=data,
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Telegram send failed: {e}")


def check_and_alert(metrics: dict, webhook_url: str = None, silent_ok: bool = True):
    """Check thresholds and send alerts if needed."""
    has_issue = False
    alerts = []

    for name, data in metrics.items():
        if name in ("timestamp", "uptime_hours", "load"):
            continue
        if data.get("status", "").startswith("🔴"):
            has_issue = True
            alerts.append(f"CRITICAL: {name.upper()} at {data['percent']:.1f}%")

    if has_issue:
        log_error(
            message="; ".join(alerts),
            level=ErrorLevel.CRITICAL,
            source="monitor",
            details=metrics,
        )
        if webhook_url:
            msg = format_telegram(metrics)
            msg += "\n\n⚠️ *Thresholds Breached!*"
            send_telegram(msg, webhook_url)

    # Print to stdout (for cron output)
    if not silent_ok or has_issue:
        print(format_telegram(metrics))


def main():
    parser = argparse.ArgumentParser(
        description="Talos Engine - Server Watchdog"
    )
    parser.add_argument(
        "--loop", type=int, default=0,
        help="Run continuously with N second interval",
    )
    parser.add_argument(
        "--webhook", type=str, default="",
        help="Telegram webhook URL for alerts",
    )
    parser.add_argument(
        "--silent", action="store_true", default=True,
        help="Only output when issues detected",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Always output health report",
    )
    args = parser.parse_args()

    silent_ok = args.silent and not args.verbose

    if args.loop:
        print(f"🖥 Talos Engine Watchdog started (interval={args.loop}s)")
        try:
            while True:
                metrics = get_health_metrics()
                check_and_alert(metrics, args.webhook, silent_ok)
                time.sleep(args.loop)
        except KeyboardInterrupt:
            print("\nWatchdog stopped.")
    else:
        metrics = get_health_metrics()
        check_and_alert(metrics, args.webhook, silent_ok)


if __name__ == "__main__":
    main()
