#!/usr/bin/env python3
"""
Talos Engine - Error Summary Aggregator

Reads the error log (data/errors.jsonl) and produces a summary
report grouped by source and severity. Outputs plain text and
Telegram-formatted markdown.

Usage:
    python scripts/error_summary.py
    python scripts/error_summary.py --since 24h
    python scripts/error_summary.py --source monitor
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.error_log import ErrorLog, ErrorLevel, _default_log


def parse_duration(dur: str) -> float:
    """Parse a duration string like '24h', '7d', '60m' to seconds."""
    dur = dur.strip().lower()
    if dur.endswith("h"):
        return float(dur[:-1]) * 3600
    if dur.endswith("d"):
        return float(dur[:-1]) * 86400
    if dur.endswith("m"):
        return float(dur[:-1]) * 60
    return float(dur)


def main():
    parser = argparse.ArgumentParser(
        description="Talos Engine - Error Summary Aggregator"
    )
    parser.add_argument(
        "--since", type=str, default="24h",
        help="Time window (e.g., 24h, 7d, 60m). Default: 24h",
    )
    parser.add_argument(
        "--source", type=str, default=None,
        help="Filter by source (e.g., monitor, proxy_updater)",
    )
    parser.add_argument(
        "--min-level", type=str, default="WARNING",
        choices=["DEBUG", "INFO", "NOTICE", "WARNING", "ERROR", "CRITICAL", "ALERT", "EMERGENCY"],
        help="Minimum error level to show",
    )
    parser.add_argument(
        "--format", type=str, default="text",
        choices=["text", "telegram", "json"],
        help="Output format",
    )
    parser.add_argument(
        "--log-file", type=str, default="data/errors.jsonl",
        help="Path to error log file",
    )
    args = parser.parse_args()

    # Load the error log
    error_log = ErrorLog(log_file=args.log_file)
    error_log.load_from_file()

    since_seconds = parse_duration(args.since)
    since_timestamp = time.time() - since_seconds

    min_level = ErrorLevel[args.min_level.upper()]

    # Get filtered entries
    entries = error_log.get_entries(
        min_level=min_level,
        source=args.source,
        since=since_timestamp,
        limit=200,
    )

    if args.format == "json":
        import json
        print(json.dumps(
            [e.to_dict() for e in entries],
            indent=2,
        ))
        return

    if args.format == "telegram":
        print(error_log.to_telegram_table(since=since_timestamp))
        return

    # Text format
    print(f"\n{'='*60}")
    print(f"  TALOS ENGINE - Error Summary")
    print(f"  Window: {args.since} | Min Level: {args.min_level}")
    if args.source:
        print(f"  Source filter: {args.source}")
    print(f"{'='*60}\n")

    if not entries:
        print("  ✅ No errors found in the selected window.")
        return

    # Summary by source
    summary = error_log.summarize(since=since_timestamp)
    if args.source:
        summary = {args.source: summary.get(args.source, {})}

    print("  Summary by Source:")
    for source, levels in sorted(summary.items()):
        level_str = " | ".join(f"{lvl}: {cnt}" for lvl, cnt in sorted(levels.items()))
        print(f"    [{source}] {level_str}")

    # Most recent errors
    print(f"\n  Recent Errors (last {min(len(entries), 20)}):")
    for entry in entries[-20:]:
        import datetime
        ts = datetime.datetime.fromtimestamp(entry.timestamp).strftime("%m-%d %H:%M:%S")
        print(f"    {ts} {entry.emoji} [{entry.source}] {entry.message[:80]}")

    print(f"\n  Total: {len(entries)} errors in {args.since}")


if __name__ == "__main__":
    main()
