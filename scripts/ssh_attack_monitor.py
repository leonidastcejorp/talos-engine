#!/usr/bin/env python3
"""
Talos Engine - SSH Attack Monitor

Monitors authentication logs for SSH brute-force attempts
and sends alerts when thresholds are exceeded.

Usage:
    python scripts/ssh_attack_monitor.py
    python scripts/ssh_attack_monitor.py --threshold 20 --period 3600
"""

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.error_log import log_error, ErrorLevel

# Common auth log paths
AUTH_LOG_PATHS = [
    "/var/log/auth.log",
    "/var/log/secure",
]

# Regex patterns for failed SSH attempts
FAILED_PATTERNS = [
    re.compile(r"Failed password for .* from (\d+\.\d+\.\d+\.\d+) port", re.I),
    re.compile(r"authentication failure.*rhost=(\d+\.\d+\.\d+\.\d+)", re.I),
    re.compile(r"Invalid user .* from (\d+\.\d+\.\d+\.\d+)", re.I),
    re.compile(r"Connection closed by authenticating user .* (\d+\.\d+\.\d+\.\d+)", re.I),
]

STATE_FILE = Path("data/ssh_monitor_state.json")


def find_auth_log() -> Path:
    """Find the system auth log file."""
    for path in AUTH_LOG_PATHS:
        p = Path(path)
        if p.exists():
            return p
    return None


def parse_failed_attempts(log_path: Path, since: float) -> dict:
    """
    Parse auth log for failed SSH attempts since timestamp.
    Returns dict of {ip: count}.
    """
    if not log_path or not log_path.exists():
        return {}

    attempts = defaultdict(int)
    try:
        with open(log_path, "r", errors="ignore") as f:
            # Read last 5000 lines for efficiency
            lines = []
            for line in f:
                lines.append(line)
                if len(lines) > 5000:
                    lines.pop(0)

            for line in lines:
                # Try to extract timestamp from syslog format
                # e.g., "Jun 17 10:30:45"
                for pattern in FAILED_PATTERNS:
                    match = pattern.search(line)
                    if match:
                        ip = match.group(1)
                        # Skip local/private IPs in count
                        if not ip.startswith(("10.", "192.168.", "172.16.")):
                            attempts[ip] += 1
                        break
    except Exception as e:
        print(f"Log parse error: {e}")

    return dict(attempts)


def load_state() -> dict:
    """Load last monitoring state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {"last_position": 0, "last_check": 0, "known_ips": {}}


def save_state(state: dict):
    """Save monitoring state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def check_attacks(threshold: int = 10, period: int = 3600) -> dict:
    """
    Check for SSH attack patterns.
    Returns summary dict with attack IPs.
    """
    log_path = find_auth_log()
    if not log_path:
        return {"error": "No auth log found", "attacks": []}

    now = time.time()
    since = now - period

    attempts = parse_failed_attempts(log_path, since)
    state = load_state()

    # Find IPs exceeding threshold
    attacks = []
    for ip, count in attempts.items():
        if count >= threshold:
            known = state.get("known_ips", {}).get(ip, 0)
            attacks.append({
                "ip": ip,
                "count": count,
                "previously_known": known > 0,
            })

    # Update state
    state["last_check"] = now
    state["known_ips"] = {ip: max(attempts.get(ip, 0), state.get("known_ips", {}).get(ip, 0))
                          for ip in set(list(attempts.keys()) + list(state.get("known_ips", {}).keys()))}
    save_state(state)

    return {
        "period_hours": round(period / 3600, 1),
        "threshold": threshold,
        "total_unique_ips": len(attempts),
        "attacks": sorted(attacks, key=lambda a: a["count"], reverse=True),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Talos Engine - SSH Attack Monitor"
    )
    parser.add_argument(
        "--threshold", type=int, default=10,
        help="Alert threshold per IP (default: 10 attempts)",
    )
    parser.add_argument(
        "--period", type=int, default=3600,
        help="Analysis period in seconds (default: 3600 = 1 hour)",
    )
    args = parser.parse_args()

    log_path = find_auth_log()
    if not log_path:
        print("⚠️ No auth log found at standard paths")
        print(f"   Checked: {', '.join(AUTH_LOG_PATHS)}")
        sys.exit(0)

    result = check_attacks(args.threshold, args.period)

    print(f"🔐 SSH Attack Monitor — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Log file: {log_path}")
    print(f"   Period: {result['period_hours']}h")
    print(f"   Threshold: {result['threshold']} attempts/IP")
    print(f"   Unique IPs seen: {result['total_unique_ips']}")

    if result["attacks"]:
        print(f"\n🚨 ATTACK DETECTED — {len(result['attacks'])} IPs exceed threshold:")
        for attack in result["attacks"]:
            tag = " (repeat)" if attack["previously_known"] else " (new)"
            print(f"   • {attack['ip']}: {attack['count']} attempts{tag}")

        log_error(
            message=f"SSH attack detected: {len(result['attacks'])} IPs exceeding threshold",
            level=ErrorLevel.ALERT,
            source="ssh_attack_monitor",
            details=result,
        )
        sys.exit(1)
    else:
        print("\n✅ No attacks detected")
        sys.exit(0)


if __name__ == "__main__":
    main()
