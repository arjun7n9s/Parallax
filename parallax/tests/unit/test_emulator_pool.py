"""Tests for the EmulatorPool (Task 1.2).

Covers: acquire/release lifecycle, exclusive leasing, timeout on exhaustion,
health-check state transitions, recycle on failure, metrics, snapshot, and
the single-device legacy wrapper.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from parallax.core.errors import InfraError
from parallax.sandbox.pool import (
    DeviceState,
    EmulatorDevice,
    EmulatorPool,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_devices(n: int = 3) -> list[EmulatorDevice]:
    return [
        EmulatorDevice(
            container_name=f"emu_{i}",
            adb_serial=f"localhost:{5555 + i}",
            adb_port=5555 + i,
            frida_port=27042 + i,
        )
        for i in range(n)
    ]


def _pool(n: int = 3, health_interval: float = 9999) -> EmulatorPool:
    """Build a pool with *n* devices and no background health loop."""
    return EmulatorPool(_make_devices(n), health_interval=health_interval)


# ---------------------------------------------------------------------------
# Acquire / release
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acquire_returns_available_device():
    pool = _pool(2)
    dev = await pool.acquire("sub-1")
    assert dev.state == DeviceState.LEASED
    assert dev.leased_by == "sub-1"
    assert len(pool.available) == 1


@pytest.mark.asyncio
async def test_release_returns_device_to_pool():
    pool = _pool(1)
    dev = await pool.acquire("sub-1")
    assert len(pool.available) == 0
    await pool.release(dev)
    assert dev.state == DeviceState.AVAILABLE
    assert dev.leased_by is None
    assert len(pool.available) == 1


@pytest.mark.asyncio
async def test_release_unknown_device_is_harmless():
    pool = _pool(1)
    unknown = EmulatorDevice(
        container_name="ghost", adb_serial="localhost:9999"
    )
    await pool.release(unknown)  # should not raise


# ---------------------------------------------------------------------------
# Exclusive leasing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exclusive_lease_prevents_double_acquire():
    """With 1 device, a second acquire must wait (and timeout)."""
    pool = _pool(1)
    dev = await pool.acquire("sub-1")

    with pytest.raises(InfraError, match="no device available"):
        await pool.acquire("sub-2", timeout=0.1)

    # After release, acquire should succeed
    await pool.release(dev)
    dev2 = await pool.acquire("sub-2")
    assert dev2.container_name == dev.container_name


@pytest.mark.asyncio
async def test_acquire_waits_and_succeeds_after_release():
    """A second acquire should succeed once the first device is released."""
    pool = _pool(1)
    dev = await pool.acquire("sub-1")

    async def release_later():
        await asyncio.sleep(0.1)
        await pool.release(dev)

    asyncio.create_task(release_later())
    dev2 = await pool.acquire("sub-2", timeout=2.0)
    assert dev2.leased_by == "sub-2"


# ---------------------------------------------------------------------------
# Pool exhaustion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acquire_raises_infra_error_on_timeout():
    pool = _pool(1)
    await pool.acquire("sub-1")

    with pytest.raises(InfraError, match="no device available"):
        await pool.acquire("sub-2", timeout=0.05)


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_marks_dead_after_consecutive_failures():
    pool = _pool(1)
    dev = pool.get_device("emu_0")
    assert dev is not None

    with patch.object(pool, "_is_healthy", new_callable=AsyncMock, return_value=False):
        # Run health checks enough times to exceed MAX_CONSECUTIVE_FAILURES
        with patch.object(pool, "_recycle", new_callable=AsyncMock):
            for _ in range(EmulatorPool.MAX_CONSECUTIVE_FAILURES):
                await pool.check_all_health()

    assert dev.state == DeviceState.DEAD


@pytest.mark.asyncio
async def test_health_check_recovers_device():
    pool = _pool(1)
    dev = pool.get_device("emu_0")
    assert dev is not None
    dev.state = DeviceState.RECYCLING
    dev.consecutive_failures = 2

    with patch.object(pool, "_is_healthy", new_callable=AsyncMock, return_value=True):
        await pool.check_all_health()

    assert dev.state == DeviceState.AVAILABLE
    assert dev.consecutive_failures == 0


@pytest.mark.asyncio
async def test_health_check_skips_leased_devices():
    pool = _pool(1)
    dev = await pool.acquire("sub-1")
    assert dev.state == DeviceState.LEASED

    mock_healthy = AsyncMock(return_value=False)
    with patch.object(pool, "_is_healthy", mock_healthy):
        await pool.check_all_health()

    # Leased device should NOT be checked
    mock_healthy.assert_not_called()
    assert dev.state == DeviceState.LEASED  # unchanged


# ---------------------------------------------------------------------------
# Recycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recycle_restores_device_on_success():
    pool = _pool(1)
    dev = pool.get_device("emu_0")
    assert dev is not None
    dev.state = DeviceState.DEAD
    dev.consecutive_failures = 5

    # Mock docker restart succeeding + health returning true
    with patch("parallax.sandbox.pool.subprocess") as mock_subprocess:
        mock_subprocess.run.return_value = None
        with patch.object(pool, "_is_healthy", new_callable=AsyncMock, return_value=True):
            await pool._recycle(dev)

    assert dev.state == DeviceState.AVAILABLE
    assert dev.consecutive_failures == 0


@pytest.mark.asyncio
async def test_recycle_marks_dead_on_failure():
    pool = _pool(1)
    dev = pool.get_device("emu_0")
    assert dev is not None

    # Mock docker restart succeeding but health never returning true
    with patch("parallax.sandbox.pool.subprocess") as mock_subprocess:
        mock_subprocess.run.return_value = None
        with patch.object(pool, "_is_healthy", new_callable=AsyncMock, return_value=False):
            # Speed up the test — patch sleep
            with patch("parallax.sandbox.pool.asyncio.sleep", new_callable=AsyncMock):
                await pool._recycle(dev)

    assert dev.state == DeviceState.DEAD


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_reflects_pool_state():
    pool = _pool(2)
    snap = pool.snapshot()
    assert snap["total"] == 2
    assert snap["available"] == 2
    assert snap["leased"] == 0
    assert len(snap["devices"]) == 2
    assert snap["devices"][0]["state"] == "available"


# ---------------------------------------------------------------------------
# from_settings / single_device
# ---------------------------------------------------------------------------


def test_single_device_pool():
    pool = EmulatorPool.single_device()
    assert pool.size == 1
    dev = list(pool._devices.values())[0]
    assert dev.container_name == "parallax_android_emulator"


def test_from_settings_creates_correct_fleet():
    with patch("parallax.sandbox.pool.settings") as mock_settings:
        mock_settings.EMULATOR_POOL_SIZE = 3
        mock_settings.EMULATOR_BASE_ADB_PORT = 5555
        mock_settings.EMULATOR_BASE_FRIDA_PORT = 27042
        mock_settings.EMULATOR_HEALTH_INTERVAL = 30.0
        pool = EmulatorPool.from_settings()

    assert pool.size == 3
    serials = [d.adb_serial for d in pool._devices.values()]
    assert "localhost:5555" in serials
    assert "localhost:5556" in serials
    assert "localhost:5557" in serials


# ---------------------------------------------------------------------------
# Health loop start/stop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_loop_starts_and_stops():
    pool = _pool(1, health_interval=0.05)
    await pool.start_health_loop()
    assert pool._health_task is not None

    await asyncio.sleep(0.02)
    await pool.stop_health_loop()
    assert pool._health_task is None


@pytest.mark.asyncio
async def test_start_health_loop_is_idempotent():
    pool = _pool(1, health_interval=9999)
    await pool.start_health_loop()
    task1 = pool._health_task
    await pool.start_health_loop()
    assert pool._health_task is task1
    await pool.stop_health_loop()


# ---------------------------------------------------------------------------
# Concurrent acquire ordering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_acquires_are_exclusive():
    """3 concurrent acquires on a 3-device pool → each gets a distinct device."""
    pool = _pool(3)

    async def grab(sid: str):
        return await pool.acquire(sid)

    devs = await asyncio.gather(grab("a"), grab("b"), grab("c"))
    names = {d.container_name for d in devs}
    assert len(names) == 3  # all distinct
    assert len(pool.available) == 0
    assert len(pool.leased) == 3


# ---------------------------------------------------------------------------
# Device property
# ---------------------------------------------------------------------------


def test_device_id_property():
    dev = EmulatorDevice(
        container_name="test", adb_serial="localhost:5555"
    )
    assert dev.device_id == "localhost:5555"
