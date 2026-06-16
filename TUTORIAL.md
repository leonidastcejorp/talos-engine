# 📖 Talos Engine — Complete Tutorial

> Step-by-step guide from zero to fully automated web operations.

---

## Prerequisites

- **VPS** running Ubuntu 24.04 LTS (provisioned via [Atlas Platform](https://github.com/leonidastcejorp/atlas-platform))
- **Python 3.11+** with venv
- **Git** installed
- **Hermes Agent** v0.16+ installed
- **Telegram Bot Token** (for notifications)
- **LLM API Key** (for Hermes AI)

---

## Step 1: Clone the Repository

```bash
cd ~/projects
git clone https://github.com/leonidastcejorp/talos-engine.git
cd talos-engine
```

---

## Step 2: Install Dependencies

```bash
# Python packages
pip install -r requirements.txt

# FlowCore in development mode
cd flowcore
pip install -e .
cd ..

# Playwright browser
python3 -m playwright install chromium
```

---

## Step 3: Configure the Framework

Edit FlowCore configuration:

```bash
nano flowcore/config/config.yaml
```

Key settings:
- `proxy.sources` — URLs to fetch free proxies
- `browser.headless` — set to `true` for server operation
- `registrar.*.enabled` — enable/disable specific registrars

---

## Step 4: Configure Hermes Agent

```bash
# Copy config template
cp hermes/config.yaml ~/.hermes/config.yaml

# Edit with your API keys
nano ~/.hermes/config.yaml
```

**Required changes:**
1. `model.api_key` — your LLM provider API key
2. `telegram.bot_token` — your Telegram bot token
3. `web.firecrawl_api_key` — Firecrawl API key (optional, for web scraping)

Copy the persona:

```bash
cp hermes/SOUL.md ~/.hermes/SOUL.md
```

Copy scripts:

```bash
cp -r hermes/scripts/* ~/.hermes/scripts/
cp -r hermes/plugins/* ~/.hermes/plugins/
```

---

## Step 5: Deploy Cron Jobs

The cron jobs handle automated monitoring, income scanning, and proxy management:

```bash
bash hermes/cron/deploy-cron.sh
```

This creates 12 cron jobs:
| Job | Schedule | Purpose |
|-----|----------|---------|
| MemStat | Hourly | RAM monitoring |
| Bootmark | Every 15min | Reboot detection |
| Session Deck | Every 30min | Context monitoring |
| DiskBay | Every 6h | Disk usage |
| Cuan Feed | Every 6h | Income opportunities |
| PortGuard | Every 6h | SSH attack detection |
| VitalSign | Every 6h | System watchdog |
| LogDesk | Every 6h | Error aggregation |
| Proxy Refresh | Every 6h | Proxy pool update |
| Daily Briefing | 16:00 daily | Full system report |
| Session Prune | Mon 03:00 | Cleanup old sessions |
| Backup | Sun 02:00 | Config backup |

**IMPORTANT**: Edit `hermes/cron/jobs.json` and update the `deliver` field to your Telegram chat ID before deploying.

---

## Step 6: Test the Monitors

```bash
# Run a watchdog check
python3 scripts/monitor.py

# Should output either:
# ✅ VitalSign — all clear (table format)
# or
# 🚨 VitalSign — alert with threshold warnings

# Run the daily briefing
python3 scripts/daily_report.py

# Check income pipeline
python3 scripts/income_pipeline.py

# Test proxy updater
python3 scripts/proxy_updater.py
```

---

## Step 7: Run Ghost Tools

The ghost tools require Playwright and are resource-intensive. Run them during low-traffic periods:

```bash
# Test Turnstile bypass capability
python3 tools/ghost_tester.py

# Create accounts (use with caution, respect ToS)
# python3 tools/ghost_creator.py --platform fiverr --count 1
```

---

## Step 8: Check Airdrops

```bash
python3 tools/airdrop_monitor.py
```

Output shows:
- Active testnet faucets
- Ongoing airdrop campaigns
- Eligibility checks

---

## Step 9: Verify Everything

```bash
# System health
python3 scripts/monitor.py

# Hermes status
hermes status

# Cron jobs
hermes cron list

# Disk usage
df -h /
```

---

## Daily Workflow

1. **Morning**: Check the daily briefing (auto-delivered at 16:00 WIB)
2. **Throughout day**: Monitor Telegram for watchdog alerts
3. **Weekly**: Review proxy pool freshness, update if needed
4. **As needed**: Run ghost tools for account creation, check new airdrops

---

## Troubleshooting

### "Playwright browser not found"
```bash
python3 -m playwright install --with-deps chromium
```

### "Hermes cron create failed"
Make sure Hermes is installed and the gateway is running:
```bash
hermes status
systemctl status hermes
```

### "Telegram notifications not delivering"
1. Check bot token in `~/.hermes/config.yaml`
2. Verify chat ID in `deliver` field of cron jobs
3. Make sure bot is added to the target group

### "Proxy pool empty"
```bash
# Force refresh
python3 scripts/proxy_updater.py

# Check sources in flowcore/config/config.yaml
```

### "Memory usage too high"
- Reduce Playwright concurrency
- Disable unused monitors via `hermes cron pause <job_id>`
- Increase swap: see Atlas Platform docs

---

## File Structure Reference

```
talos-engine/
├── README.md               # This documentation
├── TUTORIAL.md              # You are here
├── LICENSE                  # MIT
├── requirements.txt         # Python dependencies
├── flowcore/                # Automation framework
├── scripts/                 # Monitoring & pipeline
├── hermes/                  # AI agent configs
├── tools/                   # Standalone utilities
└── data/                    # Runtime data
```

---

> **Need infrastructure setup?** See [Atlas Platform](https://github.com/leonidastcejorp/atlas-platform)
>
> *"Automate everything. Guard what matters."* — Talos Engine 🦾
