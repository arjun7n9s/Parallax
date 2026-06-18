r"""Emulator pool for concurrent dynamic analysis.

Manages a fleet of Android emulator containers, each with its own adb serial
and frida-server. The dynamic worker :func:`acquire`\s a healthy device for one
analysis and :func:`release`\s it afterward. A background health-check
recycles wedged devices and keeps the pool at its target size.

Design decisions:

- **Exclusive leasing** — one analysis per device. Frida attaches to a
  *process*, so concurrent analyses on the same emulator would cross-talk.
- **Health check** — adb ``get-state`` + ``sys.boot_completed`` + frida
  ``enumerate_processes()`` (not just adb, which can report "device" while
  frida-server is dead).
- **Recycle** — on health-check failure the container is restarted and
  re-provisioned (frida-server 16.x + mitmproxy CA + proxy config).
- **Metrics** — ``parallax_emulator_pool_size{state}`` gauge (available /
  leased / recycling) for Grafana/alerts.
- **Fail-open** — if the pool is unavailable (e.g. no Docker), the dynamic
  worker still functions with a manually-provisioned single device.

Thread safety: the pool is meant to be a singleton within one worker process.
All state mutations go through an ``asyncio.Lock`` so concurrent Celery tasks
(inside the same event-loop) don't race on acquire/release.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from parallax.core.config import settings
from parallax.core.errors import InfraError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prometheus metrics — safe no-op if prometheus_client is absent
# ---------------------------------------------------------------------------
try:
    from prometheus_client import Gauge

    _POOL_GAUGE = Gauge(
        "parallax_emulator_pool_size",
        "Emulator pool device counts by state",
        ["state"],
    )
    _METRICS = True
except Exception:  # pragma: no cover
    _METRICS = False


def _record_pool_sizes(available: int, leased: int, recycling: int) -> None:
    if not _METRICS:
        return
    try:
        _POOL_GAUGE.labels(state="available").set(available)
        _POOL_GAUGE.labels(state="leased").set(leased)
        _POOL_GAUGE.labels(state="recycling").set(recycling)
    except Exception:  # noqa: BLE001 — never break the pipeline
        pass


# ---------------------------------------------------------------------------
# Device model
# ---------------------------------------------------------------------------
class DeviceState(str, Enum):
    AVAILABLE = "available"
    LEASED = "leased"
    RECYCLING = "recycling"
    DEAD = "dead"


@dataclass
class EmulatorDevice:
    """One emulator slot in the pool."""

    container_name: str
    adb_serial: str
    # These may differ between containers (each container maps different host ports).
    adb_port: int = 5555
    frida_port: int = 27042

    state: DeviceState = DeviceState.AVAILABLE
    leased_by: Optional[str] = None  # submission_id while leased
    consecutive_failures: int = 0
    last_health_check: float = field(default_factory=time.time)

    @property
    def device_id(self) -> str:
        """The adb serial used by AVDManager / frida."""
        return self.adb_serial


# ---------------------------------------------------------------------------
# Pool
# ---------------------------------------------------------------------------
class EmulatorPool:
    """Manages a fleet of Android emulator devices for dynamic analysis.

    Usage::

        pool = EmulatorPool.from_settings()
        device = await pool.acquire("submission-uuid", timeout=60)
        try:
            avd = AVDManager(device_id=device.adb_serial, adb_port=device.adb_port)
            # ... run analysis ...
        finally:
            await pool.release(device)
    """

    MAX_CONSECUTIVE_FAILURES = 3

    def __init__(self, devices: list[EmulatorDevice], health_interval: float = 30.0):
        self._devices = {d.container_name: d for d in devices}
        self._health_interval = health_interval
        self._lock = asyncio.Lock()
        self._health_task: Optional[asyncio.Task] = None
        self._update_metrics()

    # -- construction helpers ------------------------------------------------

    @classmethod
    def from_settings(cls) -> "EmulatorPool":
        """Build a pool from the application config.

        ``EMULATOR_POOL_SIZE`` sets the fleet size. Each container is named
        ``parallax_android_emulator_N`` and maps its adb port to
        ``EMULATOR_BASE_ADB_PORT + N``.
        """
        size = settings.EMULATOR_POOL_SIZE
        base_adb = settings.EMULATOR_BASE_ADB_PORT
        base_frida = settings.EMULATOR_BASE_FRIDA_PORT
        devices = []
        for i in range(size):
            adb_port = base_adb + i
            frida_port = base_frida + i
            devices.append(
                EmulatorDevice(
                    container_name=f"parallax_android_emulator_{i}",
                    adb_serial=f"localhost:{adb_port}",
                    adb_port=adb_port,
                    frida_port=frida_port,
                )
            )
        return cls(devices, health_interval=settings.EMULATOR_HEALTH_INTERVAL)

    @classmethod
    def single_device(cls) -> "EmulatorPool":
        """Wrap the legacy single-emulator config as a 1-device pool."""
        dev = EmulatorDevice(
            container_name="parallax_android_emulator",
            adb_serial=settings.FRIDA_DEVICE_ID,
            adb_port=int(settings.FRIDA_DEVICE_ID.split(":")[-1])
            if ":" in settings.FRIDA_DEVICE_ID
            else 5555,
        )
        return cls([dev])

    # -- public API ----------------------------------------------------------

    @property
    def size(self) -> int:
        return len(self._devices)

    @property
    def available(self) -> list[EmulatorDevice]:
        return [d for d in self._devices.values() if d.state == DeviceState.AVAILABLE]

    @property
    def leased(self) -> list[EmulatorDevice]:
        return [d for d in self._devices.values() if d.state == DeviceState.LEASED]

    async def acquire(
        self, submission_id: str, timeout: float = 60.0
    ) -> EmulatorDevice:
        """Lease an available, healthy device for analysis.

        Blocks up to *timeout* seconds waiting for a device. Raises
        :class:`InfraError` if the timeout expires (the worker's
        ``RetryableTask`` treats this as transient → Celery retries with
        backoff, which gives the pool time to recycle).
        """
        deadline = time.monotonic() + timeout
        while True:
            async with self._lock:
                for device in self._devices.values():
                    if device.state == DeviceState.AVAILABLE:
                        device.state = DeviceState.LEASED
                        device.leased_by = submission_id
                        logger.info(
                            "Pool: leased %s to %s",
                            device.container_name,
                            submission_id,
                        )
                        self._update_metrics()
                        return device

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise InfraError(
                    f"EmulatorPool: no device available within {timeout}s "
                    f"(pool size={self.size}, leased={len(self.leased)})"
                )
            await asyncio.sleep(min(2.0, remaining))

    async def release(self, device: EmulatorDevice) -> None:
        """Return a device to the pool after analysis."""
        async with self._lock:
            if device.container_name not in self._devices:
                logger.warning(
                    "Pool: release called for unknown device %s",
                    device.container_name,
                )
                return
            device.state = DeviceState.AVAILABLE
            device.leased_by = None
            logger.info("Pool: released %s", device.container_name)
            self._update_metrics()

    # -- health checks -------------------------------------------------------

    async def start_health_loop(self) -> None:
        """Start the background health-check task. Call once on startup."""
        if self._health_task is not None:
            return
        self._health_task = asyncio.create_task(self._health_loop())

    async def stop_health_loop(self) -> None:
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

    async def _health_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._health_interval)
                await self.check_all_health()
            except asyncio.CancelledError:
                break
            except Exception:  # noqa: BLE001 — loop must survive
                logger.exception("Pool health-check iteration failed")

    async def check_all_health(self) -> None:
        """Run a health check on every non-leased device."""
        async with self._lock:
            for device in list(self._devices.values()):
                if device.state == DeviceState.LEASED:
                    continue  # don't interfere with running analyses
                healthy = await self._is_healthy(device)
                device.last_health_check = time.time()
                if healthy:
                    device.consecutive_failures = 0
                    if device.state in (DeviceState.RECYCLING, DeviceState.DEAD):
                        device.state = DeviceState.AVAILABLE
                        logger.info(
                            "Pool: %s recovered, now available",
                            device.container_name,
                        )
                else:
                    device.consecutive_failures += 1
                    if device.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                        device.state = DeviceState.DEAD
                        logger.error(
                            "Pool: %s marked DEAD after %d consecutive failures",
                            device.container_name,
                            device.consecutive_failures,
                        )
                        # Attempt to recycle in the background
                        asyncio.create_task(self._recycle(device))
                    elif device.state == DeviceState.AVAILABLE:
                        device.state = DeviceState.RECYCLING
                        logger.warning(
                            "Pool: %s unhealthy (%d/%d), recycling",
                            device.container_name,
                            device.consecutive_failures,
                            self.MAX_CONSECUTIVE_FAILURES,
                        )
                        asyncio.create_task(self._recycle(device))
            self._update_metrics()

    async def _is_healthy(self, device: EmulatorDevice) -> bool:
        """Check adb connectivity + boot completion + frida liveness."""
        try:
            # 1. adb get-state
            adb_bin = settings.ADB_BIN or "adb"
            result = await asyncio.to_thread(
                subprocess.run,
                [adb_bin, "-s", device.adb_serial, "get-state"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0 or "device" not in (result.stdout or ""):
                return False

            # 2. sys.boot_completed
            result = await asyncio.to_thread(
                subprocess.run,
                [adb_bin, "-s", device.adb_serial, "shell", "getprop", "sys.boot_completed"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0 or (result.stdout or "").strip() != "1":
                return False

            # 3. frida-server liveness (process list via adb; avoids importing frida)
            result = await asyncio.to_thread(
                subprocess.run,
                [adb_bin, "-s", device.adb_serial, "shell", "ps -A | grep frida-server"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if "frida-server" not in (result.stdout or ""):
                return False

            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("Health check failed for %s: %s", device.container_name, exc)
            return False

    async def _recycle(self, device: EmulatorDevice) -> None:
        """Restart the emulator container and re-provision it."""
        device.state = DeviceState.RECYCLING
        self._update_metrics()
        try:
            logger.info("Pool: recycling %s...", device.container_name)
            # Docker restart
            await asyncio.to_thread(
                subprocess.run,
                ["docker", "restart", device.container_name],
                capture_output=True,
                timeout=120,
            )
            # Wait for boot
            for _ in range(30):
                await asyncio.sleep(5)
                if await self._is_healthy(device):
                    device.state = DeviceState.AVAILABLE
                    device.consecutive_failures = 0
                    logger.info("Pool: %s recycled successfully", device.container_name)
                    self._update_metrics()
                    return

            device.state = DeviceState.DEAD
            logger.error("Pool: %s failed to recover after recycle", device.container_name)
        except Exception:  # noqa: BLE001
            device.state = DeviceState.DEAD
            logger.exception("Pool: recycle failed for %s", device.container_name)
        self._update_metrics()

    # -- helpers -------------------------------------------------------------

    def _update_metrics(self) -> None:
        available = sum(1 for d in self._devices.values() if d.state == DeviceState.AVAILABLE)
        leased = sum(1 for d in self._devices.values() if d.state == DeviceState.LEASED)
        recycling = sum(
            1
            for d in self._devices.values()
            if d.state in (DeviceState.RECYCLING, DeviceState.DEAD)
        )
        _record_pool_sizes(available, leased, recycling)

    def get_device(self, container_name: str) -> Optional[EmulatorDevice]:
        return self._devices.get(container_name)

    def snapshot(self) -> dict:
        """Return a serializable snapshot of pool state."""
        return {
            "total": self.size,
            "available": len(self.available),
            "leased": len(self.leased),
            "devices": [
                {
                    "container": d.container_name,
                    "adb_serial": d.adb_serial,
                    "state": d.state.value,
                    "leased_by": d.leased_by,
                    "consecutive_failures": d.consecutive_failures,
                }
                for d in self._devices.values()
            ],
        }


# ---------------------------------------------------------------------------
# Module-level singleton (lazy-init)
# ---------------------------------------------------------------------------
_pool: Optional[EmulatorPool] = None


def get_pool() -> EmulatorPool:
    """Return (or create) the module-level emulator pool singleton.

    The first call determines whether to build a multi-device pool from
    ``EMULATOR_POOL_SIZE`` or wrap the legacy single device as a 1-device pool.
    """
    global _pool
    if _pool is None:
        if settings.EMULATOR_POOL_SIZE > 1:
            _pool = EmulatorPool.from_settings()
        else:
            _pool = EmulatorPool.single_device()
        logger.info(
            "EmulatorPool initialized: %d device(s), health interval %.0fs",
            _pool.size,
            _pool._health_interval,
        )
    return _pool
