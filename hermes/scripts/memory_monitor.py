#!/usr/bin/env python3
"""📈 MemStat — Memory & OOM Monitor untuk Telegram."""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from telegram_ui import TelegramMessage, bar
from error_log import ErrorLog

STATE_FILE = os.path.expanduser("~/.hermes/scripts/.memory_state.json")
SWAP_WARN_MB = 500
MEM_WARN_PCT = 90

log = ErrorLog("📈 MemStat")


def run(cmd: list[str], timeout: int = 10) -> tuple[str, bool]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode == 0
    except Exception:
        return "", False


def parse_mem() -> dict | None:
    raw, ok = run(["free", "-m"])
    if not ok or not raw:
        return None
    try:
        mem = [c for c in raw.split("\n") if c.startswith("Mem:")][0].split()
        swap = [c for c in raw.split("\n") if c.startswith("Swap:")][0].split()
        return {
            "used": int(mem[2]), "total": int(mem[1]),
            "avail": int(mem[6]) if len(mem) > 6 else int(mem[1]) - int(mem[2]),
            "pct": int(int(mem[2]) * 100 / int(mem[1])),
            "swap_used": int(swap[2]), "swap_total": int(swap[1]),
            "swap_pct": int(int(swap[2]) * 100 / int(swap[1])) if int(swap[1]) else 0,
        }
    except (IndexError, ValueError, ZeroDivisionError):
        return None


def check_oom() -> int:
    raw, ok = run(["dmesg", "--level=emerg,alert,crit,err"])
    if not ok:
        return 0
    return sum(1 for line in (raw or "").split("\n") if "oom" in line.lower() or "out of memory" in line.lower())


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except OSError:
        pass


def main() -> int:
    mem = parse_mem()
    oom_count = check_oom()
    prev = load_state()
    alerts: list[dict] = []

    if mem:
        swap_used, mem_pct, mem_avail = mem["swap_used"], mem["pct"], mem["avail"]
        swap_total, swap_pct = mem["swap_total"], mem["swap_pct"]

        if swap_used > SWAP_WARN_MB and not prev.get("swap_warned", False):
            alerts.append({
                "level": "WARNING", "title": "Swap penuh",
                "detail": f"{swap_used}MB/{swap_total}MB ({swap_pct}%), RAM {mem_pct}%",
                "saran": "Tutup app boros atau upgrade RAM",
            })
        prev["swap_warned"] = swap_used > SWAP_WARN_MB

        if mem_pct > MEM_WARN_PCT and not prev.get("ram_critical_warned", False):
            alerts.append({
                "level": "ERROR", "title": "RAM kritis",
                "detail": f"{mem_pct}%, sisa {mem_avail}MB",
                "saran": "Tutup program / matikan service",
            })
        prev["ram_critical_warned"] = mem_pct > MEM_WARN_PCT

        if oom_count > 0 and oom_count > prev.get("oom_count", 0):
            alerts.append({
                "level": "CRITICAL", "title": "OOM Killer aktif",
                "detail": f"Sistem bunuh program {oom_count}x",
                "saran": "dmesg | grep -i oom",
            })
        prev["oom_count"] = oom_count

        if prev.get("swap_warned_prev", False) and swap_used <= SWAP_WARN_MB:
            alerts.append({
                "level": "INFO", "title": "Swap normal",
                "detail": f"Turun ke {swap_used}MB",
            })
        prev["swap_warned_prev"] = swap_used > SWAP_WARN_MB

        if prev.get("ram_critical_prev", False) and mem_pct <= MEM_WARN_PCT:
            alerts.append({
                "level": "INFO", "title": "RAM normal",
                "detail": f"{mem_pct}%, sisa {mem_avail}MB",
            })
        prev["ram_critical_prev"] = mem_pct > MEM_WARN_PCT

    level = "OK"
    if any(a["level"] == "CRITICAL" for a in alerts):
        level = "CRITICAL"
    elif any(a["level"] == "ERROR" for a in alerts):
        level = "ERROR"
    elif any(a["level"] == "WARNING" for a in alerts):
        level = "WARNING"

    msg = TelegramMessage("MemStat", "📈", level=level)

    if mem:
        msg.add_table(["Memory", "Status"], [
            ["RAM", f"`{bar(mem['pct'])}` {mem['pct']}% — {mem['used']}M/{mem['total']}M, sisa {mem['avail']}M"],
            ["Swap", f"`{bar(mem['swap_pct'])}` {mem['swap_pct']}% — {mem['swap_used']}M/{mem['swap_total']}M"],
        ])

    for a in alerts:
        msg.add_alert(a["level"], a["title"], a.get("detail", ""), a.get("saran", ""))

    print(msg.render())
    save_state(prev)
    log.persist()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log.exception("MemStat error", "Coba ulang")
        report = log.format_report()
        if report:
            print(report)
        log.persist()
        sys.exit(1)
