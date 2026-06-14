"""Tests for the launch-resistant-malware fallback chain (sandbox/launcher.py).

Verified live against a real Cerberus sample: spawn + am-start fail (no
resolvable activity), enabling the accessibility service starts the process,
and frida attach then fires. These tests pin that behavior with a fake shell.
"""

from unittest.mock import MagicMock

import pytest

from parallax.sandbox import launcher
from parallax.sandbox.launcher import (
    LaunchError,
    LaunchStrategy,
    _norm,
    launch_for_instrumentation,
)

ACCESSIBILITY_DUMP = (
    "    96f51e7 com.x/.Acc filter f0 permission android.permission.BIND_ACCESSIBILITY_SERVICE"
)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(launcher.time, "sleep", lambda *_: None)


class FakeShell:
    """Canned adb shell. `starts_on` = substring that, once seen, makes the
    process 'appear' (pidof returns a pid thereafter)."""

    def __init__(self, dumpsys="", resolve="", starts_on=None, running=False):
        self.dumpsys_out = dumpsys
        self.resolve_out = resolve
        self.starts_on = starts_on
        self.running = running
        self.calls: list[str] = []

    def __call__(self, cmd: str) -> str:
        self.calls.append(cmd)
        if self.starts_on and self.starts_on in cmd:
            self.running = True
        if "dumpsys package" in cmd:
            return self.dumpsys_out
        if "resolve-activity" in cmd:
            return self.resolve_out
        if "pidof" in cmd:
            return "4321" if self.running else ""
        return ""


# ---------------------------------------------------------------- component norm
class TestNorm:
    @pytest.mark.parametrize(
        "comp,expected",
        [
            (".Foo", "com.x/com.x.Foo"),
            ("Foo", "com.x/com.x.Foo"),
            ("com.x/.Foo", "com.x/com.x.Foo"),
            ("a.b.C", "com.x/a.b.C"),
            ("com.x/a.b.C", "com.x/a.b.C"),
        ],
    )
    def test_norm(self, comp, expected):
        assert _norm("com.x", comp) == expected


# ---------------------------------------------------------------- strategy chain
class TestLaunchChain:
    def test_spawn_used_for_launcher_app(self):
        device = MagicMock()
        device.spawn.return_value = 111
        r = launch_for_instrumentation("com.x", shell=FakeShell(), frida_device=device)
        assert r.strategy is LaunchStrategy.SPAWN
        assert r.pid == 111
        assert r.spawned is True
        device.spawn.assert_called_once_with(["com.x"])

    def test_accessibility_wake_for_icon_hiding_malware(self):
        """No launcher, no resolvable activity → accessibility wake starts it."""
        device = MagicMock()
        device.spawn.side_effect = Exception("unable to find a front-door activity")
        shell = FakeShell(dumpsys=ACCESSIBILITY_DUMP, starts_on="enabled_accessibility_services")
        r = launch_for_instrumentation("com.x", shell=shell, frida_device=device)
        assert r.strategy is LaunchStrategy.ACCESSIBILITY_WAKE
        assert r.spawned is False  # attach, do NOT resume
        assert r.pid == 4321
        assert any("enabled_accessibility_services com.x/com.x.Acc" in c for c in shell.calls)
        assert any("accessibility_enabled 1" in c for c in shell.calls)

    def test_am_start_precedes_accessibility(self):
        """If a launcher activity resolves, am_start wins before accessibility."""
        device = MagicMock()
        device.spawn.side_effect = Exception("unable to find a front-door activity")
        shell = FakeShell(
            dumpsys=ACCESSIBILITY_DUMP,
            resolve="  com.x/com.x.Main",
            starts_on="am start",
        )
        r = launch_for_instrumentation("com.x", shell=shell, frida_device=device)
        assert r.strategy is LaunchStrategy.AM_START
        assert r.spawned is False
        assert any("am start -n com.x/com.x.Main" in c for c in shell.calls)
        # accessibility must NOT have been attempted (am_start already succeeded)
        assert not any("enabled_accessibility_services" in c for c in shell.calls)

    def test_all_strategies_fail_raises_clear_error(self):
        device = MagicMock()
        device.spawn.side_effect = Exception("no launcher")
        shell = FakeShell(dumpsys="", resolve="", starts_on=None)  # nothing ever starts
        with pytest.raises(LaunchError) as exc:
            launch_for_instrumentation("com.x", shell=shell, frida_device=device)
        assert "Could not launch com.x" in str(exc.value)

    def test_tolerates_shell_that_raises_on_pidof(self):
        """adb `pidof` exits non-zero (raises) when the process isn't running
        yet; the poll must treat that as 'not yet', not crash the chain."""

        class RaisingShell(FakeShell):
            def __call__(self, cmd: str) -> str:
                if "enabled_accessibility_services" in cmd:
                    self.running = True
                if "pidof" in cmd and not self.running:
                    raise RuntimeError("ADB command failed: pidof exit 1")
                return super().__call__(cmd)

        device = MagicMock()
        device.spawn.side_effect = Exception("unable to find a front-door activity")
        shell = RaisingShell(dumpsys=ACCESSIBILITY_DUMP)
        r = launch_for_instrumentation("com.x", shell=shell, frida_device=device)
        assert r.strategy is LaunchStrategy.ACCESSIBILITY_WAKE
        assert r.pid == 4321

    def test_no_shell_and_spawn_fails_raises(self):
        device = MagicMock()
        device.spawn.side_effect = Exception("no launcher")
        with pytest.raises(LaunchError) as exc:
            launch_for_instrumentation("com.x", shell=None, frida_device=device)
        assert "no adb shell" in str(exc.value)
