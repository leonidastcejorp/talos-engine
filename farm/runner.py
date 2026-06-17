#!/usr/bin/env python3
"""
🚀 Farm Runner — execute airdrop tasks per account with proxy + browser profile.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from playwright.async_api import async_playwright

from .proxy import ProxyRotator
from .profile import ProfileManager
from .wallet import WalletManager


@dataclass
class FarmContext:
    label: str
    wallet_label: str
    address: str
    proxy_url: str
    profile_dir: Path
    fingerprint: dict


class FarmRunner:
    def __init__(
        self,
        wallet_manager: WalletManager,
        proxy_rotator: ProxyRotator,
        profile_manager: ProfileManager,
    ):
        self.wm = wallet_manager
        self.pr = proxy_rotator
        self.pm = profile_manager
        self._running = False

    async def run_task(
        self,
        wallet_label: str,
        task: Callable[[FarmContext], Optional[dict]],
    ) -> dict:
        wallet = next((w for w in self.wm.list_wallets("evm") if w.label == wallet_label), None)
        if wallet is None:
            raise KeyError(f"wallet not found: {wallet_label}")

        proxy = self.pr.get(strategy="random")
        profile_dir, fp = self.pm.get(wallet_label)

        ctx = FarmContext(
            label=f"{wallet_label}-{asyncio.get_event_loop().time()}",
            wallet_label=wallet_label,
            address=wallet.address,
            proxy_url=proxy.url,
            profile_dir=profile_dir,
            fingerprint=fp.__dict__,
        )

        result = task(ctx)
        if asyncio.iscoroutine(result):
            result = await result
        return {"context": ctx.__dict__, "result": result or {}}

    async def run_browser_task(
        self,
        wallet_label: str,
        url: str,
        handler: Optional[Callable] = None,
        headless: bool = True,
    ) -> dict:
        """Open browser with profile + proxy, navigate to URL, optionally run handler."""
        wallet = next((w for w in self.wm.list_wallets("evm") if w.label == wallet_label), None)
        if wallet is None:
            raise KeyError(f"wallet not found: {wallet_label}")

        proxy = self.pr.get(strategy="random")
        profile_dir, fp = self.pm.get(wallet_label)

        async with async_playwright() as p:
            args = ["--disable-blink-features=AutomationControlled"]
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=headless,
                args=args,
                viewport={"width": fp.viewport["width"], "height": fp.viewport["height"]},
                locale=fp.locale,
                timezone_id=fp.timezone,
                color_scheme=fp.color_scheme,
                proxy={"server": proxy.url} if proxy.protocol in ("http", "https", "socks5") else None,
            )
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            outcome = {"url": url, "title": await page.title()}
            if handler:
                extra = handler(page)
                if asyncio.iscoroutine(extra):
                    extra = await extra
                outcome.update(extra or {})
            await browser.close()
        return outcome
