"""
Talos Engine - Form Automation Registrar

Handles automated account registration on Discord, Fiverr, Reddit, and
other platforms using Playwright with anti-detection measures.
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from ..core.browser import StealthBrowser
from ..core.fingerprint import FingerprintGenerator, Fingerprint
from ..utils.names import IdentityGenerator, Identity

logger = logging.getLogger(__name__)


@dataclass
class RegistrationResult:
    """Outcome of a registration attempt."""
    platform: str
    success: bool
    username: str
    error: Optional[str] = None
    screenshot: Optional[str] = None


class PlatformRegistrar:
    """Base class for platform-specific registration handlers."""

    PLATFORM_NAME: str = "generic"
    REGISTRATION_URL: str = ""
    SUCCESS_INDICATOR: str = ""
    TIMEOUT: int = 60000

    def __init__(
        self,
        browser: StealthBrowser,
        typing_delay: tuple = (0.05, 0.2),
        nav_delay: tuple = (1.0, 3.0),
        screenshot_dir: str = "data/screenshots",
        max_retries: int = 3,
    ):
        self.browser = browser
        self.typing_delay = typing_delay
        self.nav_delay = nav_delay
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries

    async def human_type(self, page: Page, selector: str, text: str):
        """Type text with human-like delays between keystrokes."""
        element = await page.wait_for_selector(selector, timeout=self.TIMEOUT)
        await element.click()
        await asyncio.sleep(random.uniform(*self.typing_delay))
        await element.fill("")
        for char in text:
            await element.type(char, delay=random.randint(50, 200))
        await asyncio.sleep(random.uniform(*self.nav_delay))

    async def human_click(self, page: Page, selector: str):
        """Click with a small pre-click delay to mimic human behavior."""
        await asyncio.sleep(random.uniform(0.1, 0.5))
        element = await page.wait_for_selector(selector, timeout=self.TIMEOUT)
        await element.click()
        await asyncio.sleep(random.uniform(*self.nav_delay))

    async def take_screenshot(self, page: Page, name: str) -> str:
        """Capture a screenshot for debugging."""
        path = self.screenshot_dir / f"{name}_{random.randint(1000, 9999)}.png"
        await page.screenshot(path=str(path))
        return str(path)

    async def register(self, identity: Identity) -> RegistrationResult:
        """Execute registration flow. Override in subclasses."""
        raise NotImplementedError


class DiscordRegistrar(PlatformRegistrar):
    """Discord account registration."""

    PLATFORM_NAME = "discord"
    REGISTRATION_URL = "https://discord.com/register"
    SUCCESS_INDICATOR = "text=Welcome to Discord"

    async def register(self, identity: Identity) -> RegistrationResult:
        for attempt in range(self.max_retries):
            try:
                page = await self.browser.new_page()
                await page.goto(self.REGISTRATION_URL, wait_until="networkidle")
                await asyncio.sleep(random.uniform(*self.nav_delay))

                # Fill email
                await self.human_type(page, 'input[name="email"]', identity.email)

                # Fill display name
                await self.human_type(
                    page, 'input[name="global_name"]', identity.username
                )

                # Fill username
                await self.human_type(
                    page, 'input[name="username"]', identity.username
                )

                # Fill password
                await self.human_type(
                    page, 'input[name="password"]', identity.password
                )

                # Fill date of birth
                month, day, year = identity.birth_date.split("/")
                month_map = {
                    "01": "January", "02": "February", "03": "March",
                    "04": "April", "05": "May", "06": "June",
                    "07": "July", "08": "August", "09": "September",
                    "10": "October", "11": "November", "12": "December",
                }
                await page.select_option('select[name="month"]', month_map[month])
                await page.select_option('select[name="day"]', day)
                await page.select_option('select[name="year"]', year)

                # Submit
                await self.human_click(page, 'button[type="submit"]')

                # Wait for success or captcha
                try:
                    await page.wait_for_selector(
                        self.SUCCESS_INDICATOR, timeout=15000
                    )
                    logger.info("Discord registration success: %s", identity.username)
                    return RegistrationResult(
                        platform=self.PLATFORM_NAME,
                        success=True,
                        username=identity.username,
                    )
                except PlaywrightTimeout:
                    # Check for captcha
                    if await page.query_selector('[class*="captcha"]'):
                        logger.warning("Captcha detected on Discord, attempt %d", attempt + 1)
                        return RegistrationResult(
                            platform=self.PLATFORM_NAME,
                            success=False,
                            username=identity.username,
                            error="CAPTCHA_REQUIRED",
                        )
                    # Still might have succeeded - check URL change
                    if "login" not in page.url.lower():
                        logger.info(
                            "Discord registration likely succeeded: %s", identity.username
                        )
                        return RegistrationResult(
                            platform=self.PLATFORM_NAME,
                            success=True,
                            username=identity.username,
                        )
                    return RegistrationResult(
                        platform=self.PLATFORM_NAME,
                        success=False,
                        username=identity.username,
                        error="TIMEOUT",
                    )
            except Exception as e:
                logger.error(
                    "Discord registration error (attempt %d): %s", attempt + 1, e
                )
                if attempt == self.max_retries - 1:
                    return RegistrationResult(
                        platform=self.PLATFORM_NAME,
                        success=False,
                        username=identity.username,
                        error=str(e),
                    )
            finally:
                await page.close()

        return RegistrationResult(
            platform=self.PLATFORM_NAME,
            success=False,
            username=identity.username,
            error="MAX_RETRIES",
        )


class RedditRegistrar(PlatformRegistrar):
    """Reddit account registration."""

    PLATFORM_NAME = "reddit"
    REGISTRATION_URL = "https://www.reddit.com/register/"
    SUCCESS_INDICATOR = "text=Home"

    async def register(self, identity: Identity) -> RegistrationResult:
        for attempt in range(self.max_retries):
            try:
                page = await self.browser.new_page()
                await page.goto(self.REGISTRATION_URL, wait_until="networkidle")
                await asyncio.sleep(random.uniform(*self.nav_delay))

                # Reddit registration uses email-based flow
                await self.human_type(
                    page, 'input[name="email"]', identity.email
                )

                await self.human_click(page, 'button:has-text("Continue")')
                await asyncio.sleep(random.uniform(*self.nav_delay))

                # Choose username
                await self.human_type(
                    page, 'input[name="username"]', identity.username
                )

                # Choose password
                await self.human_type(
                    page, 'input[name="password"]', identity.password
                )

                await self.human_click(page, 'button[type="submit"]')
                await asyncio.sleep(random.uniform(*self.nav_delay))

                logger.info("Reddit registration attempted: %s", identity.username)
                return RegistrationResult(
                    platform=self.PLATFORM_NAME,
                    success=True,
                    username=identity.username,
                )

            except Exception as e:
                logger.error(
                    "Reddit registration error (attempt %d): %s", attempt + 1, e
                )
                if attempt == self.max_retries - 1:
                    return RegistrationResult(
                        platform=self.PLATFORM_NAME,
                        success=False,
                        username=identity.username,
                        error=str(e),
                    )
            finally:
                await page.close()

        return RegistrationResult(
            platform=self.PLATFORM_NAME,
            success=False,
            username=identity.username,
            error="MAX_RETRIES",
        )


class FiverrRegistrar(PlatformRegistrar):
    """Fiverr account registration."""

    PLATFORM_NAME = "fiverr"
    REGISTRATION_URL = "https://www.fiverr.com/join"
    SUCCESS_INDICATOR = "text=Dashboard"

    async def register(self, identity: Identity) -> RegistrationResult:
        for attempt in range(self.max_retries):
            try:
                page = await self.browser.new_page()
                await page.goto(self.REGISTRATION_URL, wait_until="networkidle")
                await asyncio.sleep(random.uniform(*self.nav_delay))

                # Fiverr uses email-first flow
                await self.human_type(
                    page, 'input[type="email"]', identity.email
                )

                await self.human_click(page, 'button:has-text("Continue")')
                await asyncio.sleep(random.uniform(*self.nav_delay))

                # Fill in details on next step
                await self.human_type(
                    page, 'input[name="username"]', identity.username
                )
                await self.human_type(
                    page, 'input[type="password"]', identity.password
                )

                await self.human_click(page, 'button[type="submit"]')
                await asyncio.sleep(random.uniform(*self.nav_delay))

                logger.info("Fiverr registration attempted: %s", identity.username)
                return RegistrationResult(
                    platform=self.PLATFORM_NAME,
                    success=True,
                    username=identity.username,
                )

            except Exception as e:
                logger.error(
                    "Fiverr registration error (attempt %d): %s", attempt + 1, e
                )
                if attempt == self.max_retries - 1:
                    return RegistrationResult(
                        platform=self.PLATFORM_NAME,
                        success=False,
                        username=identity.username,
                        error=str(e),
                    )
            finally:
                await page.close()

        return RegistrationResult(
            platform=self.PLATFORM_NAME,
            success=False,
            username=identity.username,
            error="MAX_RETRIES",
        )


REGISTRAR_MAP: Dict[str, type] = {
    "discord": DiscordRegistrar,
    "reddit": RedditRegistrar,
    "fiverr": FiverrRegistrar,
}


class RegistrationEngine:
    """Orchestrates multi-platform registration using a pool of browsers."""

    def __init__(
        self,
        browser: StealthBrowser,
        typing_delay: tuple = (0.05, 0.2),
        nav_delay: tuple = (1.0, 3.0),
        screenshot_dir: str = "data/screenshots",
        max_retries: int = 3,
    ):
        self.browser = browser
        self.typing_delay = typing_delay
        self.nav_delay = nav_delay
        self.screenshot_dir = screenshot_dir
        self.max_retries = max_retries

    async def register_on(
        self, platform: str, identities: list[Identity]
    ) -> list[RegistrationResult]:
        """Register multiple identities on a single platform."""
        registrar_cls = REGISTRAR_MAP.get(platform.lower())
        if not registrar_cls:
            raise ValueError(
                f"Unsupported platform: {platform}. "
                f"Supported: {list(REGISTRAR_MAP.keys())}"
            )

        registrar = registrar_cls(
            browser=self.browser,
            typing_delay=self.typing_delay,
            nav_delay=self.nav_delay,
            screenshot_dir=self.screenshot_dir,
            max_retries=self.max_retries,
        )

        results = []
        for identity in identities:
            result = await registrar.register(identity)
            results.append(result)
            # Respectful delay between accounts
            await asyncio.sleep(random.uniform(5, 15))

        return results

    async def bulk_register(
        self, platforms: list[str], count: int = 10
    ) -> Dict[str, list[RegistrationResult]]:
        """Create identities and register on multiple platforms."""
        identities = IdentityGenerator.batch(count)
        all_results: Dict[str, list[RegistrationResult]] = {}

        for platform in platforms:
            logger.info(
                "Starting bulk registration on %s (%d accounts)", platform, count
            )
            results = await self.register_on(platform, identities)
            all_results[platform] = results

        return all_results
