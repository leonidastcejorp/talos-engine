#!/usr/bin/env python3
"""📋 LogDesk — kumpulkan error dari monitor & report ke Telegram."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from telegram_ui import TelegramMessage
from error_log import ErrorLog

STATE_FILE = os.path.expanduser("~/.hermes/scripts/.error_summary_state.json")
CACHE_FILE = "/root/projects/bounty-output/error_summary_report.txt"
LOGBACK_JAM = 24
os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)


def load_last_check() -> str | None:
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE) as f:
            return json.load(f).get("last_check_ts")
    except Exception:
        return None


def save_last_check() -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"last_check_ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f)
    except OSError:
        pass


def write_cache(content: str | None) -> None:
    try:
        with open(CACHE_FILE, "w") as f:
            if content:
                f.write(content)
            else:
                f.write(f"✅ Error log bersih.\n{datetime.now().strftime('%H:%M')}")
    except OSError:
        pass


def main(all_flag: bool = False, clear_flag: bool = False) -> int:
    if clear_flag:
        ErrorLog.clear_old(14)
        print("✅ Error log dibersihkan (entry > 14 hari dihapus)")
        return 0

    entries = ErrorLog.get_recent(200)
    if not entries:
        write_cache(None)
        return 0  # silent when nothing

    last_check = None if all_flag else load_last_check()
    cutoff = last_check or (datetime.now() - timedelta(hours=LOGBACK_JAM)).strftime("%Y-%m-%d %H:%M:%S")
    baru = entries if all_flag else [e for e in entries if e["ts"] >= cutoff]

    crit = [e for e in baru if e["level"] == "CRITICAL"]
    errs = [e for e in baru if e["level"] == "ERROR"]
    warns = [e for e in baru if e["level"] == "WARNING"]
    total = len(crit) + len(errs) + len(warns)

    if total == 0 and not all_flag:
        write_cache(None)
        return 0
    if total == 0:
        write_cache(None)
        return 0

    level = "CRITICAL" if crit else "ERROR" if errs else "WARNING"
    msg = TelegramMessage("LogDesk", "📋", level=level)
    msg.add_text(f"<b>{total} hal</b> perlu diperhatikan\n")

    by_name: dict[str, list[dict]] = {}
    for e in crit + errs + warns:
        name = e.get("display_name", e.get("script", "?"))
        by_name.setdefault(name, []).append(e)

    for name in sorted(by_name.keys()):
        items = by_name[name]
        worst = max(
            items,
            key=lambda e: ["INFO", "WARNING", "ERROR", "CRITICAL"].index(e["level"])
            if e["level"] in ("INFO", "WARNING", "ERROR", "CRITICAL") else 0,
        )
        worst_ico = {"CRITICAL": "💀", "ERROR": "🔴", "WARNING": "🟡"}.get(worst["level"], "🟡")
        msg.add_text(f"{worst_ico} <b>{name}</b>")
        rows = []
        for e in items:
            ico = {"CRITICAL": "💀", "ERROR": "🔴", "WARNING": "🟡"}.get(e["level"], "·")
            cell = e["judul"]
            if e.get("saran"):
                cell += f"\n💡 {e['saran']}"
            rows.append([ico, cell])
        msg.add_table(["", "Detail"], rows)
        msg.add_blank()

    result = msg.render()
    save_last_check()
    write_cache(result)
    print(result)
    return 0


if __name__ == "__main__":
    all_flag = "--all" in sys.argv
    clear_flag = "--clear" in sys.argv
    try:
        sys.exit(main(all_flag, clear_flag))
    except Exception:
        print("🔴 Gagal bikin laporan error")
        sys.exit(1)
