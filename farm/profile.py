#!/usr/bin/env python3
"""
🖼️ Profile Manager — isolated browser profiles + fingerprint randomization.
"""
from __future__ import annotations

import json
import random
import shutil
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Fingerprint:
    user_agent: str
    viewport: dict
    locale: str
    timezone: str
    color_scheme: str
    platform: str
    # Optional advanced fields (kept empty by default)
    webgl_vendor: str = ""
    webgl_renderer: str = ""
    fonts: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.fonts is None:
            self.fonts = []


class ProfileManager:
    UA_POOL = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:127.0) Gecko/20100101 Firefox/127.0",
    ]

    def __init__(self, base_dir: str | Path = "~/.talos/profiles"):
        self.base_dir = Path(base_dir).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _random_fp(self) -> Fingerprint:
        return Fingerprint(
            user_agent=random.choice(self.UA_POOL),
            viewport={
                "width": random.choice([1280, 1366, 1440, 1536, 1920]),
                "height": random.choice([720, 768, 864, 900, 1080]),
            },
            locale=random.choice(["en-US", "en-GB", "id-ID", "de-DE", "fr-FR"]),
            timezone=random.choice(["America/New_York", "Europe/London", "Asia/Jakarta", "Europe/Berlin"]),
            color_scheme=random.choice(["light", "dark"]),
            platform=random.choice(["Windows", "macOS", "Linux"]),
        )

    def create(self, label: str) -> Path:
        """Create a new isolated browser profile directory."""
        profile_dir = self.base_dir / label
        if profile_dir.exists():
            raise FileExistsError(f"profile already exists: {profile_dir}")
        profile_dir.mkdir(parents=True)
        fp = self._random_fp()
        (profile_dir / "fingerprint.json").write_text(json.dumps(asdict(fp), indent=2))
        (profile_dir / "created_at.txt").write_text(datetime.now().isoformat())
        return profile_dir

    def delete(self, label: str) -> None:
        profile_dir = self.base_dir / label
        if profile_dir.exists():
            shutil.rmtree(profile_dir)

    def list_profiles(self) -> list[str]:
        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]

    def get(self, label: str) -> tuple[Path, Fingerprint]:
        profile_dir = self.base_dir / label
        if not profile_dir.exists():
            raise KeyError(f"profile not found: {label}")
        fp_path = profile_dir / "fingerprint.json"
        data = json.loads(fp_path.read_text()) if fp_path.exists() else {}
        return profile_dir, Fingerprint(**data)
