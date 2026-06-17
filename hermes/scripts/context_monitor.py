#!/usr/bin/env python3
"""📊 SessionDeck — monitor kapasitas context window session Hermes."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from telegram_ui import TelegramMessage, bar
from error_log import ErrorLog

DB = os.path.expanduser("~/.hermes/state.db")
STATE_FILE = os.path.expanduser("~/.hermes/scripts/.context_thresholds.json")
AMBANG_PCT = [50, 75, 90]
log = ErrorLog("📊 SessionDeck")

KAPASITAS = {
    "deepseek-v4": 1_000_000, "deepseek-v3": 1_000_000, "deepseek-r1": 1_000_000,
    "deepseek-chat": 64_000, "claude": 200_000, "gpt-4.1": 1_000_000, "gpt-4o": 128_000,
    "gemini": 1_000_000, "llama-4": 1_000_000, "llama-3.1": 128_000,
    "mistral-large": 128_000, "codestral": 256_000, "qwen-2.5": 128_000,
    "kimi": 128_000,
}


def cari_kapasitas(model: str) -> int:
    if not model:
        return 128_000
    m = model.lower()
    for key in sorted(KAPASITAS.keys(), key=len, reverse=True):
        if key in m:
            return KAPASITAS[key]
    return 128_000


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"notified": {}}
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"notified": {}}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except OSError:
        pass


def get_sessions() -> list:
    if not os.path.exists(DB):
        return []
    try:
        conn = sqlite3.connect(DB, timeout=5)
        cur = conn.execute("""
            SELECT id, COALESCE(title, 'untitled'), COALESCE(model, ''),
                   COALESCE(input_tokens + output_tokens, 0)
            FROM sessions
            WHERE ended_at IS NULL OR started_at > strftime('%s', 'now', '-24 hours')
            ORDER BY (input_tokens + output_tokens) DESC LIMIT 5
        """)
        rows = cur.fetchall()
        conn.close()
        return rows
    except sqlite3.Error:
        return []


def main() -> int:
    state = load_state()
    notified = state.get("notified", {})
    rows = get_sessions()
    if not rows:
        return 0

    new_alerts = []
    for sid, title, model, total in rows:
        total = total or 0
        if total < 1000:
            continue
        kap = cari_kapasitas(model)
        pct = int(total * 100 / kap)
        title_short = (title or "untitled")[:35]
        ses_notified = notified.get(sid, [])

        baru = [a for a in AMBANG_PCT if total >= int(kap * a / 100) and a not in ses_notified]
        if baru:
            max_pct = max(baru)
            level = "CRITICAL" if max_pct >= 90 else "WARNING"
            saran = "**Ketik /compress SEKARANG**" if max_pct >= 90 else "Sebaiknya /compress"
            model_short = (model.split("/")[-1] if model else "?")[:15]
            new_alerts.append({
                "title": title_short, "pct": max_pct,
                "usage": f"{total//1000}k/{kap//1000}k",
                "model": model_short, "level": level, "saran": saran,
            })
            notified[sid] = sorted(set(ses_notified + baru))

    if not new_alerts:
        return 0

    level = "CRITICAL" if any(a["level"] == "CRITICAL" for a in new_alerts) else "WARNING"
    msg = TelegramMessage("SessionDeck", "📊", level=level)
    msg.add_text(f"**{len(new_alerts)} session** butuh /compress\n")
    rows_data = []
    for a in new_alerts:
        rows_data.append([
            a["title"],
            f"`{bar(a['pct'])}` {a['pct']}%",
            a["usage"],
            a["model"],
        ])
    msg.add_table(["Session", "Usage", "Tokens", "Model"], rows_data)
    msg.add_alert(level, "Rekomendasi", "Jalanin /compress di session yang penuh", "Biar gak ke-cut off tengah jalan")
    print(msg.render())

    save_state({"notified": notified})
    log.persist()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log.exception("SessionDeck error", "")
        report = log.format_report()
        if report:
            print(report)
        log.persist()
        sys.exit(1)
