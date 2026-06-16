# 🔧 Talos Tools

Standalone automation tools for account creation, airdrop farming, and security testing.

## Tools Overview

| Tool | Purpose | Runtime |
|------|---------|---------|
| `ghost_creator.py` | Mass account creator — Fiverr, Reddit, Discord | Playwright |
| `ghost_tester.py` | Cloudflare Turnstile bypass capability tester | Playwright |
| `airdrop_monitor.py` | Multi-platform airdrop checker — Galxe, Layer3, faucets | aiohttp |
| `farming_guide.py` | Testnet farming guide with faucet URLs & earnings estimates | CLI |

## Quick Start

```bash
# Install deps
pip install playwright aiohttp aiohttp-socks pyyaml
python3 -m playwright install chromium

# Test turnstile bypass
python3 tools/ghost_tester.py

# Check active airdrops
python3 tools/airdrop_monitor.py
```

## Security Notes

- All tools use proxy support — configure `config/config.yaml`
- Rate limiting built-in to avoid IP bans
- Fingerprint randomization on every session
- No credentials stored in plaintext
