"""
Talos Engine - Pipeline Monitoring & Opportunity Watcher

Monitors server health, pipeline progress, and detects
automation opportunities. Sends alerts when thresholds
are breached.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Callable, Any

logger = logging.getLogger(__name__)


@dataclass
class HealthMetrics:
    """System health snapshot."""
    ram_percent: float = 0.0
    disk_percent: float = 0.0
    cpu_percent: float = 0.0
    swap_percent: float = 0.0
    uptime_seconds: int = 0
    load_avg: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    boot_id: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        """Quick health check at default thresholds."""
        return (
            self.ram_percent < 90
            and self.disk_percent < 85
            and self.cpu_percent < 95
        )

    def check_thresholds(
        self,
        ram_limit: float = 90,
        disk_limit: float = 85,
        cpu_limit: float = 95,
    ) -> List[str]:
        """Return list of breached threshold names."""
        breached = []
        if self.ram_percent >= ram_limit:
            breached.append(f"RAM ({self.ram_percent:.1f}%)")
        if self.disk_percent >= disk_limit:
            breached.append(f"DISK ({self.disk_percent:.1f}%)")
        if self.cpu_percent >= cpu_limit:
            breached.append(f"CPU ({self.cpu_percent:.1f}%)")
        return breached


class HealthCollector:
    """Collects system health metrics from /proc and psutil."""

    @staticmethod
    def collect() -> HealthMetrics:
        """Gather current system health metrics."""
        try:
            import psutil
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            return HealthMetrics(
                ram_percent=ram.percent,
                disk_percent=disk.percent,
                cpu_percent=psutil.cpu_percent(interval=1),
                swap_percent=psutil.swap_memory().percent,
                uptime_seconds=int(time.time() - psutil.boot_time()),
                load_avg=list(psutil.getloadavg()),
                boot_id=HealthCollector._get_boot_id(),
            )
        except ImportError:
            return HealthMetrics()

    @staticmethod
    def _get_boot_id() -> str:
        """Get boot UUID from /proc/sys/kernel/random/boot_id."""
        boot_file = Path("/proc/sys/kernel/random/boot_id")
        if boot_file.exists():
            return boot_file.read_text().strip()
        return "unknown"


class PipelineWatcher:
    """
    Watches pipeline health and sends alerts on threshold breaches.

    Can be configured to call alert handlers (webhook, Telegram, etc.)
    when system metrics exceed defined limits.
    """

    def __init__(
        self,
        check_interval: int = 300,
        ram_limit: float = 90,
        disk_limit: float = 85,
        cpu_limit: float = 95,
        alert_callback: Optional[Callable[[str], Any]] = None,
        state_file: str = "data/watcher_state.json",
    ):
        self.check_interval = check_interval
        self.ram_limit = ram_limit
        self.disk_limit = disk_limit
        self.cpu_limit = cpu_limit
        self.alert_callback = alert_callback
        self.state_file = Path(state_file)
        self._last_boot_id: Optional[str] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Begin periodic health monitoring."""
        self._running = True
        self._last_boot_id = HealthCollector._get_boot_id()
        self._task = asyncio.create_task(self._watch_loop())
        logger.info("PipelineWatcher started (interval=%ds)", self.check_interval)

    async def _watch_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                metrics = HealthCollector.collect()

                # Boot detection
                if metrics.boot_id != self._last_boot_id:
                    self._last_boot_id = metrics.boot_id
                    await self._alert(
                        "🔄 **System Reboot Detected**\n"
                        f"New boot ID: {metrics.boot_id[:8]}..."
                    )

                # Threshold checks
                breached = metrics.check_thresholds(
                    self.ram_limit, self.disk_limit, self.cpu_limit
                )
                if breached:
                    alert_msg = (
                        "⚠️ **Threshold Alert**\n"
                        + "\n".join(f"• {b}" for b in breached)
                    )
                    await self._alert(alert_msg)

                # Save state
                self._save_state(metrics)

            except Exception as e:
                logger.error("Watcher error: %s", e)

            await asyncio.sleep(self.check_interval)

    async def _alert(self, message: str):
        """Send alert through configured callback."""
        logger.warning("ALERT: %s", message)
        if self.alert_callback:
            try:
                if asyncio.iscoroutinefunction(self.alert_callback):
                    await self.alert_callback(message)
                else:
                    self.alert_callback(message)
            except Exception as e:
                logger.error("Alert callback failed: %s", e)

    def _save_state(self, metrics: HealthMetrics):
        """Persist watcher state to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "last_check": metrics.timestamp,
            "ram_percent": metrics.ram_percent,
            "disk_percent": metrics.disk_percent,
            "cpu_percent": metrics.cpu_percent,
            "boot_id": metrics.boot_id,
        }
        self.state_file.write_text(json.dumps(state, indent=2))

    async def stop(self):
        """Stop monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("PipelineWatcher stopped")
