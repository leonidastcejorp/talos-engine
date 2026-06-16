#!/usr/bin/env python3
"""
Talos Engine - Reboot Monitor

Detects system reboots by comparing boot IDs and sends
notification when a reboot is detected. Designed to run
on startup via cron @reboot or systemd timer.

Usage:
    Put in crontab: @reboot python3 /path/to/scripts/reboot_monitor.py
    Or run manually: python scripts/reboot_monitor.py
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.error_log import log_error, ErrorLevel

STATE_FILE = Path("data/boot_state.json")


def get_boot_id() -> str:
    """Read boot UUID from /proc."""
    boot_file = Path("/proc/sys/kernel/random/boot_id")
    if boot_file.exists():
        return boot_file.read_text().strip()
    return "unknown"


def get_uptime() -> float:
    """Get system uptime in seconds."""
    try:
        with open("/proc/uptime") as f:
            return float(f.readline().split()[0])
    except Exception:
        return 0


def check_reboot(send_alert: bool = True):
    """Check if system has rebooted since last run. Sends alert if configured."""
    current_boot_id = get_boot_id()
    current_time = time.time()

    # Load previous state
    previous = {}
    if STATE_FILE.exists():
        try:
            previous = json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            pass

    previous_boot_id = previous.get("boot_id", "")
    is_reboot = previous_boot_id and previous_boot_id != current_boot_id

    # Always save current state
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "boot_id": current_boot_id,
        "last_seen": current_time,
        "uptime_seconds": get_uptime(),
        "is_reboot": is_reboot,
        "previous_boot_id": previous_boot_id if is_reboot else None,
    }
    STATE_FILE.write_text(json.dumps(state, indent=2))

    if is_reboot:
        print("🔄 SYSTEM REBOOT DETECTED!")
        print(f"   Previous boot ID: {previous_boot_id[:16]}...")
        print(f"   Current boot ID:  {current_boot_id[:16]}...")
        print(f"   Uptime: {get_uptime():.0f}s")

        log_error(
            message="System reboot detected",
            level=ErrorLevel.ALERT,
            source="reboot_monitor",
            details={
                "previous_boot_id": previous_boot_id,
                "current_boot_id": current_boot_id,
                "uptime_seconds": get_uptime(),
            },
        )

        # Try Telegram notification
        if send_alert:
            _send_telegram_alert(previous_boot_id, current_boot_id)

        return True

    print(f"✅ No reboot detected (boot ID: {current_boot_id[:16]}...)")
    return False


def _send_telegram_alert(old_id: str, new_id: str):
    """Send reboot notification via Telegram."""
    import urllib.request
    import urllib.parse

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")

    msg = (
        "🔄 *System Reboot Detected*\n\n"
        f"Previous boot: `{old_id[:16]}...`\n"
        f"Current boot: `{new_id[:16]}...`\n"
        f"Uptime: {get_uptime():.0f}s\n"
        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    try:
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "Markdown",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=data,
        )
        urllib.request.urlopen(req, timeout=10)
        print("   Telegram alert sent")
    except Exception as e:
        print(f"   Telegram alert failed: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Talos Engine - Reboot Monitor"
    )
    parser.add_argument(
        "--no-alert", action="store_true",
        help="Skip Telegram notification",
    )
    parser.add_argument(
        "--init", action="store_true",
        help="Initialize state file without alerting",
    )
    args = parser.parse_args()

    if args.init:
        state = {
            "boot_id": get_boot_id(),
            "last_seen": time.time(),
            "uptime_seconds": get_uptime(),
            "is_reboot": False,
        }
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2))
        print(f"✅ Boot state initialized: {state['boot_id'][:16]}...")
        return

    rebooted = check_reboot(send_alert=not args.no_alert)
    sys.exit(0 if not rebooted else 1)


if __name__ == "__main__":
    main()
