#!/usr/bin/env python3
"""📡 VitalSign — Server Watchdog (RAM, Disk, CPU) untuk Telegram."""
from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from telegram_ui import TelegramMessage, bar
from error_log import ErrorLog

log = ErrorLog("📡 VitalSign")


def run(cmd: str, timeout: int = 15) -> tuple[str, bool]:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode == 0
    except subprocess.TimeoutExpired:
        return "", False
    except FileNotFoundError:
        log.error("Perintah gak ada", f"`{cmd.split()[0]}` gak ada", "Cek PATH")
        return "", False
    except OSError as e:
        log.error("Gagal jalanin", f"{e}", "Cek permission")
        return "", False


def parse_free() -> dict | None:
    out, ok = run("free -m")
    if not ok or not out:
        return None
    try:
        mem = [c for c in out.split("\n") if c.startswith("Mem:")][0].split()
        total, used = int(mem[1]), int(mem[2])
        avail = int(mem[6]) if len(mem) > 6 else total - used
        return {
            "used_gb": used / 1024,
            "total_gb": total / 1024,
            "pct": int(used * 100 / total) if total else 0,
        }
    except (IndexError, ValueError, ZeroDivisionError):
        return None


def parse_df() -> dict | None:
    out, ok = run("df -h / | tail -1")
    if not ok or not out:
        return None
    parts = out.split()
    try:
        return {
            "used": parts[2],
            "total": parts[1],
            "pct": int(parts[4].rstrip("%")),
        }
    except (IndexError, ValueError):
        return None


def parse_load() -> dict | None:
    out, _ = run("uptime | grep -oP 'load average:.*' | cut -d: -f2")
    if not out:
        return None
    vals = [float(x) for x in out.replace(",", "").split() if x.replace(".", "").isdigit()]
    if not vals:
        return None
    cores_out, _ = run("nproc")
    cores = int(cores_out) if cores_out and cores_out.isdigit() else 2
    load = vals[0]
    return {"load": load, "cores": cores, "util": (load / cores) * 100}


def ram_level(pct: int) -> str:
    if pct >= 92: return "CRITICAL"
    if pct >= 82: return "ERROR"
    if pct >= 70: return "WARNING"
    return "OK"


def disk_level(pct: int) -> str:
    if pct >= 93: return "CRITICAL"
    if pct >= 88: return "ERROR"
    if pct >= 78: return "WARNING"
    return "OK"


def cpu_level(util: float) -> str:
    if util >= 150: return "CRITICAL"
    if util >= 100: return "ERROR"
    if util >= 70:  return "WARNING"
    return "OK"


def worst_level(*levels: str) -> str:
    order = ["OK", "WARNING", "ERROR", "CRITICAL"]
    return max(levels, key=lambda l: order.index(l)) if levels else "OK"


def main() -> int:
    ram = parse_free()
    disk = parse_df()
    cpu = parse_load()

    levels = []
    if ram: levels.append(ram_level(ram["pct"]))
    if disk: levels.append(disk_level(disk["pct"]))
    if cpu: levels.append(cpu_level(cpu["util"]))
    level = worst_level(*levels) if levels else "OK"

    msg = TelegramMessage("VitalSign", "📡", level=level)

    # Ringkas: gabung bar + value di 1 cell
    rows = []
    if ram:
        rows.append(["RAM", f"`{bar(ram['pct'])}` {ram['pct']}% — {ram['used_gb']:.1f}G/{ram['total_gb']:.1f}G"])
    if disk:
        rows.append(["Disk", f"`{bar(disk['pct'])}` {disk['pct']}% — {disk['used']}/{disk['total']}"])
    if cpu:
        rows.append(["CPU", f"`{bar(min(cpu['util'], 100))}` {cpu['util']:.0f}% — load {cpu['load']:.2f}/{cpu['cores']}c"])
    if rows:
        msg.add_table(["Metric", "Status"], rows)

    # Alert RINGKAS (cuma kalau ada masalah)
    if ram and ram_level(ram["pct"]) != "OK":
        lvl = ram_level(ram["pct"])
        avail_gb = ram["total_gb"] - ram["used_gb"]
        if lvl == "CRITICAL":
            msg.add_alert("CRITICAL", "RAM kritis", f"{ram['pct']}%, sisa {avail_gb:.1f}G", "Matikan program berat")
            log.critical("RAM habis", f"{ram['pct']}%", "Matikan program")
        elif lvl == "ERROR":
            msg.add_alert("ERROR", "RAM bahaya", f"{ram['pct']}%, sisa {avail_gb:.1f}G", "Bersihin cache: drop_caches")
        else:
            msg.add_alert("WARNING", "RAM tinggi", f"{ram['pct']}%, sisa {avail_gb:.1f}G", "Pantau, restart Hermes kalo naik")

    if disk and disk_level(disk["pct"]) != "OK":
        lvl = disk_level(disk["pct"])
        sisa = 40 * (100 - disk["pct"]) / 100
        if lvl == "CRITICAL":
            msg.add_alert("CRITICAL", "Disk penuh", f"{disk['pct']}%, sisa ~{sisa:.1f}G", "Hapus log: journalctl --vacuum-size=500M")
            log.critical("Disk penuh", f"{disk['pct']}%", "Hapus log")
        elif lvl == "ERROR":
            msg.add_alert("ERROR", "Disk bahaya", f"{disk['pct']}% ({disk['used']}/{disk['total']})", "apt clean & hapus log")
        else:
            msg.add_alert("WARNING", "Disk naik", f"{disk['pct']}% ({disk['used']}/{disk['total']})", "Pantau, cleanup dalam 1-2 minggu")

    if cpu and cpu_level(cpu["util"]) != "OK":
        lvl = cpu_level(cpu["util"])
        if lvl == "CRITICAL":
            msg.add_alert("CRITICAL", "CPU overload", f"load {cpu['load']:.2f}/{cpu['cores']}c", "Cek htop, matikan yg boros")
            log.critical("CPU overload", f"{cpu['load']:.2f}", "Cek htop")
        elif lvl == "ERROR":
            msg.add_alert("ERROR", "CPU penuh", f"load {cpu['load']:.2f}/{cpu['cores']}c", "Cek ps aux --sort=-%cpu")
        else:
            msg.add_alert("WARNING", "CPU tinggi", f"load {cpu['load']:.2f}/{cpu['cores']}c ({cpu['util']:.0f}%)", "Jangan spawn task baru dulu")

    print(msg.render())
    log.persist()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log.exception("VitalSign error", "Coba ulang")
        report = log.format_report()
        if report:
            print(report)
        log.persist()
        sys.exit(1)
