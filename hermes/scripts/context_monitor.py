#!/usr/bin/env python3
"""
Talos Engine - Context Monitor

Monitors Hermes Agent session context usage and warns
when approaching token limits.

Usage:
    python scripts/context_monitor.py
    python scripts/context_monitor.py --limit 80000
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.error_log import log_error, ErrorLevel

DEFAULT_STATE_DB = os.path.expanduser("~/.hermes/state.db")
DEFAULT_TOKEN_LIMIT = 100000  # Warn when context approaches this


def get_context_usage(db_path: str) -> dict:
    """Extract context usage from Hermes Agent state."""
    import sqlite3

    result = {
        "active_sessions": 0,
        "avg_tokens_per_session": 0,
        "max_tokens_in_session": 0,
        "total_tokens_loaded": 0,
    }

    if not os.path.exists(db_path):
        return result

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()

        # Try to get session context info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        if "conversations" in tables:
            try:
                cursor.execute(
                    "SELECT COUNT(*), AVG(prompt_tokens + completion_tokens), "
                    "MAX(prompt_tokens + completion_tokens), "
                    "SUM(prompt_tokens + completion_tokens) "
                    "FROM conversations"
                )
                row = cursor.fetchone()
                if row and row[0]:
                    result["active_sessions"] = row[0] or 0
                    result["avg_tokens_per_session"] = int(row[1] or 0)
                    result["max_tokens_in_session"] = row[2] or 0
                    result["total_tokens_loaded"] = row[3] or 0
            except sqlite3.OperationalError:
                pass

        conn.close()
    except Exception as e:
        print(f"DB read warning: {e}")

    return result


def check_context(limit: int = DEFAULT_TOKEN_LIMIT) -> dict:
    """Check context usage and alert if near limit."""
    ctx = get_context_usage(DEFAULT_STATE_DB)

    alerts = []
    if ctx["max_tokens_in_session"] > limit * 0.8:
        alerts.append(
            f"Session approaching token limit: "
            f"{ctx['max_tokens_in_session']:,} / {limit:,}"
        )
        log_error(
            message=f"Context limit approaching: {ctx['max_tokens_in_session']} tokens",
            level=ErrorLevel.WARNING,
            source="context_monitor",
            details=ctx,
        )

    ctx["alerts"] = alerts
    ctx["limit"] = limit
    ctx["usage_pct"] = (
        round(ctx["max_tokens_in_session"] / limit * 100, 1)
        if ctx["max_tokens_in_session"] > 0
        else 0
    )

    return ctx


def main():
    parser = argparse.ArgumentParser(
        description="Talos Engine - Context Monitor"
    )
    parser.add_argument(
        "--limit", type=int, default=DEFAULT_TOKEN_LIMIT,
        help=f"Token limit warning threshold (default: {DEFAULT_TOKEN_LIMIT})",
    )
    parser.add_argument(
        "--state-db", type=str, default=DEFAULT_STATE_DB,
        help="Path to Hermes Agent state.db",
    )
    args = parser.parse_args()

    ctx = get_context_usage(args.state_db)

    print("📊 Hermes Agent Context Usage")
    print(f"   Active sessions:    {ctx['active_sessions']}")
    print(f"   Avg tokens/session: {ctx['avg_tokens_per_session']:,}")
    print(f"   Max tokens/session: {ctx['max_tokens_in_session']:,}")
    print(f"   Total tokens loaded: {ctx['total_tokens_loaded']:,}")

    # Check against limit
    pct = (
        ctx["max_tokens_in_session"] / args.limit * 100
        if ctx["max_tokens_in_session"] > 0
        else 0
    )
    print(f"   Limit: {args.limit:,} tokens ({pct:.1f}% used)")

    if pct > 80:
        print(f"\n⚠️ WARNING: Context usage is high ({pct:.1f}%)!")
        print("   Consider running: hermes prune")
        sys.exit(1)

    print("\n✅ Context usage is healthy")


if __name__ == "__main__":
    main()
