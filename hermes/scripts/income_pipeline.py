#!/usr/bin/env python3
"""
💰 Cuan Feed — cari gigs & peluang cuan dari Reddit, Freelancer, DeFi.
Output: silent kalo gak ada yang menarik. Alert kalo ada high-value gig.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from telegram_ui import TelegramMessage, fmt_num
from error_log import ErrorLog

CACHE_DIR = "/root/projects/bounty-output"
CACHE_FILE = f"{CACHE_DIR}/pipeline_report.txt"
os.makedirs(CACHE_DIR, exist_ok=True)

log = ErrorLog("💰 Cuan Feed")
RESULTS: list[tuple[str, str, str]] = []


def tulis(cat: str, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M")
    RESULTS.append((ts, cat, msg))


def fetch(url: str, timeout: int = 20) -> str | None:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 BREACH-bot/1.0"
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        log.warning(f"HTTP {e.code} di {url[:40]}", "Mungkin situs down", "Cek manual")
        return None
    except Exception as e:
        log.warning(f"Gagal fetch {url[:40]}", f"{type(e).__name__}", "Cek koneksi")
        return None


def cek_reddit(sub: str, query: str) -> int:
    url = f"https://old.reddit.com/r/{sub}/search.rss?q={urllib.parse.quote(query)}&sort=new&restrict_sr=on&limit=15"
    html = fetch(url)
    if not html:
        return 0
    entries = re.findall(r"<entry>(.*?)</entry>", html, re.DOTALL)
    if not entries:
        return 0
    matches = 0
    keywords = ["$", "usd", "pay", "paypal", "btc", "eth", "crypto", "task", "job", "hire"]
    for e in entries[:8]:
        title_m = re.search(r"<title>(.*?)</title>", e, re.DOTALL)
        if not title_m:
            continue
        title = title_m.group(1).strip()
        title = title.replace("&amp;", "&").replace("&#x27;", "'").replace("&quot;", '"')
        if any(kw in title.lower() for kw in keywords):
            link_m = re.search(r'<link[^>]*href="([^"]+)"', e) or re.search(r"<link>(.*?)</link>", e)
            link = link_m.group(1).strip() if link_m else ""
            tulis(sub, f"{title[:80]}|{link}")
            matches += 1
    return matches


def cek_freelancer() -> int:
    data = fetch("https://www.freelancer.com/api/projects/0.1/projects/active/?limit=5", timeout=15)
    if not data:
        return 0
    try:
        j = json.loads(data)
    except json.JSONDecodeError:
        return 0
    if j.get("status") != "success":
        return 0
    projects = j.get("result", {}).get("projects", [])
    count = 0
    for p in projects[:5]:
        title = (p.get("title", "Untitled") or "Untitled")[:60]
        budget = p.get("budget", {}) or {}
        amount = budget.get("minimum", "?")
        currency = (budget.get("currency", {}) or {}).get("code", "$")
        tulis("Freelancer", f"{title}|{currency}{amount}")
        count += 1
    return count


def write_cache() -> None:
    try:
        with open(CACHE_FILE, "w") as f:
            f.write(f"💰 Income Pipeline — {datetime.now().isoformat()}\n")
            f.write("=" * 52 + "\n")
            for ts, cat, msg in RESULTS:
                f.write(f"[{ts}] [{cat}] {msg}\n")
    except OSError:
        log.error("Gagal simpan cache", "Disk issue", "Cek disk")


def main() -> int:
    try:
        cek_reddit("slavelabour", "paypal crypto usd bitcoin")
        cek_reddit("beermoney", "paypal free crypto")
        cek_reddit("forhire", "paypal usd")
        cek_freelancer()
    except Exception:
        log.exception("Pipeline error", "Cek koneksi")

    write_cache()

    # High-value filter: $50+ gigs
    high_val = []
    for ts, cat, msg in RESULTS:
        if re.search(r'\$[5-9]\d{2,}|\$\d{4,}', msg):
            title_part = msg.split("|")[0] if "|" in msg else msg
            link_part = msg.split("|")[1] if "|" in msg else ""
            high_val.append((cat, title_part[:60], link_part, ts))

    if not high_val and not log.ada_masalah():
        return 0

    if high_val:
        msg = TelegramMessage("CuanFeed", "💰", level="OK")
        msg.add_text("<b>HIGH-VALUE GIG TERDETEKSI!</b>\n")
        rows = [[cat, title, link[:50] if link else "—", ts] for cat, title, link, ts in high_val[:6]]
        msg.add_table(["Kategori", "Detail", "Link", "Jam"], rows)
        print(msg.render())
    elif log.ada_masalah():
        report = log.format_report()
        if report:
            print(report)

    log.persist()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log.exception("Cuan Feed error", "")
        report = log.format_report()
        if report:
            print(report)
        log.persist()
        sys.exit(1)
