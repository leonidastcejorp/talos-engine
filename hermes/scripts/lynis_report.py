#!/usr/bin/env python3
"""🔍 Lynis Reporter — audit hardening + kirim ke Telegram (mingguan)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from telegram_ui import TelegramMessage, bar
from error_log import ErrorLog

LYNIS_LOG = "/var/log/lynis.log"
STATE_FILE = os.path.expanduser("~/.hermes/scripts/.lynis_state.json")
log = ErrorLog("🔍 Lynis")


def run_lynis() -> int:
    try:
        r = subprocess.run(
            ["lynis", "audit", "system", "--quick", "--no-colors", "--quiet"],
            capture_output=True, text=True, timeout=300,
        )
        return r.returncode
    except FileNotFoundError:
        log.error("Lynis gak ada", "apt install lynis", "Install manual")
        return 1
    except subprocess.TimeoutExpired:
        log.error("Lynis timeout", "> 5 menit", "Jalankan manual")
        return 1
    except Exception as e:
        log.error("Lynis gagal", f"{e}", "Cek manual")
        return 1


def parse_score() -> int:
    if not os.path.exists(LYNIS_LOG):
        return 0
    try:
        with open(LYNIS_LOG) as f:
            for line in f:
                m = re.search(r"Hardening index\s*:\s*\[(\d+)\]", line)
                if m:
                    return int(m.group(1))
    except Exception:
        pass
    return 0


def parse_issues() -> tuple[list[str], list[str]]:
    warnings, suggestions = [], []
    if not os.path.exists(LYNIS_LOG):
        return warnings, suggestions
    try:
        with open(LYNIS_LOG) as f:
            for line in f:
                m = re.match(r"^warning\[([A-Z0-9_-]+)\]\s*=\s*(.+)$", line.strip())
                if m:
                    warnings.append(f"{m.group(2)[:100]}")
                m = re.match(r"^suggestion\[([A-Z0-9_-]+)\]\s*=\s*(.+)$", line.strip())
                if m:
                    suggestions.append(f"{m.group(2)[:100]}")
    except Exception:
        pass
    return warnings, suggestions


def load_prev_score() -> int:
    if not os.path.exists(STATE_FILE):
        return 0
    try:
        with open(STATE_FILE) as f:
            return json.load(f).get("last_score", 0)
    except Exception:
        return 0


def save_score(score: int) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"last_score": score, "last_run": datetime.now().isoformat()}, f)
    except OSError:
        pass


def main() -> int:
    rc = run_lynis()
    if rc != 0 and not os.path.exists(LYNIS_LOG):
        report = log.format_report()
        if report:
            print(report)
        log.persist()
        return 1

    score = parse_score()
    warnings, suggestions = parse_issues()
    prev = load_prev_score()
    diff = score - prev
    level = "OK" if score >= 75 else "WARNING" if score >= 60 else "ERROR"

    msg = TelegramMessage("LynisAudit", "🔍", level=level)
    msg.add_table(["Metric", "Value"], [
        ["Hardening", f"`{bar(score)}` **{score}/100**"],
        ["Sebelumnya", f"{prev}/100"],
        ["Perubahan", f"{diff:+d}"],
        ["Warnings", str(len(warnings))],
        ["Suggestions", str(len(suggestions))],
    ])

    if diff > 0:
        msg.add_alert("INFO", "Skor naik", f"{prev} → {score}", "Mantap")
    elif diff < 0:
        msg.add_alert("WARNING", "Skor turun", f"{prev} → {score}", "Cek issue di bawah")

    if warnings:
        rows = [[w] for w in warnings[:6]]
        if len(warnings) > 6:
            rows.append([f"... +{len(warnings) - 6} lainnya"])
        msg.add_table(["Warning"], rows, caption=f"⚠️ {len(warnings)} warning")
    if suggestions:
        rows = [[s] for s in suggestions[:6]]
        if len(suggestions) > 6:
            rows.append([f"... +{len(suggestions) - 6} lainnya"])
        msg.add_table(["Suggestion"], rows, caption=f"💡 {len(suggestions)} suggestion")
    if not warnings and not suggestions and score >= 80:
        msg.add_text("✅ **Bersih** — gak ada warning/suggestion.")

    print(msg.render())
    save_score(score)
    log.persist()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log.exception("Lynis error", "")
        report = log.format_report()
        if report:
            print(report)
        log.persist()
        sys.exit(1)
