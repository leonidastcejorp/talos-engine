"""
Talos Engine - Structured Error Logger

Provides leveled error logging with filtering, aggregation,
and Telegram-formatted output for monitoring scripts.
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Dict, List, Optional


class ErrorLevel(IntEnum):
    """Error severity levels matching syslog."""
    DEBUG = 7
    INFO = 6
    NOTICE = 5
    WARNING = 4
    ERROR = 3
    CRITICAL = 2
    ALERT = 1
    EMERGENCY = 0


LEVEL_NAMES = {
    ErrorLevel.DEBUG: "DEBUG",
    ErrorLevel.INFO: "INFO",
    ErrorLevel.NOTICE: "NOTICE",
    ErrorLevel.WARNING: "WARNING",
    ErrorLevel.ERROR: "ERROR",
    ErrorLevel.CRITICAL: "CRITICAL",
    ErrorLevel.ALERT: "ALERT",
    ErrorLevel.EMERGENCY: "EMERGENCY",
}

LEVEL_EMOJI = {
    ErrorLevel.DEBUG: "🔍",
    ErrorLevel.INFO: "ℹ️",
    ErrorLevel.NOTICE: "📌",
    ErrorLevel.WARNING: "⚠️",
    ErrorLevel.ERROR: "❌",
    ErrorLevel.CRITICAL: "🔥",
    ErrorLevel.ALERT: "🚨",
    ErrorLevel.EMERGENCY: "💀",
}


@dataclass
class ErrorEntry:
    """A single error log entry."""
    timestamp: float = field(default_factory=time.time)
    level: ErrorLevel = ErrorLevel.ERROR
    source: str = "unknown"
    message: str = ""
    details: Optional[dict] = None

    @property
    def level_name(self) -> str:
        return LEVEL_NAMES.get(self.level, "UNKNOWN")

    @property
    def emoji(self) -> str:
        return LEVEL_EMOJI.get(self.level, "❓")

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "level": self.level.value,
            "level_name": self.level_name,
            "source": self.source,
            "message": self.message,
            "details": self.details,
        }

    def to_telegram_line(self) -> str:
        """Format as a single Telegram message line."""
        import datetime
        ts = datetime.datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")
        return f"{self.emoji} `{ts}` **{self.source}**: {self.message}"


class ErrorLog:
    """In-memory error log with filtering and aggregation."""

    def __init__(
        self,
        log_file: Optional[str] = None,
        min_level: ErrorLevel = ErrorLevel.WARNING,
        max_entries: int = 1000,
    ):
        self.log_file = Path(log_file) if log_file else None
        self.min_level = min_level
        self.max_entries = max_entries
        self._entries: List[ErrorEntry] = []

    def log(
        self,
        message: str,
        level: ErrorLevel = ErrorLevel.ERROR,
        source: str = "unknown",
        details: Optional[dict] = None,
    ):
        """Record an error entry. Drops entries below min_level."""
        if level > self.min_level:
            return

        entry = ErrorEntry(
            level=level,
            source=source,
            message=message,
            details=details,
        )
        self._entries.append(entry)

        # Trim if over max
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries:]

        # Persist if file is set
        if self.log_file:
            self._append_to_file(entry)

    def _append_to_file(self, entry: ErrorEntry):
        """Append a JSON line to the log file."""
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception:
            pass

    def load_from_file(self):
        """Load entries from a JSON-lines log file."""
        if not self.log_file or not self.log_file.exists():
            return
        with open(self.log_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = ErrorEntry(
                        timestamp=data.get("timestamp", 0),
                        level=ErrorLevel(data.get("level", 3)),
                        source=data.get("source", "unknown"),
                        message=data.get("message", ""),
                        details=data.get("details"),
                    )
                    self._entries.append(entry)
                except (json.JSONDecodeError, ValueError):
                    pass

    def get_entries(
        self,
        min_level: Optional[ErrorLevel] = None,
        source: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 50,
    ) -> List[ErrorEntry]:
        """Filter and return entries."""
        results = self._entries

        if min_level is not None:
            results = [e for e in results if e.level <= min_level]
        if source is not None:
            results = [e for e in results if e.source == source]
        if since is not None:
            results = [e for e in results if e.timestamp >= since]

        return results[-limit:]

    def summarize(self, since: Optional[float] = None) -> Dict[str, dict]:
        """Aggregate errors by source and level."""
        entries = self.get_entries(since=since) if since else self._entries
        summary = defaultdict(lambda: defaultdict(int))
        for entry in entries:
            summary[entry.source][entry.level_name] += 1

        return {
            source: dict(level_counts)
            for source, level_counts in summary.items()
        }

    def to_telegram_table(self, since: Optional[float] = None) -> str:
        """Format error summary as a Telegram Markdown table."""
        entries = self.get_entries(since=since, limit=50)
        if not entries:
            return "✅ No errors in the selected period."

        lines = ["📊 *Error Summary*", ""]
        lines.append("| Time | Level | Source | Message |")
        lines.append("|---|---|---|---|")
        for entry in entries[-20:]:
            import datetime
            ts = datetime.datetime.fromtimestamp(entry.timestamp).strftime("%H:%M")
            lines.append(
                f"| {ts} | {entry.emoji} | {entry.source} | "
                f"{entry.message[:50]} |"
            )
        return "\n".join(lines)

    def clear(self):
        """Clear all entries."""
        self._entries.clear()


# Global error log instance (used by monitoring scripts)
_default_log = ErrorLog(log_file="data/errors.jsonl", min_level=ErrorLevel.WARNING)


def log_error(
    message: str,
    level: ErrorLevel = ErrorLevel.ERROR,
    source: str = "unknown",
    details: Optional[dict] = None,
):
    """Convenience function to log to the default error log."""
    _default_log.log(message=message, level=level, source=source, details=details)


def get_error_summary(since: Optional[float] = None) -> str:
    """Get a Telegram-formatted error summary."""
    return _default_log.to_telegram_table(since=since)
