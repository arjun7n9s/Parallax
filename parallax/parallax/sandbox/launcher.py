"""Launch strategies for instrumenting launch-resistant (icon-hiding) malware.

Banking trojans routinely ship without a LAUNCHER activity (hidden icon) and
expose their malicious surface as an AccessibilityService / NotificationListener
that the system binds only when the capability is "enabled". frida's
spawn-by-launch then fails with ``unable to find a front-door activity``.

This module gets the process running by another means and returns its pid so the
caller can **attach** (attach needs no launcher) instead of spawn.

Verified on a real Cerberus sample: ``spawn`` and ``am start`` both fail (no
resolvable activity); enabling the accessibility service via secure settings
starts the process, and frida ``attach`` + ``Java.perform`` then fire.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

Shell = Callable[[str], str]


class LaunchStrategy(str, Enum):
    SPAWN = "spawn"  # frida controls a suspended process (early instrumentation)
    AM_START = "am_start"  # started a declared/launcher activity
    ACCESSIBILITY_WAKE = "accessibility_wake"  # enabled an AccessibilityService
    NOTIFICATION_WAKE = "notification_wake"  # bound a NotificationListenerService
    MONKEY = "monkey"  # last-resort launcher intent


class LaunchError(Exception):
    pass


@dataclass
class LaunchResult:
    strategy: LaunchStrategy
    pid: int
    # True ONLY for SPAWN: the process is suspended and the caller MUST
    # device.resume(pid) after loading the script. Every attach path leaves the
    # process already running, so the caller attaches and does NOT resume.
    spawned: bool
    detail: str = ""


@dataclass
class _Components:
    activities: list[str] = field(default_factory=list)
    accessibility_services: list[str] = field(default_factory=list)
    notification_listeners: list[str] = field(default_factory=list)


def _norm(package: str, comp: str) -> str:
    """Return a fully-qualified ``package/fully.qualified.Class`` string."""
    comp = comp.strip()
    pkg, cls = comp.split("/", 1) if "/" in comp else (package, comp)
    if cls.startswith("."):
        cls = pkg + cls
    elif "." not in cls:
        cls = f"{pkg}.{cls}"
    return f"{pkg}/{cls}"


def _pid_of(package: str, shell: Shell) -> int | None:
    # `pidof` exits non-zero when the process isn't running, which adb shell
    # wrappers surface as a raised error — that just means "no pid yet", not a
    # real failure, so swallow it and let the caller keep polling.
    try:
        out = (shell(f"pidof {package}") or "").strip()
    except Exception:  # noqa: BLE001
        return None
    if not out:
        return None
    try:
        return int(out.split()[0])  # pidof may return several; take the first
    except ValueError:
        return None


def _wait_for_pid(package: str, shell: Shell, timeout: int) -> int | None:
    for _ in range(max(1, timeout)):
        pid = _pid_of(package, shell)
        if pid:
            return pid
        time.sleep(1)
    return None


def _introspect(package: str, shell: Shell) -> _Components:
    """Find launch handles for the package from the live package manager."""
    comps = _Components()
    try:
        dump = shell(f"dumpsys package {package}") or ""
    except Exception as exc:  # noqa: BLE001 — introspection is best-effort
        logger.warning("dumpsys failed for %s: %s", package, exc)
        dump = ""

    for line in dump.splitlines():
        if "BIND_ACCESSIBILITY_SERVICE" in line:
            m = re.search(rf"{re.escape(package)}/\S+", line)
            if m:
                comps.accessibility_services.append(m.group(0))
        elif "BIND_NOTIFICATION_LISTENER_SERVICE" in line:
            m = re.search(rf"{re.escape(package)}/\S+", line)
            if m:
                comps.notification_listeners.append(m.group(0))

    # Launcher activity, if any (clean and version-robust).
    try:
        ra = shell(f"cmd package resolve-activity --brief {package}") or ""
        m = re.search(rf"{re.escape(package)}/\S+", ra)
        if m:
            comps.activities.append(m.group(0))
    except Exception:  # noqa: BLE001
        pass

    return comps


def launch_for_instrumentation(
    package: str,
    shell: Shell,
    frida_device=None,
    timeout: int = 30,
) -> LaunchResult:
    """Get ``package`` running so frida can instrument it.

    Strategy order (first that yields a pid wins):
      1. frida ``spawn`` — early instrumentation; needs a launcher activity.
      2. ``am start`` on the resolved launcher/declared activity.
      3. **accessibility wake** — enable an AccessibilityService via secure
         settings (the reliable path for icon-hiding trojans like Cerberus).
      4. **notification wake** — bind a NotificationListenerService.
      5. ``monkey`` launcher intent (last resort).

    Returns a :class:`LaunchResult`; ``spawned`` tells the caller whether to
    resume (spawn) or just attach. Raises :class:`LaunchError` if nothing starts
    the process (loud failure, never a silent hang).
    """
    # 1. SPAWN
    if frida_device is not None:
        try:
            pid = frida_device.spawn([package])
            logger.info("Launched %s via spawn (pid %s)", package, pid)
            return LaunchResult(LaunchStrategy.SPAWN, pid, spawned=True, detail="launcher")
        except Exception as exc:  # noqa: BLE001 — fall through to non-launcher paths
            logger.info("spawn() failed for %s (%s); using launch fallback chain", package, exc)

    # Every fallback below needs adb. Without a shell, spawn was the only option.
    if shell is None:
        raise LaunchError(
            f"Could not spawn {package} and no adb shell available for the launch "
            f"fallback chain (icon-hiding malware needs am-start/accessibility-wake)."
        )

    comps = _introspect(package, shell)

    def _root(cmd: str) -> str:
        # secure-settings / am / cmd need root on the (rooted) analysis emulator.
        return shell(f"su 0 {cmd}")

    # 2. AM_START
    for act in comps.activities:
        try:
            _root(f"am start -n {_norm(package, act)}")
        except Exception as exc:  # noqa: BLE001
            logger.debug("am start %s failed: %s", act, exc)
            continue
        if pid := _wait_for_pid(package, shell, 5):
            logger.info("Launched %s via am start %s (pid %s)", package, act, pid)
            return LaunchResult(LaunchStrategy.AM_START, pid, spawned=False, detail=act)

    # 3. ACCESSIBILITY_WAKE — the verified path for icon-hiding trojans.
    for acc in comps.accessibility_services:
        fq = _norm(package, acc)
        try:
            _root(f"settings put secure enabled_accessibility_services {fq}")
            _root("settings put secure accessibility_enabled 1")
        except Exception as exc:  # noqa: BLE001
            logger.debug("accessibility enable %s failed: %s", acc, exc)
            continue
        if pid := _wait_for_pid(package, shell, 10):
            logger.info("Launched %s via accessibility wake %s (pid %s)", package, acc, pid)
            return LaunchResult(LaunchStrategy.ACCESSIBILITY_WAKE, pid, spawned=False, detail=acc)

    # 4. NOTIFICATION_WAKE
    for nl in comps.notification_listeners:
        try:
            _root(f"cmd notification allow_listener {_norm(package, nl)}")
        except Exception as exc:  # noqa: BLE001
            logger.debug("notification allow_listener %s failed: %s", nl, exc)
            continue
        if pid := _wait_for_pid(package, shell, 5):
            logger.info("Launched %s via notification wake %s (pid %s)", package, nl, pid)
            return LaunchResult(LaunchStrategy.NOTIFICATION_WAKE, pid, spawned=False, detail=nl)

    # 5. MONKEY
    try:
        _root(f"monkey -p {package} -c android.intent.category.LAUNCHER 1")
    except Exception:  # noqa: BLE001
        pass
    if pid := _wait_for_pid(package, shell, 5):
        logger.info("Launched %s via monkey (pid %s)", package, pid)
        return LaunchResult(LaunchStrategy.MONKEY, pid, spawned=False, detail="monkey")

    raise LaunchError(
        f"Could not launch {package} via any strategy "
        f"(activities={len(comps.activities)}, "
        f"accessibility={len(comps.accessibility_services)}, "
        f"notification={len(comps.notification_listeners)})"
    )
