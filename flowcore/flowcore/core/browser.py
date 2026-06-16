"""
Talos Engine - Browser Automation Core

Playwright wrapper with stealth patches, fingerprint injection,
proxy support, and anti-detection measures.
"""

import asyncio
import random
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)

from ..utils.network import ProxyManager

logger = logging.getLogger(__name__)


class StealthBrowser:
    """
    Anti-detection browser wrapper with configurable fingerprint and proxy.

    Usage:
        async with StealthBrowser() as browser:
            page = await browser.new_page()
            await page.goto("https://example.com")
    """

    def __init__(
        self,
        headless: bool = True,
        proxy: Optional[Dict[str, str]] = None,
        viewport: Optional[Dict[str, int]] = None,
        locale: str = "en-US",
        timezone: str = "America/Chicago",
        color_scheme: str = "dark",
        user_data_dir: Optional[str] = None,
    ):
        self.headless = headless
        self.proxy = proxy
        self.viewport = viewport or {"width": 1280, "height": 720}
        self.locale = locale
        self.timezone = timezone
        self.color_scheme = color_scheme
        self.user_data_dir = user_data_dir
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def __aenter__(self) -> "StealthBrowser":
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()

    async def start(self):
        """Launch browser with anti-detection measures."""
        self._playwright = await async_playwright().start()

        launch_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-webrtc",
        ]

        if self.proxy and self.proxy.get("server"):
            launch_args.append(f'--proxy-server={self.proxy["server"]}')

        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
        )

        await self._create_context()
        logger.info("StealthBrowser started (headless=%s)", self.headless)

    async def _create_context(self) -> BrowserContext:
        """Create a browser context with anti-fingerprinting measures."""
        if self._context:
            await self._context.close()

        context_options: Dict[str, Any] = {
            "viewport": self.viewport,
            "locale": self.locale,
            "timezone_id": self.timezone,
            "color_scheme": self.color_scheme,
            "user_agent": self._random_user_agent(),
            "bypass_csp": True,
            "java_script_enabled": True,
            "has_touch": False,
            "is_mobile": False,
        }

        if self.user_data_dir:
            context_options["storage_state"] = str(
                Path(self.user_data_dir) / "state.json"
            )

        if self.proxy:
            context_options["proxy"] = self.proxy

        self._context = await self._browser.new_context(**context_options)
        await self._apply_stealth_patches(self._context)
        return self._context

    async def _apply_stealth_patches(self, context: BrowserContext):
        """Apply anti-detection scripts to all new pages."""
        await context.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', { get: () => false });

            // Override chrome.runtime
            window.chrome = { runtime: {} };

            // Override plugins length
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });

            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({state: Notification.permission}) :
                originalQuery(parameters)
            );
        """)

    async def new_page(self) -> Page:
        """Create a new page with stealth patches active."""
        if not self._context:
            await self._create_context()
        page = await self._context.new_page()
        return page

    async def new_context_with_proxy(
        self, proxy: Dict[str, str]
    ) -> BrowserContext:
        """Create a new browser context with a specific proxy."""
        self.proxy = proxy
        return await self._create_context()

    async def stop(self):
        """Clean shutdown."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("StealthBrowser stopped")

    @staticmethod
    def _random_user_agent() -> str:
        """Return a realistic Chrome user agent string."""
        chrome_versions = [
            "120.0.0.0", "121.0.0.0", "122.0.0.0",
        ]
        webkit_version = "537.36"
        version = random.choice(chrome_versions)
        return (
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            f"AppleWebKit/{webkit_version} (KHTML, like Gecko) "
            f"Chrome/{version} Safari/{webkit_version}"
        )


class BrowserPool:
    """Pool of browser instances for concurrent automation."""

    def __init__(
        self,
        proxy_manager: "ProxyManager",
        pool_size: int = 5,
        headless: bool = True,
    ):
        self.proxy_manager = proxy_manager
        self.pool_size = pool_size
        self.headless = headless
        self._browsers: list[StealthBrowser] = []

    async def start(self):
        """Initialize all browser instances."""
        proxies = self.proxy_manager.get_proxies(self.pool_size)
        for proxy in proxies:
            browser = StealthBrowser(
                headless=self.headless,
                proxy=proxy,
            )
            await browser.start()
            self._browsers.append(browser)
        logger.info(
            "BrowserPool started with %d browsers", len(self._browsers)
        )

    def acquire(self) -> Optional[StealthBrowser]:
        """Get an available browser instance."""
        for browser in self._browsers:
            return browser
        return None

    async def stop(self):
        """Shutdown all browser instances."""
        for browser in self._browsers:
            await browser.stop()
        self._browsers.clear()
