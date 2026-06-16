"""
Talos Engine - Identity Fingerprint Generator

Generates realistic browser and user identity profiles for
anti-detection during web automation.
"""

import random
import hashlib
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Fingerprint:
    """A synthetic browser/user fingerprint profile."""

    user_agent: str
    platform: str
    screen_width: int
    screen_height: int
    color_depth: int
    language: str
    timezone: str
    canvas_hash: str = field(init=False)
    webgl_vendor: str
    webgl_renderer: str
    hardware_concurrency: int
    device_memory: int

    def __post_init__(self):
        # Generate a stable canvas fingerprint hash from the profile
        fingerprint_seed = f"{self.user_agent}:{self.platform}:{self.screen_width}"
        self.canvas_hash = hashlib.md5(fingerprint_seed.encode()).hexdigest()[:16]


class FingerprintGenerator:
    """Generates randomized but consistent browser fingerprints."""

    PLATFORMS = ["Win32", "MacIntel", "Linux x86_64"]
    WEBGL_VENDORS = [
        "Google Inc. (NVIDIA)",
        "Google Inc. (Intel)",
        "Google Inc. (AMD)",
    ]
    WEBGL_RENDERERS = [
        "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
        "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
        "ANGLE (AMD, AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0)",
    ]
    TIMEZONES = [
        "America/Chicago",
        "America/New_York",
        "America/Los_Angeles",
        "Europe/London",
        "Europe/Berlin",
        "Asia/Tokyo",
    ]

    @classmethod
    def generate(cls, seed: Optional[str] = None) -> Fingerprint:
        """Generate a random fingerprint, optionally seeded for consistency."""
        if seed:
            random.seed(seed)

        platform = random.choice(cls.PLATFORMS)

        return Fingerprint(
            user_agent=cls._random_user_agent(),
            platform=platform,
            screen_width=random.choice([1366, 1440, 1920, 2560]),
            screen_height=random.choice([768, 900, 1080, 1440]),
            color_depth=random.choice([24, 30]),
            language="en-US",
            timezone=random.choice(cls.TIMEZONES),
            webgl_vendor=random.choice(cls.WEBGL_VENDORS),
            webgl_renderer=random.choice(cls.WEBGL_RENDERERS),
            hardware_concurrency=random.choice([4, 8, 12, 16]),
            device_memory=random.choice([4, 8, 16]),
        )

    @staticmethod
    def _random_user_agent() -> str:
        """Generate a realistic Chrome user agent."""
        major = random.randint(118, 122)
        minor = random.randint(0, 9)
        build = random.randint(1000, 9999)
        return (
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{major}.{minor}.{build}.0 Safari/537.36"
        )
