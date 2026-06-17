#!/usr/bin/env python3
"""🔐 SSH Login Watch — Alert Telegram setiap ada yang berhasil login."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from telegram_ui import TelegramMessage
from error_log import ErrorLog

STATE_FILE = os.path.expanduser("~/.hermes/scripts/.ssh_login_state.json")
GEO_CACHE = os.path.expanduser("~/.hermes/scripts/.geo_cache.json")
PAM_USER = os.environ.get("PAM_USER", "?")
PAM_RHOST = os.environ.get("PAM_RHOST", "?")
PAM_TYPE = os.environ.get("PAM_TYPE", "open_session")
log = ErrorLog("🔐 SSH Login")


def lookup_country(ip: str) -> str:
    if not ip or ip in ("?", "unknown") or ip.startswith("127."):
        return "LO"
    cache = {}
    if os.path.exists(GEO_CACHE):
        try:
            with open(GEO_CACHE) as f:
                cache = json.load(f)
        except Exception:
            cache = {}
    if ip in cache:
        return cache[ip]
    try:
        out = subprocess.run(
            ["curl", "-s", "--max-time", "5", f"https://ipinfo.io/{ip}/country"],
            capture_output=True, text=True, timeout=8,
        ).stdout.strip()
        country = out if out and len(out) <= 3 else "??"
    except Exception:
        country = "??"
    cache[ip] = country
    if len(cache) > 500:
        cache = dict(list(cache.items())[-300:])
    try:
        os.makedirs(os.path.dirname(GEO_CACHE), exist_ok=True)
        with open(GEO_CACHE, "w") as f:
            json.dump(cache, f)
    except OSError:
        pass
    return country


def is_new_login() -> bool:
    now = datetime.now()
    if not os.path.exists(STATE_FILE):
        return True
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        last = state.get("last", {})
        if last.get("user") == PAM_USER and last.get("ip") == PAM_RHOST:
            last_ts = datetime.fromisoformat(last.get("ts", "2000-01-01"))
            if (now - last_ts).total_seconds() < 300:  # 5 min
                return False
    except Exception:
        return True
    return True


def save_state() -> None:
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump({
                "last": {"user": PAM_USER, "ip": PAM_RHOST, "ts": datetime.now().isoformat()}
            }, f)
    except OSError:
        pass


def main() -> int:
    if PAM_TYPE != "open_session":
        return 0
    if not is_new_login():
        return 0  # dedup

    country = lookup_country(PAM_RHOST)
    client = os.environ.get("SSH_CLIENT", "").split()
    port = client[2] if len(client) > 2 else "?"
    tty = os.environ.get("SSH_TTY", "?").replace("/dev/", "")

    msg = TelegramMessage("SSHLogin", "🔐", level="INFO")
    msg.add_table(["Detail", "Value"], [
        ["User", PAM_USER],
        ["IP", f"`{PAM_RHOST}` ({country})"],
        ["Port", port],
        ["TTY", tty],
    ])

    print(msg.render())
    save_state()
    log.persist()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log.exception("SSH Login Watch error", "")
        sys.exit(0)
