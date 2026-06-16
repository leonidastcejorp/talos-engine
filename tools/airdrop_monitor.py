#!/usr/bin/env python3
"""
Airdrop & Free Money Monitor — checks Galxe, Layer3, Faucet opportunities
Reports any new/active campaigns that can earn quick $
"""
import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

REPORT = []

def log(msg):
    REPORT.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def check_layer3():
    """Check Layer3.xyz for active quests"""
    try:
        req = urllib.request.Request(
            "https://api.layer3.xyz/api/trpc/quest.listActiveQuests?limit=10&offset=0",
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            quests = data.get("result", {}).get("data", {}).get("json", [])
            if quests:
                log(f"🌐 Layer3: {len(quests)} active quests found!")
                for q in quests[:5]:
                    name = q.get("title", "Unnamed")
                    reward = q.get("reward", {})
                    reward_str = json.dumps(reward) if reward else "?"
                    log(f"   • {name} — Reward: {reward_str}")
            else:
                log("🌐 Layer3: No active quests detected")
    except Exception as e:
        log(f"🌐 Layer3: Error — {e}")

def check_galxe():
    """Check Galxe for active campaigns"""
    try:
        req = urllib.request.Request(
            "https://graphigo.prd.galxe.xyz/query",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "query": "{campaigns(first:5,orderBy:CREATED_AT_DESC){edges{node{id name reward{type amount}}}}}"
            }).encode()
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            campaigns = data.get("data", {}).get("campaigns", {}).get("edges", [])
            if campaigns:
                log(f"🌟 Galxe: {len(campaigns)} campaigns found!")
                for c in campaigns[:5]:
                    node = c.get("node", {})
                    name = node.get("name", "Unnamed")
                    reward = node.get("reward", {})
                    log(f"   • {name} — Reward: {reward.get('type','?')} {reward.get('amount','?')}")
            else:
                log("🌟 Galxe: No campaigns detected")
    except Exception as e:
        log(f"🌟 Galxe: Error — {e}")

def check_faucets():
    """Check available free testnet faucets"""
    faucets = [
        ("Sepolia ETH", "https://faucet.sepolia.dev/"),
        ("Goerli ETH", "https://goerlifaucet.com/"),
        ("zkSync Sepolia", "https://portal.zksync.io/faucet"),
        ("Scroll Sepolia", "https://scroll.io/faucet"),
        ("Base Sepolia", "https://base.org/faucet"),
    ]
    log("💧 Available faucets (manual claim):")
    for name, url in faucets:
        log(f"   • {name}: {url}")

def check_free_money_reddit():
    """Check r/slavelabour for quick gigs"""
    try:
        req = urllib.request.Request(
            "https://www.reddit.com/r/slavelabour/search.json?q=paypal+crypto+bitcoin+usd&restrict_sr=on&sort=new&limit=10",
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            posts = data.get("data", {}).get("children", [])
            if posts:
                log(f"💼 r/slavelabour: {len(posts)} recent gig posts")
                for p in posts[:5]:
                    title = p.get("data", {}).get("title", "No title")
                    log(f"   • {title[:100]}")
            else:
                log("💼 r/slavelabour: No recent gigs")
    except Exception as e:
        log(f"💼 r/slavelabour: Error — {e}")

def total_opportunities():
    """Summarize everything"""
    print("=" * 60)
    print("💰 AIRDROP & FREE MONEY REPORT")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    for line in REPORT:
        print(line)
    print("=" * 60)
    print("\n🎯 NEXT STEPS:")
    print("1. Claim testnet faucets → swap/bridge → farm points")
    print("2. Complete Layer3/Galxe quests → claim token rewards")
    print("3. r/slavelabour gigs → direct PayPal/USD")
    print("4. Sell testnet tokens on faucet exchange")

if __name__ == "__main__":
    check_layer3()
    check_galxe()
    check_faucets()
    check_free_money_reddit()
    total_opportunities()
