#!/usr/bin/env python3
"""
Talos Engine - Memory Monitor

Hourly RAM check with threshold-based alerts.
Designed for cron: 0 * * * * /path/to/memory_monitor.py

Usage:
    python scripts/memory_monitor.py
    python scripts/memory_monitor.py --threshold 85
"""

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.error_log import log_error, ErrorLevel

try:
    import psutil
except ImportError:
    print("ERROR: psutil required. Install: pip install psutil")
    sys.exit(1)

DEFAULT_THRESHOLD = 85  # Alert if RAM exceeds this %


def check_memory(threshold: int = DEFAULT_THRESHOLD) -> bool:
    """
    Check RAM usage against threshold.
    Returns True if healthy, False if threshold breached.
    """
    ram = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # RAM check
    if ram.percent >= threshold:
        process = _top_process()
        log_error(
            message=f"RAM at {ram.percent:.1f}% — threshold {threshold}%",
            level=ErrorLevel.CRITICAL,
            source="memory_monitor",
            details={
                "ram_pct": ram.percent,
                "ram_used_gb": round(ram.used / (1024**3), 2),
                "ram_total_gb": round(ram.total / (1024**3), 2),
                "top_process": process,
            },
        )
        print(f"🚨 CRITICAL: RAM at {ram.percent:.1f}%")
        if process:
            print(f"   Top process: {process}")
        return False

    # Swap check
    if swap.percent >= 50:
        log_error(
            message=f"Swap at {swap.percent:.1f}% — heavy swapping detected",
            level=ErrorLevel.WARNING,
            source="memory_monitor",
            details={"swap_pct": swap.percent},
        )
        print(f"⚠️ WARNING: Swap at {swap.percent:.1f}%")
        return False

    return True


def _top_process() -> str:
    """Get the highest-memory process name."""
    try:
        processes = []
        for proc in psutil.process_iter(["name", "memory_percent"]):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        processes.sort(key=lambda p: p["memory_percent"] or 0, reverse=True)
        if processes:
            top = processes[0]
            return f"{top['name']} ({top['memory_percent']:.1f}%)"
    except Exception:
        pass
    return ""


def main():
    parser = argparse.ArgumentParser(
        description="Talos Engine - Memory Monitor"
    )
    parser.add_argument(
        "--threshold", type=int, default=DEFAULT_THRESHOLD,
        help=f"RAM usage alert threshold in %% (default: {DEFAULT_THRESHOLD})",
    )
    args = parser.parse_args()

    ram = psutil.virtual_memory()
    swap = psutil.swap_memory()

    print(f"🧠 Memory Check — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   RAM:  {ram.percent:.1f}% ({ram.used / 1024**3:.1f} / {ram.total / 1024**3:.1f} GB)")
    print(f"   Swap: {swap.percent:.1f}% ({swap.used / 1024**3:.1f} / {swap.total / 1024**3:.1f} GB)")

    healthy = check_memory(args.threshold)

    if healthy:
        print("   ✅ Memory OK")

    sys.exit(0 if healthy else 1)


if __name__ == "__main__":
    main()
