#!/usr/bin/env python3
"""
🔄 Proxy Updater — Download + test free proxies dari berbagai sumber.
Output ke cache. Stdout TABEL ringkas ke Telegram kalau ada perubahan berarti.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

import aiohttp

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from telegram_ui import TelegramMessage, fmt_num
from error_log import ErrorLog

PROXY_DIR = "/root/projects/bounty-output/proxies"
ALIVE_FILE = f"{PROXY_DIR}/alive.txt"
STATE_FILE = os.path.expanduser("~/.hermes/scripts/.proxy_state.json")
BATCH_SIZE = 200
PROXY_TIMEOUT = 5
MIN_ALIVE_THRESHOLD = 5
CONCURRENCY = 100

SOURCES = {
    "shiftytr-http":   "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "hookzof-socks5":  "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "anonymous-http":  "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/http_proxies.txt",
    "roosterkid-https":"https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
    "proxyscrape-api": "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "jetkai-http":     "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
    "prxchk-http":     "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt",
}

IP_PORT_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$")
log = ErrorLog("🔄 Proxy")


def is_valid_proxy(proxy: str) -> bool:
    if not proxy or ":" not in proxy:
        return False
    p = proxy.strip()
    if not IP_PORT_RE.match(p):
        return False
    parts = p.split(":")
    try:
        for octet in parts[0].split("."):
            v = int(octet)
            if v < 0 or v > 255:
                return False
        port = int(parts[1])
        if port < 1 or port > 65535:
            return False
    except ValueError:
        return False
    return True


async def download_proxies(session) -> tuple[dict, list]:
    source_proxies: dict[str, set] = defaultdict(set)
    source_errors: dict[str, str] = {}

    async def fetch_source(name, url):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
                text = await r.text()
                for line in text.strip().split("\n"):
                    p = line.strip()
                    if is_valid_proxy(p):
                        source_proxies[name].add(p)
        except Exception as e:
            source_errors[name] = str(e)[:60]

    await asyncio.gather(*(fetch_source(n, u) for n, u in SOURCES.items()))

    all_unique = set()
    for proxies in source_proxies.values():
        all_unique.update(proxies)

    if source_errors:
        for name, err in source_errors.items():
            log.warning(f"Gagal download {name}", err[:100], "Cek koneksi / source")

    return source_proxies, list(all_unique)


async def test_proxy(session, proxy, sem):
    async with sem:
        for proto in ["http", "https"]:
            try:
                async with session.get(
                    "https://httpbin.org/ip",
                    proxy=f"{proto}://{proxy}",
                    timeout=aiohttp.ClientTimeout(total=PROXY_TIMEOUT),
                ) as r:
                    if r.status == 200:
                        data = await r.json()
                        return (proxy, data.get("origin", "?"), True)
            except Exception:
                pass
    return (proxy, None, False)


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"last_alive_count": 0, "last_run": None}
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"last_alive_count": 0, "last_run": None}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except OSError:
        log.error("Gagal simpan state", "File state gak bisa ditulis", "Cek disk")


async def main_async() -> int:
    os.makedirs(PROXY_DIR, exist_ok=True)
    state = load_state()

    async with aiohttp.ClientSession() as session:
        source_proxies, all_proxies = await download_proxies(session)
        if not all_proxies:
            log.error("Gagal download proxy", "Semua sumber error", "Cek koneksi / sources")
            return 1

        # Save raw
        with open(f"{PROXY_DIR}/raw_all.txt", "w") as f:
            f.write("\n".join(all_proxies))

        # Test batch
        sem = asyncio.Semaphore(CONCURRENCY)
        to_test = all_proxies[:BATCH_SIZE]
        results = await asyncio.gather(*(test_proxy(session, p, sem) for p in to_test))

    alive = [r[0] for r in results if r[2]]
    proxy_to_sources: dict[str, list[str]] = {}
    for src, proxies in source_proxies.items():
        for p in proxies:
            proxy_to_sources.setdefault(p, []).append(src)

    source_alive: dict[str, int] = defaultdict(int)
    for proxy in alive:
        for s in proxy_to_sources.get(proxy, ["unknown"]):
            source_alive[s] += 1

    # Save alive
    if len(alive) >= MIN_ALIVE_THRESHOLD:
        with open(ALIVE_FILE, "w") as f:
            f.write("\n".join(alive))

    # Decide: notify kalau significant change
    prev_count = state.get("last_alive_count", 0)
    diff = len(alive) - prev_count
    pct_change = abs(diff) * 100 / max(prev_count, 1)

    significant = (
        len(alive) < MIN_ALIVE_THRESHOLD or       # under threshold — alert
        pct_change > 30 or                          # change > 30%
        (prev_count > 0 and len(alive) == 0)        # all dead
    )

    save_state({
        "last_alive_count": len(alive),
        "last_run": datetime.now().isoformat(),
    })

    if not significant:
        return 0  # silent

    # Compose Telegram message
    level = "ERROR" if len(alive) < MIN_ALIVE_THRESHOLD else "OK"
    msg = TelegramMessage("Proxy Updater", "🔄", level=level)

    msg.add_table(
        ["Metric", "Value"],
        [
            ["Dites", f"{len(to_test)} dari {len(all_proxies)} total"],
            ["Hidup", f"{len(alive)} ({len(alive)/max(len(to_test),1)*100:.1f}%)"],
            ["Mati", f"{len(to_test) - len(alive)}"],
            ["Perubahan", f"{diff:+d} dari run sebelumnya"],
        ],
    )

    if source_alive:
        rows = sorted(source_alive.items(), key=lambda x: x[1], reverse=True)[:5]
        msg.add_table(
            ["Source", "Hidup"],
            [[name, str(n)] for name, n in rows],
            caption="Top 5 sumber",
        )

    if len(alive) < MIN_ALIVE_THRESHOLD:
        msg.add_alert("ERROR", "Pool proxy menipis",
                      f"Cuma {len(alive)} proxy hidup (min {MIN_ALIVE_THRESHOLD})",
                      "Cek koneksi atau tambah source")
    elif prev_count == 0 and len(alive) > 0:
        msg.add_alert("INFO", "Pool proxy pertama kali",
                      f"{len(alive)} proxy hidup tersimpan")
    elif pct_change > 30:
        msg.add_alert("WARNING", "Pool proxy berubah signifikan",
                      f"{diff:+d} ({pct_change:.0f}%)",
                      "Cek kualitas source")

    print(msg.render())
    return 0


def main() -> int:
    try:
        return asyncio.run(main_async())
    except Exception:
        log.exception("Proxy Updater error", "Cek dependencies & koneksi")
        report = log.format_report()
        if report:
            print(report)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log.exception("Proxy fatal error", "")
        report = log.format_report()
        if report:
            print(report)
        sys.exit(1)
