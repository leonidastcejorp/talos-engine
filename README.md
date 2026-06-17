# 🦾 Talos Engine

> *"Automation framework for modern web operations"*
>
> **Talos** — the bronze automaton of Greek myth, guardian of Crete. Like its namesake, Talos Engine automates the repetitive, guards the perimeter, and never sleeps.

## What is Talos Engine?

Talos Engine is a comprehensive **automation framework** for web operations — airdrop farming, bug bounty reconnaissance, proxy management, account creation, and system monitoring. It's the runtime companion to [Atlas Platform](https://github.com/leonidastcejorp/atlas-platform), which handles infrastructure provisioning.

| Component | Purpose |
|-----------|---------|
| **FlowCore** | Python automation framework — browser, scraper, registrar, proxy manager |
| **Scripts** | Cron-compatible monitoring & pipeline scripts |
| **Hermes Configs** | AI agent configuration, persona, and cron job definitions |
| **Tools** | Standalone utilities — ghost account creator, airdrop monitor, farming guide |

## Architecture

```
talos-engine/
├── flowcore/           # 🧠 Python automation framework
│   ├── flowcore/
│   │   ├── core/       # Browser + fingerprint engines
│   │   ├── modules/    # Registrar, scraper, watcher
│   │   └── utils/      # Names, network, proxy management
│   ├── config/         # Framework configuration
│   ├── scripts/        # CLI entry points
│   └── tests/          # Unit tests
├── farm/              # ✈️ Airdrop farming infra (wallet, proxy, profile, runner)
├── bounty/            # 🛡️ Bug bounty recon pipeline + report generator
├── scripts/           # 📡 Monitoring & automation scripts
│   └── lib/            # Shared libraries (error logging)
├── hermes/            # 🤖 Hermes Agent configuration
│   ├── cron/           # Cron job definitions & deployer
│   ├── plugins/        # Agent plugins (RTK rewrite)
│   └── scripts/        # Agent scripts (monitoring, pipelines)
├── tools/             # 🔧 Standalone utilities
└── data/              # 📊 Runtime data
```

## Requirements

- **Python** 3.11+
- **Node.js** 22+ (for PM2, optional)
- **Playwright** Chromium
- **Hermes Agent** v0.16+ (for cron jobs & monitoring)
- **Go** 1.22+ (for security tools: nuclei, subfinder, httpx)

## Quick Install

```bash
# Clone the repo
git clone https://github.com/leonidastcejorp/talos-engine.git
cd talos-engine

# Install Python deps
pip install -r requirements.txt

# Install FlowCore in dev mode
cd flowcore && pip install -e . && cd ..

# Install Playwright browser
python3 -m playwright install chromium

# Copy Hermes configs to your Hermes directory
cp hermes/config.yaml ~/.hermes/config.yaml
cp hermes/SOUL.md ~/.hermes/SOUL.md
cp -r hermes/scripts/* ~/.hermes/scripts/
cp -r hermes/plugins/* ~/.hermes/plugins/

# Deploy cron jobs
bash hermes/cron/deploy-cron.sh

# Verify
python3 scripts/monitor.py
```

## New Modules

### 🌾 Farm (Airdrop Farming)

| Module | File | Description |
|--------|------|-------------|
| Wallet | `farm/wallet.py` | Encrypted HD wallet manager for EVM |
| Proxy | `farm/proxy.py` | Health-checked proxy pool + rotation |
| Profile | `farm/profile.py` | Isolated browser profiles + fingerprint |
| Runner | `farm/runner.py` | Execute tasks per wallet/profile/proxy |

### 🛡️ Bounty (Bug Bounty Recon)

| Module | File | Description |
|--------|------|-------------|
| Recon | `bounty/recon.py` | subfinder → httpx → nuclei pipeline |
| Report | `bounty/report.py` | Markdown report generator |

## Components

### FlowCore Framework

| Module | File | Description |
|--------|------|-------------|
| Browser | `flowcore/core/browser.py` | Playwright wrapper — stealth, fingerprint, proxy, multi-session |
| Fingerprint | `flowcore/core/fingerprint.py` | Browser fingerprint generator — canvas, WebGL, fonts |
| Registrar | `flowcore/modules/registrar.py` | Auto-registration — Discord, Fiverr, Reddit |
| Scraper | `flowcore/modules/scraper.py` | Anti-detection web scraper with rotation |
| Watcher | `flowcore/modules/watcher.py` | Pipeline health monitoring & alerts |
| Names | `flowcore/utils/names.py` | Random identity generation |
| Network | `flowcore/utils/network.py` | Proxy pool manager — health checks, rotation |

### Monitoring Scripts

| Script | Schedule | What It Does |
|--------|----------|-------------|
| `monitor.py` | Every 6h | RAM/Disk/CPU watchdog — silent when healthy |
| `daily_report.py` | Daily 16:00 | Token usage, system health, opportunities |
| `memory_monitor.py` | Hourly | RAM/swap threshold alerts |
| `disk_alert.sh` | Every 6h | Disk usage check with directory analysis |
| `context_monitor.py` | Every 30min | Hermes session context monitoring |
| `reboot_monitor.py` | Every 15min | Boot detection & notification |
| `ssh_attack_monitor.py` | Every 6h | Brute-force detection from auth.log |
| `income_pipeline.py` | Every 6h | Reddit/Freelancer opportunity scraper |
| `proxy_updater.py` | Every 6h | Free proxy list refresh & testing |
| `error_summary.py` | Every 6h | Structured error log aggregation |
| `prune.sh` | Weekly Mon | Session cleanup (>30 days) |
| `vps_backup.sh` | Weekly Sun | Configuration backup |

### Standalone Tools

| Tool | Description |
|------|-------------|
| `ghost_creator.py` | Mass account creator with Playwright — Fiverr, Reddit, Discord |
| `ghost_tester.py` | Cloudflare Turnstile bypass capability tester |
| `airdrop_monitor.py` | Multi-platform airdrop checker — Galxe, Layer3, faucets |
| `farming_guide.py` | Testnet farming guide with faucet URLs & earnings estimates |

## Configuration

All configuration is in YAML files:

- **FlowCore**: `flowcore/config/config.yaml` — browser settings, proxy sources, registrar credentials
- **Hermes**: `hermes/config.yaml` — AI model, API keys, Telegram, cron schedules

### API Keys Required

| Service | Config Path | Purpose |
|---------|------------|---------|
| LLM Provider | `hermes/config.yaml` → `model.api_key` | AI reasoning |
| Telegram Bot | `hermes/config.yaml` → `telegram.bot_token` | Notifications |
| Firecrawl | `hermes/config.yaml` → `web.firecrawl_api_key` | Web scraping |
| FAL | `hermes/config.yaml` → `image_gen.fal_key` | Image generation |

All keys use `YOUR_*_HERE` placeholders — replace before deploying.

## Security Notes

- **All scripts are read-only** — they monitor, they don't modify system state
- **Hermes runs as isolated user** (`hermes`) with systemd sandboxing
- **No credentials in plaintext** — use environment variables or Hermes secrets
- **Proxy support on all network tools** — rotate IPs, avoid tracking
- **Rate limiting built-in** — prevent API bans and IP blocks

## Companion Repository

This is the **runtime** half of the system. For infrastructure provisioning, see:

🔗 [**Atlas Platform**](https://github.com/leonidastcejorp/atlas-platform) — one-command VPS setup + hardening

## License

MIT — see [LICENSE](LICENSE)

---

> *"Automate everything. Guard what matters."*
>
> — Talos Engine 🦾
