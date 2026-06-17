#!/usr/bin/env python3
"""
🛡️ Blocklist Updater — auto-update ipset blacklist dari feed blocklist.de.

Feed blocklist.de fokus ke IP yang aktif melakukan SSH bruteforce,
port scan, dan attack lain — perfect untuk VPS. Update tiap 6 jam via cron.

Sumber:
  - blocklist.de all.txt:  https://lists.blocklist.de/lists/all.txt
  - firehol_level1 (backup): https://iplists.firehol.org/files/firehol_level1.netset
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from telegram_ui import TelegramMessage, fmt_num
from error_log import ErrorLog

IPSET_NAME = "blacklist"
STATE_FILE = os.path.expanduser("~/.hermes/scripts/.blocklist_state.json")
SOURCES = [
    ("blocklist.de", "https://lists.blocklist.de/lists/all.txt"),
    ("firehol_l1",   "https://iplists.firehol.org/files/firehol_level1.netset"),
]
MAX_ENTRIES = 131_072
log = ErrorLog("🛡️ Blocklist")


def fetch(url: str, timeout: int = 30) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BREACH-blocklist/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.warning(f"Gagal fetch {url[:50]}", f"{type(e).__name__}: {str(e)[:80]}", "Cek koneksi")
        return None


def parse_ips(text: str) -> set[str]:
    """Parse text → set of valid IPv4 CIDR entries (IPv6 di-skip)."""
    valid: set[str] = set()
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Skip comments after #
        line = line.split("#")[0].strip()
        if not line:
            continue
        try:
            if "/" in line:
                net = ipaddress.ip_network(line, strict=False)
                # Skip IPv6 — ipset blacklist IPv4 only
                if net.version != 4:
                    continue
            else:
                addr = ipaddress.ip_address(line)
                if addr.version != 4:
                    continue
                line = f"{line}/32"
            valid.add(line)
        except ValueError:
            continue
    return valid


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"last_count": 0, "last_run": None, "known": []}
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"last_count": 0, "last_run": None, "known": []}


def save_state(count: int, entries: set[str]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        # Don't dump 131k entries to JSON; just store hash & count
        with open(STATE_FILE, "w") as f:
            json.dump({
                "last_count": count,
                "last_run": datetime.now().isoformat(),
                "hash": hash(frozenset(entries)) & 0xFFFFFFFFFFFFFFFF,
            }, f)
    except OSError:
        pass


def ipset_restore(entries: set[str]) -> tuple[int, str]:
    """Replace ipset blacklist with new entries via stdin pipe. Returns (count, err)."""
    if len(entries) > MAX_ENTRIES:
        # Truncate (keep smaller blocks first, more specific = better)
        sorted_entries = sorted(entries, key=lambda x: ipaddress.ip_network(x).num_addresses)
        entries = set(sorted_entries[:MAX_ENTRIES])

    # Build stdin content
    stdin_data = ""
    for entry in entries:
        stdin_data += f"add {IPSET_NAME} {entry}\n"

    swap_name = f"{IPSET_NAME}_new"
    try:
        # Force destroy swap (might be leftover from previous failed run)
        subprocess.run(
            ["ipset", "destroy", swap_name],
            capture_output=True, timeout=10,
        )
        # Create new set
        result = subprocess.run(
            ["ipset", "create", swap_name, "hash:net", "maxelem", str(MAX_ENTRIES)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return 0, f"ipset create gagal: {result.stderr[:200]}"

        # Build stdin for swap_name
        swap_stdin = "".join(f"add {swap_name} {e}\n" for e in entries)
        result = subprocess.run(
            ["ipset", "restore"],
            input=swap_stdin,
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            subprocess.run(["ipset", "destroy", swap_name], capture_output=True, timeout=10)
            return 0, f"ipset restore gagal: {result.stderr[:200]}"

        # Swap (atomic)
        result = subprocess.run(
            ["ipset", "swap", swap_name, IPSET_NAME],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return 0, f"ipset swap gagal: {result.stderr[:200]}"
        subprocess.run(["ipset", "destroy", swap_name], capture_output=True, timeout=10)
    except subprocess.CalledProcessError as e:
        return 0, f"ipset error: {e.stderr.decode()[:200] if e.stderr else str(e)}"
    except Exception as e:
        return 0, f"Error: {e}"

    return len(entries), ""


def main() -> int:
    state = load_state()
    all_ips: set[str] = set()

    for name, url in SOURCES:
        text = fetch(url)
        if text:
            ips = parse_ips(text)
            all_ips.update(ips)
            print(f"  📥 {name}: {len(ips)} entries")

    if not all_ips:
        log.error("Gagal fetch semua sumber", "Blocklist kosong", "Cek koneksi / sources")
        report = log.format_report()
        if report:
            print(report)
        log.persist()
        return 1

    print(f"  📦 Total unique: {len(all_ips)}")

    # Update ipset
    count, err = ipset_restore(all_ips)
    if err:
        log.error("Gagal update ipset", err[:200], "Cek manual: ipset list")
        report = log.format_report()
        if report:
            print(report)
        log.persist()
        return 1

    # Compare to previous
    prev_count = state.get("last_count", 0)
    diff = count - prev_count

    save_state(count, all_ips)

    # Notify kalau perubahan signifikan
    significant = abs(diff) > 500 or count == 0

    if not significant and not log.ada_masalah():
        return 0  # silent

    level = "OK"
    msg = TelegramMessage("BlocklistUpdater", "🛡️", level=level)
    msg.add_table(["Metric", "Value"], [
        ["Total IP", fmt_num(count)],
        ["Sebelumnya", fmt_num(prev_count)],
        ["Perubahan", f"{diff:+,}"],
    ])
    if abs(diff) > 1000:
        msg.add_alert(
            "WARNING" if diff > 0 else "INFO",
            "Perubahan signifikan",
            f"{diff:+,} IP dibanding run sebelumnya",
        )

    print(msg.render())
    log.persist()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log.exception("Blocklist updater error", "Cek dependencies")
        report = log.format_report()
        if report:
            print(report)
        log.persist()
        sys.exit(1)
