#!/usr/bin/env python3
"""
Talos Engine - Proxy Pool Refresher

Downloads fresh proxy lists from free sources, tests them,
and updates the proxy pool file with only working proxies.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flowcore.utils.network import ProxyManager

logger = logging.getLogger(__name__)

# Free proxy list sources (these are publicly available)
FREE_PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt",
]


async def fetch_proxy_list(url: str) -> list[str]:
    """Fetch a proxy list from a URL. Returns list of proxy strings."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    logger.warning("Failed to fetch %s: HTTP %d", url, resp.status)
                    return []
                text = await resp.text()
                proxies = [
                    line.strip()
                    for line in text.splitlines()
                    if line.strip() and not line.startswith("#")
                ]
                logger.info("Fetched %d proxies from %s", len(proxies), url)
                return proxies
    except Exception as e:
        logger.error("Error fetching %s: %s", url, e)
        return []


async def refresh_proxies(
    pool_file: str = "data/proxies.txt",
    test_url: str = "https://httpbin.org/ip",
):
    """Download fresh proxies, test them, and save the working ones."""
    print(f"\n{'='*60}")
    print(f"  TALOS ENGINE - Proxy Refresh")
    print(f"  Pool file: {pool_file}")
    print(f"{'='*60}\n")

    manager = ProxyManager(
        pool_file=pool_file,
        test_url=test_url,
    )

    # Fetch proxies from all sources
    print("  Fetching proxy lists...")
    all_proxies: set[str] = set()
    for url in FREE_PROXY_SOURCES:
        proxies = await fetch_proxy_list(url)
        all_proxies.update(proxies)
        await asyncio.sleep(1)  # Be polite to sources

    print(f"  Collected {len(all_proxies)} unique proxies")

    # Add to manager
    for proxy_url in all_proxies:
        manager.add_proxy(proxy_url)

    print(f"  Testing {len(manager._proxies)} proxies...")
    result = await manager.health_check_all()

    # Save only alive proxies
    manager.save_to_file()

    print(f"\n  Results:")
    print(f"    Total tested: {result['alive'] + result['dead']}")
    print(f"    Alive:  {result['alive']}")
    print(f"    Dead:   {result['dead']}")
    print(f"\n  Proxy pool saved to {pool_file}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Talos Engine - Proxy Pool Refresher"
    )
    parser.add_argument(
        "-f", "--pool-file", default="data/proxies.txt",
        help="Path to proxy pool file (default: data/proxies.txt)",
    )
    parser.add_argument(
        "--test-url", default="https://httpbin.org/ip",
        help="URL to test proxies against",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    asyncio.run(refresh_proxies(args.pool_file, args.test_url))


if __name__ == "__main__":
    main()
