#!/usr/bin/env python3
"""
🚨 Gateway Watch — Monitor apakah service Hermes masih jalan.
Silent when UP. Alert Telegram HANYA kalo DOWN.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from telegram_ui import TelegramMessage
from error_log import ErrorLog

SERVICE_NAME = "hermes.service"
STATE_FILE = os.path.expanduser("~/.hermes/scripts/.gateway_state.json")
log = ErrorLog("🚨 Gateway Watch")


def is_service_active() -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["systemctl", "is-active", SERVICE_NAME],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0, r.stdout.strip() or "unknown"
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, f"error: {e}"


def get_service_info() -> dict:
    """Get uptime + last log lines kalau service jalan."""
    info = {"uptime": "?", "last_log": ""}
    try:
        # Uptime dari MainPID start time
        out = subprocess.run(
            ["systemctl", "show", SERVICE_NAME, "--property=ActiveEnterTimestamp"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if "=" in out:
            info["uptime"] = out.split("=", 1)[1] or "?"
    except Exception:
        pass
    return info


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"last_status": "unknown", "last_alert_ts": None}
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"last_status": "unknown", "last_alert_ts": None}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except OSError:
        pass


def main() -> int:
    active, status = is_service_active()
    state = load_state()
    now = datetime.now().isoformat()

    if active:
        # Recovery message (kalo sebelumnya down)
        if state.get("last_alert_ts"):
            msg = TelegramMessage("GatewayWatch", "🚨", level="OK")
            msg.add_alert("INFO", "Gateway recovered",
                          f"Service balik UP setelah downtime",
                          "Cek log buat tau root cause")
            msg.add_table(["Service", "Status"], [
                ["Service", "✅ Active"],
                ["Waktu", datetime.now().strftime("%H:%M WIB")],
            ])
            print(msg.render())
            state["last_alert_ts"] = None
        # Else: silent
        state["last_status"] = status
        save_state(state)
        return 0

    # Service DOWN
    last_alert = state.get("last_alert_ts")
    if last_alert:
        try:
            last_dt = datetime.fromisoformat(last_alert)
            if (datetime.now() - last_dt).total_seconds() < 1800:  # 30 min cooldown
                state["last_status"] = status
                save_state(state)
                return 0
        except Exception:
            pass

    # Get last log lines (concise)
    try:
        log_out = subprocess.run(
            ["journalctl", "-u", SERVICE_NAME, "-n", "3", "--no-pager", "-q"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        last_log = " | ".join(log_out.split("\n")[-3:]) if log_out else "—"
    except Exception:
        last_log = "(gagal baca log)"

    msg = TelegramMessage("GatewayWatch", "🚨", level="CRITICAL")
    msg.add_alert("CRITICAL", "Hermes gateway DOWN!",
                  f"Service status: {status}",
                  "systemctl status hermes · journalctl -u hermes -n 30")
    msg.add_table(["Detail", "Value"], [
        ["Service", SERVICE_NAME],
        ["Status", f"❌ {status}"],
        ["Last log", last_log[:200]],
        ["Waktu", datetime.now().strftime("%H:%M WIB")],
    ])
    print(msg.render())

    log.critical("Gateway down", f"Status: {status}", "Cek service")
    state["last_alert_ts"] = now
    state["last_status"] = status
    save_state(state)
    log.persist()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log.exception("Gateway Watch error", "")
        report = log.format_report()
        if report:
            print(report)
        log.persist()
        sys.exit(0)
