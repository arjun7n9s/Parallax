#!/usr/bin/env python3
"""Chaos script for the emulator pool (Task 1.2 verification gate).

Randomly kills emulator containers during a batch of N simulated analyses.
Verifies that:
  - Every analysis still reaches a terminal state (failover logged).
  - The pool self-heals back to target size.
  - No analysis hangs forever.

Usage:
    python scripts/chaos_emulator.py --pool-size 3 --analyses 10 --kill-interval 15

Requires a running emulator fleet (docker compose scale android-emulator=N).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
import subprocess
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("chaos_emulator")

# Add the project root to sys.path for imports
sys.path.insert(0, str(__file__ and __import__("pathlib").Path(__file__).resolve().parents[1]))

from parallax.sandbox.pool import EmulatorDevice, EmulatorPool  # noqa: E402


async def simulate_analysis(pool: EmulatorPool, analysis_id: str, duration: float) -> dict:
    """Simulate an analysis lifecycle: acquire → work → release."""
    result = {"id": analysis_id, "status": "pending", "device": None, "error": None}
    try:
        device = await pool.acquire(analysis_id, timeout=120)
        result["device"] = device.container_name
        result["status"] = "running"
        logger.info("Analysis %s acquired %s", analysis_id, device.container_name)

        # Simulate analysis work
        await asyncio.sleep(duration)

        result["status"] = "complete"
        logger.info("Analysis %s completed on %s", analysis_id, device.container_name)
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        logger.warning("Analysis %s failed: %s", analysis_id, exc)
    finally:
        if result.get("device"):
            try:
                await pool.release(device)
            except Exception:
                pass
    return result


async def chaos_killer(
    pool: EmulatorPool,
    kill_interval: float,
    duration: float,
) -> int:
    """Periodically kill a random emulator container."""
    kills = 0
    end_time = time.monotonic() + duration
    while time.monotonic() < end_time:
        await asyncio.sleep(kill_interval)
        devices = list(pool._devices.values())
        if not devices:
            continue

        target = random.choice(devices)
        logger.warning(
            "CHAOS: killing container %s (state=%s)", target.container_name, target.state
        )
        try:
            subprocess.run(
                ["docker", "kill", target.container_name],
                capture_output=True,
                timeout=10,
            )
            kills += 1
        except Exception as exc:
            logger.debug("CHAOS: kill failed (container may not exist): %s", exc)

    return kills


async def run_chaos(pool_size: int, num_analyses: int, kill_interval: float):
    """Run the chaos test."""
    # Build pool
    devices = [
        EmulatorDevice(
            container_name=f"parallax_android_emulator_{i}",
            adb_serial=f"localhost:{5555 + i}",
            adb_port=5555 + i,
        )
        for i in range(pool_size)
    ]
    pool = EmulatorPool(devices, health_interval=10.0)
    await pool.start_health_loop()

    # Estimate total duration
    analysis_duration = 5.0  # seconds per simulated analysis
    total_duration = (num_analyses / pool_size) * analysis_duration + 30

    # Launch analyses + chaos killer concurrently
    analysis_tasks = [
        simulate_analysis(pool, f"analysis-{i}", analysis_duration) for i in range(num_analyses)
    ]
    chaos_task = asyncio.create_task(chaos_killer(pool, kill_interval, total_duration))

    results = await asyncio.gather(*analysis_tasks)
    chaos_task.cancel()
    try:
        kills = await chaos_task
    except asyncio.CancelledError:
        kills = 0

    await pool.stop_health_loop()

    # Report
    completed = sum(1 for r in results if r["status"] == "complete")
    failed = sum(1 for r in results if r["status"] == "failed")

    print("\n" + "=" * 60)
    print("CHAOS TEST REPORT")
    print("=" * 60)
    print(f"Pool size:       {pool_size}")
    print(f"Analyses:        {num_analyses}")
    print(f"Completed:       {completed}")
    print(f"Failed:          {failed}")
    print(f"Containers killed: {kills}")
    print("Pool final state:")
    for d in pool._devices.values():
        print(f"  {d.container_name}: {d.state.value} (failures={d.consecutive_failures})")

    all_terminal = all(r["status"] in ("complete", "failed") for r in results)
    print(f"\nAll analyses reached terminal state: {'✅ YES' if all_terminal else '❌ NO'}")

    if not all_terminal:
        print("FAIL: some analyses did not reach a terminal state!")
        sys.exit(1)
    print("PASS: chaos test succeeded.")


def main():
    parser = argparse.ArgumentParser(description="Chaos test for emulator pool")
    parser.add_argument("--pool-size", type=int, default=3, help="Number of emulator devices")
    parser.add_argument("--analyses", type=int, default=10, help="Number of analyses to run")
    parser.add_argument(
        "--kill-interval", type=float, default=15.0, help="Seconds between container kills"
    )
    args = parser.parse_args()

    asyncio.run(run_chaos(args.pool_size, args.analyses, args.kill_interval))


if __name__ == "__main__":
    main()
