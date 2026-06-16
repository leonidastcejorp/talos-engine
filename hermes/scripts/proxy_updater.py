#!/usr/bin/env python3
"""
Talos Engine - Proxy Updater

Downloads free proxy lists from public sources, tests them
for connectivity, and saves working proxies to the pool file.

Usage:
    python scripts/proxy_updater.py
    python scripts/proxy_updater.py --output data/proxies.txt
    python scripts/proxy_updater.py --test-only
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.error_log import log_error, ErrorLevel

try:
    import aiohttp
except ImportError:
    print("ERROR: aiohttp required. Install: pip install aiohttp")
    sys.exit(1)

# Public free proxy sources
PROXY_SOURCES: list[str] = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS.txt",
]

POOL_FILE = Path("data/proxies.txt")
STATS_FILE = Path("data/proxy_stats.json")


async def fetch_proxies(url: str) -> list[str]:
    """Download proxy list from a URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    return []
                text = await resp.text()
                return [
                    line.strip()
                    for line in text.splitlines()
                    if line.strip() and not line.startswith("#")
                ]
    except Exception as e:
        log_error(
            message=f"Failed to fetch proxies from {url}: {e}",
            level=ErrorLevel.WARNING,
            source="proxy_updater",
        )
        return []


async def test_proxy(proxy_url: str, test_url: str, timeout: int = 10) -> tuple[str, bool, float]:
    """Test a single proxy. Returns (url, alive, latency_ms)."""
    start = time.monotonic()
    try:
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.get(test_url, proxy=proxy_url) as resp:
                latency = (time.monotonic() - start) * 1000
                return (proxy_url, resp.status == 200, latency)
    except Exception:
        return (proxy_url, False, 0)


async def test_all(
    proxies: list[str],
    test_url: str = "https://httpbin.org/ip",
    concurrency: int = 50,
) -> dict:
    """Test all proxies with controlled concurrency."""
    semaphore = asyncio.Semaphore(concurrency)
    results = {"alive": [], "dead": [], "total": len(proxies)}

    async def worker(url: str):
        async with semaphore:
            url, alive, latency = await test_proxy(url, test_url)
            if alive:
                results["alive"].append({"url": url, "latency_ms": round(latency, 1)})
            else:
                results["dead"].append(url)

    tasks = [worker(url) for url in proxies]
    await asyncio.gather(*tasks, return_exceptions=True)
    return results


async def run_update(output_file: str, test_only: bool = False):
    """Main update logic."""
    print(f"\n{'='*60}")
    print(f"  TALOS ENGINE - Proxy Updater")
    print(f"{'='*60}\n")

    if not test_only:
        # Fetch fresh proxies
        print("📥 Fetching proxy lists...")
        all_proxies: set[str] = set()
        for source in PROXY_SOURCES:
            proxies = await fetch_proxies(source)
            all_proxies.update(proxies)
            print(f"   {source.split('/')[-2]}: {len(proxies)}")
            await asyncio.sleep(0.5)

        print(f"\n   Unique proxies collected: {len(all_proxies)}")
        proxies_to_test = list(all_proxies)
    else:
        # Load existing proxies for testing
        if Path(output_file).exists():
            proxies_to_test = [
                line.strip()
                for line in Path(output_file).read_text().splitlines()
                if line.strip() and not line.startswith("#")
            ]
            print(f"📂 Loaded {len(proxies_to_test)} proxies from {output_file}")
        else:
            print(f"❌ No proxy file at {output_file}")
            return

    if not proxies_to_test:
        print("No proxies to test.")
        return

    # Test
    print(f"\n🧪 Testing {len(proxies_to_test)} proxies...")
    results = await test_all(proxies_to_test)
    alive_count = len(results["alive"])
    dead_count = len(results["dead"])

    print(f"\n   Results:")
    print(f"   ✅ Alive: {alive_count}")
    print(f"   ❌ Dead:  {dead_count}")
    print(f"   📊 Success rate: {alive_count / max(results['total'], 1) * 100:.1f}%")

    # Save
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort alive by latency
    results["alive"].sort(key=lambda p: p["latency_ms"])
    content = "\n".join(p["url"] for p in results["alive"])
    output_path.write_text(content)
    print(f"\n📁 Saved {alive_count} working proxies to {output_file}")

    # Save stats
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    import json as _json
    stats = {
        "updated": time.time(),
        "total_tested": results["total"],
        "alive": alive_count,
        "dead": dead_count,
        "top_latency_ms": results["alive"][0]["latency_ms"] if results["alive"] else 0,
        "avg_latency_ms": (
            round(sum(p["latency_ms"] for p in results["alive"]) / alive_count, 1)
            if alive_count > 0
            else 0
        ),
    }
    STATS_FILE.write_text(_json.dumps(stats, indent=2))

    if alive_count < 10:
        log_error(
            message=f"Proxy pool low: only {alive_count} working proxies",
            level=ErrorLevel.WARNING,
            source="proxy_updater",
        )


def main():
    parser = argparse.ArgumentParser(
        description="Talos Engine - Proxy Updater"
    )
    parser.add_argument(
        "--output", type=str, default=str(POOL_FILE),
        help="Output proxy pool file",
    )
    parser.add_argument(
        "--test-only", action="store_true",
        help="Only test existing proxies (skip fetching)",
    )
    args = parser.parse_args()

    asyncio.run(run_update(args.output, args.test_only))


if __name__ == "__main__":
    main()
