"""
Talos Engine - Proxy Pool Manager

Manages a pool of proxies with health checking, rotation,
and automatic refreshing from external sources.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class ProxyRecord:
    """A single proxy entry with health status."""
    url: str
    protocol: str = "http"
    host: str = ""
    port: int = 8080
    username: Optional[str] = None
    password: Optional[str] = None
    alive: bool = True
    latency_ms: float = 0.0
    fail_count: int = 0
    last_checked: float = 0.0
    last_used: float = 0.0

    @property
    def formatted(self) -> str:
        """Return proxy URL string."""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def playwright_format(self) -> Dict[str, str]:
        """Return proxy config dict for Playwright."""
        return {
            "server": f"{self.protocol}://{self.host}:{self.port}",
            "username": self.username or "",
            "password": self.password or "",
        }

    @classmethod
    def from_url(cls, url: str) -> Optional["ProxyRecord"]:
        """Parse a proxy URL into a ProxyRecord."""
        try:
            parts = url.split("://")
            protocol = parts[0] if len(parts) > 1 else "http"
            rest = parts[-1]

            auth_part = ""
            host_port = rest
            if "@" in rest:
                auth_part, host_port = rest.rsplit("@", 1)

            host, port_str = host_port.rsplit(":", 1) if ":" in host_port else (host_port, "8080")
            port = int(port_str)

            username = None
            password = None
            if ":" in auth_part:
                username, password = auth_part.split(":", 1)

            return cls(
                url=url.strip(),
                protocol=protocol,
                host=host,
                port=port,
                username=username,
                password=password,
            )
        except Exception:
            return None


class ProxyManager:
    """
    Manages a pool of proxies with rotation and health checks.

    Loads proxies from file, tests them, and provides
    the best available proxy for requests.
    """

    def __init__(
        self,
        pool_file: str = "data/proxies.txt",
        max_concurrent_checks: int = 20,
        check_timeout: int = 15,
        test_url: str = "https://httpbin.org/ip",
    ):
        self.pool_file = Path(pool_file)
        self.max_concurrent_checks = max_concurrent_checks
        self.check_timeout = check_timeout
        self.test_url = test_url
        self._proxies: List[ProxyRecord] = []
        self._lock = asyncio.Lock()

    def load_from_file(self) -> int:
        """Load proxies from pool file. Returns count loaded."""
        if not self.pool_file.exists():
            logger.warning("Proxy pool file not found: %s", self.pool_file)
            return 0

        lines = [
            line.strip()
            for line in self.pool_file.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]

        self._proxies = []
        for line in lines:
            record = ProxyRecord.from_url(line)
            if record:
                self._proxies.append(record)

        logger.info("Loaded %d proxies from %s", len(self._proxies), self.pool_file)
        return len(self._proxies)

    def save_to_file(self):
        """Save current proxy list back to file."""
        self.pool_file.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(p.formatted for p in self._proxies if p.alive)
        self.pool_file.write_text(content)
        logger.info("Saved %d alive proxies to %s", len(self._proxies), self.pool_file)

    async def health_check_all(self) -> Dict[str, int]:
        """Test all proxies concurrently. Returns alive/dead counts."""
        async with self._lock:
            semaphore = asyncio.Semaphore(self.max_concurrent_checks)

            async def check_one(proxy: ProxyRecord):
                async with semaphore:
                    await self._check_proxy(proxy)

            tasks = [check_one(p) for p in self._proxies]
            await asyncio.gather(*tasks, return_exceptions=True)

            alive = sum(1 for p in self._proxies if p.alive)
            dead = sum(1 for p in self._proxies if not p.alive)
            logger.info(
                "Health check complete: %d alive, %d dead", alive, dead
            )
            return {"alive": alive, "dead": dead}

    async def _check_proxy(self, proxy: ProxyRecord):
        """Test a single proxy for connectivity and latency."""
        try:
            proxy.last_checked = time.time()
            start = time.monotonic()

            connector = None
            if proxy.protocol in ("socks5", "socks4"):
                from aiohttp_socks import ProxyConnector
                connector = ProxyConnector.from_url(proxy.formatted)
                timeout = aiohttp.ClientTimeout(total=self.check_timeout)
                async with aiohttp.ClientSession(
                    connector=connector, timeout=timeout
                ) as session:
                    async with session.get(self.test_url) as resp:
                        proxy.alive = resp.status == 200
                        proxy.fail_count = 0 if proxy.alive else proxy.fail_count + 1
            else:
                timeout = aiohttp.ClientTimeout(total=self.check_timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(
                        self.test_url, proxy=proxy.formatted
                    ) as resp:
                        proxy.alive = resp.status == 200
                        proxy.fail_count = 0 if proxy.alive else proxy.fail_count + 1

            proxy.latency_ms = (time.monotonic() - start) * 1000

        except Exception:
            proxy.alive = False
            proxy.fail_count += 1
            proxy.last_checked = time.time()

    def get_alive_proxies(self) -> List[ProxyRecord]:
        """Return all currently alive proxies."""
        return [p for p in self._proxies if p.alive]

    def get_random_proxy(self) -> Optional[ProxyRecord]:
        """Get a random alive proxy."""
        alive = self.get_alive_proxies()
        if not alive:
            return None
        proxy = random.choice(alive)
        proxy.last_used = time.time()
        return proxy

    def get_proxies(self, count: int = 5) -> List[Dict[str, str]]:
        """Get N proxy configs in Playwright format."""
        alive = self.get_alive_proxies()
        selected = random.sample(alive, min(count, len(alive)))
        return [p.playwright_format for p in selected]

    def add_proxy(self, url: str):
        """Add a new proxy to the pool."""
        record = ProxyRecord.from_url(url)
        if record and record not in self._proxies:
            self._proxies.append(record)

    def remove_dead(self):
        """Remove all dead proxies from pool."""
        self._proxies = [p for p in self._proxies if p.alive]
