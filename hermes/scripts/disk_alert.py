#!/usr/bin/env python3
"""📀 DiskBay — monitor disk, swap, ZRAM."""
from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from telegram_ui import TelegramMessage, bar
from error_log import ErrorLog

log = ErrorLog("📀 DiskBay")


def run(cmd: str, timeout: int = 10) -> tuple[str, bool]:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode == 0
    except Exception:
        return "", False


def parse_disk() -> dict | None:
    out, ok = run("df / | awk 'NR==2 {print $5, $3, $2}'")
    if not ok or not out:
        return None
    parts = out.split()
    try:
        return {"pct": int(parts[0].rstrip("%")), "used": parts[1], "total": parts[2]}
    except (IndexError, ValueError):
        return None


def parse_swap() -> bool:
    out, ok = run("swapon --show 2>/dev/null | grep -E '/swapfile|/dev/zram'")
    return bool(ok and out)


def parse_zram() -> dict | None:
    out, ok = run("systemctl is-active zram-hermes.service 2>/dev/null")
    if not (ok and out.strip() == "active"):
        return None
    zout, zok = run("zramctl --noheadings --raw --output=DISKSIZE,DATA 2>/dev/null | head -1")
    if not (zok and zout):
        return None
    parts = zout.split()
    try:
        size, used = int(parts[0]), int(parts[1])
        return {
            "size_mb": round(size / 1048576),
            "used_mb": round(used / 1048576),
            "pct": int(used * 100 / size) if size else 0,
        }
    except (IndexError, ValueError):
        return None


def main() -> int:
    disk = parse_disk()
    swap_ok = parse_swap()
    zram = parse_zram()
    issues = []

    if disk and disk["pct"] >= 80:
        issues.append(("disk", "CRITICAL" if disk["pct"] >= 90 else "WARNING", disk))
    if not swap_ok:
        issues.append(("swap", "CRITICAL", None))

    if not issues and not log.entries:
        return 0

    if any(i[1] == "CRITICAL" for i in issues):
        level = "CRITICAL"
    elif any(i[1] == "WARNING" for i in issues):
        level = "WARNING"
    else:
        level = "OK"

    msg = TelegramMessage("DiskBay", "📀", level=level)
    rows = []
    if disk:
        rows.append(["Disk", f"`{bar(disk['pct'])}` {disk['pct']}% — {disk['used']}/{disk['total']}"])
    rows.append(["Swap", "✅ Aktif" if swap_ok else "❌ TIDAK AKTIF"])
    if zram:
        rows.append(["ZRAM", f"`{bar(zram['pct'])}` {zram['pct']}% — {zram['used_mb']}M/{zram['size_mb']}M"])
    msg.add_table(["Metric", "Status"], rows)

    for kind, lvl, data in issues:
        if kind == "disk":
            sisa = 40 * (100 - data["pct"]) / 100
            if lvl == "CRITICAL":
                msg.add_alert("CRITICAL", "Disk penuh", f"{data['pct']}%, sisa ~{sisa:.1f}G", "Hapus log: journalctl --vacuum-size=500M")
                log.critical("Disk penuh", f"{data['pct']}%", "Hapus log")
            else:
                msg.add_alert("WARNING", "Disk naik", f"{data['pct']}% ({data['used']}/{data['total']})", "apt clean dalam 1-2 minggu")
        elif kind == "swap":
            msg.add_alert("CRITICAL", "Swap TIDAK AKTIF", "VPS bisa OOM kalo RAM penuh", "Pasang swapfile 2GB")
            log.critical("Swap mati", "No swap", "Pasang swap")

    print(msg.render())
    log.persist()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log.exception("DiskBay error", "")
        report = log.format_report()
        if report:
            print(report)
        log.persist()
        sys.exit(1)
