# flowcore - Talos Engine Automation Framework

The core Python automation framework powering the Talos Engine.

## Overview

flowcore provides a modular, anti-detection automation framework for:

- **Web Automation** — Browser control with stealth patches and fingerprinting
- **Account Creation** — Multi-platform registration (Discord, Fiverr, Reddit)
- **Web Scraping** — Anti-bot countermeasures with proxy rotation
- **Pipeline Monitoring** — Health checks, alerts, and opportunity detection
- **Proxy Management** — Pool rotation with automatic health testing

## Architecture

```
flowcore/
├── core/           # Browser, fingerprinting
├── modules/        # Registrars, scrapers, watchers
├── utils/          # Identity gen, proxy pool
├── scripts/        # CLI entry points
├── tests/          # Unit tests
└── config/         # YAML configuration
```

## Quick Start

```bash
cd flowcore
pip install -e .

# Run bulk registration
python scripts/run_pipeline.py register -p discord -n 5

# Refresh proxy pool
python scripts/refresh_proxies.py

# Start monitoring
python scripts/run_pipeline.py watch --interval 600
```

## Core Modules

### Browser (`core/browser.py`)
Playwright wrapper with stealth patches, Proxy support, and configurable fingerprint. Use `StealthBrowser` as an async context manager.

### Fingerprint (`core/fingerprint.py`)
Generates realistic browser profiles with user agents, canvas hashes, WebGL data.

### Registrar (`modules/registrar.py`)
Form-filling automation for Discord, Reddit, Fiverr. Handles typing delays, navigation, captcha detection.

### Scraper (`modules/scraper.py`)
Anti-detection HTTP client with rate limiting, user-agent rotation, SOCKS5 proxy support.

### Watcher (`modules/watcher.py`)
System health monitoring with threshold alerts and reboot detection.

### Identity Generator (`utils/names.py`)
Synthetic identity generation: names, emails, passwords, birth dates.

### Proxy Manager (`utils/network.py`)
Proxy pool with health checking, rotation, and Playwright integration.

## Configuration

See `config/config.yaml` for all settings:
- Browser: headless mode, viewport, locale, timezone
- Proxy: pool file, refresh interval, test URL
- Registrars: platforms, delays, retry limits
- Watcher: check interval, alert thresholds

## Requirements

- Python >= 3.9
- Playwright (with `playwright install chromium`)
- See `requirements.txt` for Python deps

## License

MIT License — see `LICENSE` file.
