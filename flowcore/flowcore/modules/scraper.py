"""
Talos Engine - Anti-Detection Web Scraper

High-level scraping interface with built-in rate limiting,
user-agent rotation, and anti-bot countermeasures.
"""

import asyncio
import logging
import random
from typing import Optional, Any

import aiohttp
from aiohttp_socks import ProxyConnector

from ..core.fingerprint import FingerprintGenerator

logger = logging.getLogger(__name__)


class AntiDetectionScraper:
    """
    Web scraper with built-in anti-detection measures:
    - Realistic headers
    - Randomized delays
    - Proxy support via SOCKS5/HTTP
    - Session persistence
    """

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        delay_range: tuple = (2, 5),
        max_concurrent: int = 5,
        max_retries: int = 3,
    ):
        self.proxy_url = proxy_url
        self.delay_range = delay_range
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._fingerprint = FingerprintGenerator.generate()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            connector = None
            if self.proxy_url:
                connector = ProxyConnector.from_url(self.proxy_url)

            headers = {
                "User-Agent": self._fingerprint.user_agent,
                "Accept": "text/html,application/xhtml+xml,"
                         "application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "no-cache",
            }
            self._session = aiohttp.ClientSession(
                headers=headers,
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def fetch(
        self, url: str, method: str = "GET", **kwargs
    ) -> Optional[str]:
        """Fetch a URL with retries and anti-detection delays."""
        async with self._semaphore:
            for attempt in range(self.max_retries):
                try:
                    session = await self._get_session()
                    # Random delay before request
                    await asyncio.sleep(random.uniform(*self.delay_range))

                    async with session.request(method, url, **kwargs) as resp:
                        if resp.status == 429:
                            wait = int(resp.headers.get("Retry-After", 60))
                            logger.warning(
                                "Rate limited on %s, waiting %ds", url, wait
                            )
                            await asyncio.sleep(wait)
                            continue
                        if resp.status >= 500:
                            logger.warning(
                                "Server error %d on %s, retrying", resp.status, url
                            )
                            continue
                        return await resp.text()

                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.warning(
                        "Fetch error for %s (attempt %d): %s",
                        url, attempt + 1, e,
                    )
                    if attempt == self.max_retries - 1:
                        return None
                    await asyncio.sleep(2 ** attempt)

        return None

    async def fetch_json(self, url: str, **kwargs) -> Optional[Any]:
        """Fetch and parse JSON from a URL."""
        text = await self.fetch(url, **kwargs)
        if text is None:
            return None
        import json
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("JSON parse error for %s: %s", url, e)
            return None

    async def close(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
