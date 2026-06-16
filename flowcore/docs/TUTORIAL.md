# Talos Engine - Flowcore Tutorial

This tutorial walks through setting up and using the flowcore automation framework.

---

## Prerequisites

- Python 3.9+
- Playwright browsers: `playwright install chromium`
- A proxy list file (optional, for proxy features)

## Step 1: Installation

```bash
cd flowcore
pip install -r requirements.txt
pip install -e .
```

## Step 2: Configure

Edit `config/config.yaml` to match your environment:

```yaml
browser:
  headless: true       # Set false for debugging
  viewport:
    width: 1280
    height: 720

proxy:
  pool_file: "data/proxies.txt"
```

## Step 3: First Pipeline — Bulk Registration

Create 5 Discord accounts:

```bash
python scripts/run_pipeline.py register -p discord -n 5
```

Register on multiple platforms:

```bash
python scripts/run_pipeline.py register -p discord fiverr reddit -n 10
```

With visible browser windows for debugging:

```bash
python scripts/run_pipeline.py register -p discord -n 3 --no-headless
```

## Step 4: Proxy Pool Management

Refresh your proxy list from free sources:

```bash
python scripts/refresh_proxies.py
```

Use a custom pool file:

```bash
python scripts/refresh_proxies.py -f /path/to/my/proxies.txt
```

## Step 5: Web Scraping

Scrape a single URL with anti-detection:

```bash
python scripts/run_pipeline.py scrape -u https://example.com
```

With a proxy:

```bash
python scripts/run_pipeline.py scrape -u https://example.com --proxy socks5://user:pass@host:1080
```

## Step 6: Pipeline Monitoring

Start the watcher to monitor system health:

```bash
python scripts/run_pipeline.py watch --interval 600
```

The watcher checks RAM, disk, CPU and detects system reboots.

## Using flowcore as a Library

### Browser Automation

```python
import asyncio
from flowcore.core.browser import StealthBrowser

async def main():
    async with StealthBrowser(headless=True) as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")
        print(await page.title())

asyncio.run(main())
```

### Identity Generation

```python
from flowcore.utils.names import IdentityGenerator

identity = IdentityGenerator.generate()
print(f"Username: {identity.username}")
print(f"Email: {identity.email}")
print(f"Password: {identity.password}")

# Generate a batch
identities = IdentityGenerator.batch(50)
```

### Fingerprint Generation

```python
from flowcore.core.fingerprint import FingerprintGenerator

fingerprint = FingerprintGenerator.generate()
print(f"User Agent: {fingerprint.user_agent}")
print(f"Platform: {fingerprint.platform}")
print(f"Canvas Hash: {fingerprint.canvas_hash}")
```

### Proxy Management

```python
import asyncio
from flowcore.utils.network import ProxyManager

async def main():
    manager = ProxyManager(pool_file="data/proxies.txt")
    manager.load_from_file()

    # Test all proxies
    results = await manager.health_check_all()
    print(f"Alive: {results['alive']}, Dead: {results['dead']}")

    # Get a random working proxy
    proxy = manager.get_random_proxy()
    if proxy:
        print(f"Using: {proxy.formatted}")

asyncio.run(main())
```

### Scraping

```python
import asyncio
from flowcore.modules.scraper import AntiDetectionScraper

async def main():
    scraper = AntiDetectionScraper()
    content = await scraper.fetch("https://httpbin.org/json")
    if content:
        print(content)
    await scraper.close()

asyncio.run(main())
```

### Watcher with Custom Alerts

```python
import asyncio
from flowcore.modules.watcher import PipelineWatcher

async def my_alert(message: str):
    # Send to Telegram, Slack, email, etc.
    print(f"ALERT: {message}")

async def main():
    watcher = PipelineWatcher(
        check_interval=300,
        ram_limit=85,
        disk_limit=80,
        cpu_limit=90,
        alert_callback=my_alert,
    )
    await watcher.start()
    # Run for 1 hour
    await asyncio.sleep(3600)
    await watcher.stop()

asyncio.run(main())
```

## Troubleshooting

### "Browser not installed" error
```bash
playwright install chromium
playwright install-deps chromium
```

### Proxy connection failures
- Verify proxy format: `protocol://[user:pass@]host:port`
- Run health check: `python scripts/refresh_proxies.py`
- Check your proxy list is valid

### Registration failures
- Some platforms require CAPTCHA solving (not included)
- Try `--no-headless` to watch browser behavior
- Increase delays in `config.yaml`

### High memory usage
- Reduce `max_concurrent` in config
- Run fewer registrations at a time
- Close unused browser contexts

## Next Steps

- Integrate with Hermes Agent for scheduling
- Set up cron jobs for automated proxy refreshing
- Connect watcher to Telegram/Slack for alerts
- Explore the standalone tools in `tools/` directory
