#!/usr/bin/env python3
"""🚪 PortGuard — deteksi percobaan hack SSH dari fail2ban log."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from telegram_ui import TelegramMessage
from error_log import ErrorLog

STATE_FILE = os.path.expanduser("~/.hermes/scripts/.ssh_attack_state.json")
AMBANG = 5
F2B_LOG = "/var/log/fail2ban.log"
log = ErrorLog("🚪 PortGuard")


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"known_ips": [], "last_notified_level": 999, "initialized": False}
    try:
        with open(STATE_FILE) as f:
            d = json.load(f)
            d.setdefault("known_ips", [])
            d.setdefault("last_notified_level", 999)
            d.setdefault("initialized", False)
            return d
    except Exception:
        return {"known_ips": [], "last_notified_level": 999, "initialized": False}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except OSError:
        pass


def get_recent_bans() -> list[tuple[str, str]]:
    if not os.path.exists(F2B_LOG):
        return []
    try:
        r = subprocess.run(["grep", "NOTICE.*Ban", F2B_LOG], capture_output=True, text=True, timeout=10)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    raw = r.stdout.strip()
    if not raw:
        return []
    cutoff = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    bans = []
    for line in raw.split("\n"):
        if not line.strip():
            continue
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        ts = parts[0] + " " + parts[1].rstrip(",")
        ip = parts[-1]
        if ts >= cutoff:
            bans.append((ts, ip))
    return bans


def main() -> int:
    state = load_state()
    bans = get_recent_bans()
    if not bans and not state.get("initialized"):
        return 0  # silent when nothing

    current_ips = [ip for _, ip in bans]
    current_set = set(current_ips)
    total_bans = len(bans)
    new_ips = current_set - set(state["known_ips"])
    new_count = len(new_ips)

    # First run: initialize
    if not state.get("initialized"):
        save_state({
            "known_ips": list(current_set),
            "last_notified_level": new_count,
            "initialized": True,
            "last_checked": datetime.now().isoformat(),
        })
        msg = TelegramMessage("PortGuard", "🚪", level="OK")
        msg.add_table(["Metric", "Value"], [
            ["Status", "✅ Pemantauan dimulai"],
            ["Percobaan 24j", str(total_bans)],
            ["IP unik", str(len(current_set))],
        ])
        print(msg.render())
        return 0

    # Save state
    save_state({
        "known_ips": list(current_set),
        "last_notified_level": state["last_notified_level"],
        "initialized": True,
        "last_checked": datetime.now().isoformat(),
    })

    # Threshold check
    if new_count > AMBANG and new_count > state["last_notified_level"]:
        level = "ERROR" if new_count > 20 else "WARNING"
        save_state({
            "known_ips": list(current_set),
            "last_notified_level": new_count,
            "initialized": True,
            "last_checked": datetime.now().isoformat(),
        })
        top_ips = sorted(new_ips)[:5]
        msg = TelegramMessage("PortGuard", "🚪", level=level)
        msg.add_alert(
            level,
            "Serangan SSH terdeteksi" if level == "ERROR" else "Percobaan SSH",
            f"{new_count} IP baru, {total_bans}x percobaan, {len(current_set)} IP unik",
            "Ganti port SSH / Cloudflare WAF" if level == "ERROR" else "fail2ban udah blokir"
        )
        msg.add_table(["Detail", "Value"], [
            ["IP baru (sample)", ", ".join(top_ips) + ("..." if new_count > 5 else "")],
        ])
        print(msg.render())
        if level == "ERROR":
            log.critical("SSH attack", f"{new_count} IP", "Ganti port")
        else:
            log.warning("SSH attempt", f"{new_count} IP", "OK")

    log.persist()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log.exception("PortGuard error", "")
        report = log.format_report()
        if report:
            print(report)
        log.persist()
        sys.exit(1)
