#!/usr/bin/env python3
"""
Talos Engine - Pipeline Runner

Entry point for running automation pipelines:
account creation, scraping, and monitoring tasks.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flowcore.core.browser import StealthBrowser
from flowcore.core.fingerprint import FingerprintGenerator
from flowcore.modules.registrar import RegistrationEngine
from flowcore.modules.scraper import AntiDetectionScraper
from flowcore.modules.watcher import PipelineWatcher, HealthCollector
from flowcore.utils.network import ProxyManager
from flowcore.utils.names import IdentityGenerator

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO"):
    """Configure logging for pipeline execution."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )


async def run_registration(
    platforms: list[str],
    count: int = 10,
    headless: bool = True,
):
    """Run bulk account registration."""
    print(f"\n{'='*60}")
    print(f"  TALOS ENGINE - Bulk Registration")
    print(f"  Platforms: {', '.join(platforms)}")
    print(f"  Accounts per platform: {count}")
    print(f"{'='*60}\n")

    async with StealthBrowser(headless=headless) as browser:
        engine = RegistrationEngine(browser=browser)
        results = await engine.bulk_register(platforms, count)

        for platform, platform_results in results.items():
            success = sum(1 for r in platform_results if r.success)
            failed = sum(1 for r in platform_results if not r.success)
            print(f"  {platform}: {success} success, {failed} failed")

    print(f"\n  Pipeline complete.\n")


async def run_scraper(url: str, proxy_url: str = None):
    """Run web scraping task."""
    print(f"\n{'='*60}")
    print(f"  TALOS ENGINE - Web Scraper")
    print(f"  Target: {url}")
    print(f"{'='*60}\n")

    scraper = AntiDetectionScraper(proxy_url=proxy_url)
    try:
        content = await scraper.fetch(url)
        if content:
            print(f"  Fetched {len(content)} bytes from {url}")
        else:
            print(f"  Failed to fetch {url}")
    finally:
        await scraper.close()


async def run_watcher(interval: int = 300):
    """Run pipeline monitoring watcher."""
    print(f"\n{'='*60}")
    print(f"  TALOS ENGINE - Pipeline Watcher")
    print(f"  Check interval: {interval}s")
    print(f"{'='*60}\n")

    watcher = PipelineWatcher(check_interval=interval)

    async def alert_handler(message: str):
        print(f"  [ALERT] {message}")

    watcher.alert_callback = alert_handler
    await watcher.start()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n  Shutting down watcher...")
    finally:
        await watcher.stop()


def main():
    parser = argparse.ArgumentParser(
        description="Talos Engine - Pipeline Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s register -p discord fiverr -n 20
  %(prog)s scrape -u https://example.com
  %(prog)s watch --interval 600
        """,
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    subparsers = parser.add_subparsers(dest="command", help="Pipeline command")

    # Register subcommand
    reg_parser = subparsers.add_parser("register", help="Bulk account registration")
    reg_parser.add_argument(
        "-p", "--platforms", nargs="+",
        default=["discord"], choices=["discord", "fiverr", "reddit"],
        help="Target platforms",
    )
    reg_parser.add_argument(
        "-n", "--count", type=int, default=10,
        help="Accounts per platform",
    )
    reg_parser.add_argument(
        "--no-headless", action="store_true",
        help="Show browser windows",
    )

    # Scrape subcommand
    scrape_parser = subparsers.add_parser("scrape", help="Web scraping")
    scrape_parser.add_argument(
        "-u", "--url", required=True, help="Target URL",
    )
    scrape_parser.add_argument(
        "--proxy", help="Proxy URL (e.g., socks5://host:port)",
    )

    # Watch subcommand
    watch_parser = subparsers.add_parser("watch", help="Pipeline monitoring")
    watch_parser.add_argument(
        "--interval", type=int, default=300,
        help="Check interval in seconds",
    )

    args = parser.parse_args()
    setup_logging(args.log_level)

    if args.command == "register":
        asyncio.run(run_registration(
            args.platforms, args.count, headless=not args.no_headless,
        ))
    elif args.command == "scrape":
        asyncio.run(run_scraper(args.url, args.proxy))
    elif args.command == "watch":
        asyncio.run(run_watcher(args.interval))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
