#!/usr/bin/env python3
"""
🔗 Proxy Rotator — health-checked proxy pool with rotation strategies.
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import aiohttp
from aiohttp_socks import ProxyConnector


@dataclass
class Proxy:
    url: str
    protocol: str = "http"
    latency_ms: Optional[int] = None
    alive: bool = True
    last_used: Optional[str] = None
    fail_count: int = 0
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if "://" in self.url:
            self.protocol, rest = self.url.split("://", 1)


class ProxyRotator:
    def __init__(self, proxies: Optional[list[str]] = None, test_url: str = "https://httpbin.org/ip"):
        self.test_url = test_url
        self.proxies: list[Proxy] = []
        if proxies:
            self.load(proxies)

    def load(self, proxies: list[str], tags: Optional[list[str]] = None) -> None:
        for p in proxies:
            p = p.strip()
            if not p:
                continue
            self.proxies.append(Proxy(url=p, tags=tags or []))

    def load_file(self, path: str | Path, tags: Optional[list[str]] = None) -> None:
        text = Path(path).expanduser().read_text()
        self.load(text.splitlines(), tags=tags)

    def get(self, strategy: str = "round_robin", tags: Optional[list[str]] = None) -> Proxy:
        pool = self.proxies
        if tags:
            pool = [p for p in pool if any(t in p.tags for t in tags)]
        alive = [p for p in pool if p.alive]
        if not alive:
            raise RuntimeError("no alive proxies available")
        if strategy == "random":
            return random.choice(alive)
        if strategy == "least_used":
            return min(alive, key=lambda p: p.fail_count)
        # round_robin
        oldest = min(alive, key=lambda p: p.last_used or "")
        return oldest

    async def check(self, proxy: Proxy, timeout: int = 15) -> bool:
        try:
            connector = ProxyConnector.from_url(proxy.url) if proxy.protocol in ("socks5", "socks4", "http") else None
            async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(self.test_url, proxy=None if connector else proxy.url) as resp:
                    proxy.alive = resp.status == 200
                    proxy.fail_count = 0 if proxy.alive else proxy.fail_count + 1
                    return proxy.alive
        except Exception:
            proxy.alive = False
            proxy.fail_count += 1
            return False

    async def health_check_all(self, concurrency: int = 20) -> tuple[int, int]:
        sem = asyncio.Semaphore(concurrency)

        async def _check(p: Proxy) -> bool:
            async with sem:
                return await self.check(p)

        results = await asyncio.gather(*(_check(p) for p in self.proxies))
        alive = sum(results)
        return alive, len(self.proxies) - alive
