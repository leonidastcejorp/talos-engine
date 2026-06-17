#!/usr/bin/env python3
"""Example task: open Galxe dashboard for a wallet."""
from typing import Optional


async def galxe_checkin(runner, wallet_label: str, headless: bool = True) -> dict:
    """Navigate to Galxe and return page metadata."""
    url = "https://galxe.com"

    async def handler(page):
        return {
            "connected": "wallet" in (await page.content()).lower(),
            "wallet": wallet_label,
        }

    return await runner.run_browser_task(wallet_label, url, handler=handler, headless=headless)
