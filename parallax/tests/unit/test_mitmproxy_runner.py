"""Regression tests for the embedded mitmproxy runner.

mitmproxy 11 exposes DumpMaster.run as a coroutine. The old implementation
passed that coroutine function directly to Thread(target=...), so the coroutine
was never awaited and no flows could be captured.
"""

from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

import pytest

from parallax.analysis.dynamic import mitmproxy_runner
from parallax.analysis.dynamic.mitmproxy_runner import MitmproxyRunner


class FakeOptions:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeDumpMaster:
    instances: list["FakeDumpMaster"] = []

    def __init__(self, opts, with_termlog=False, with_dumper=False):
        self.opts = opts
        self.with_termlog = with_termlog
        self.with_dumper = with_dumper
        self.added = []
        self.addons = SimpleNamespace(add=self.added.append)
        self.shutdown_called = False
        self.run_started = threading.Event()

        FakeDumpMaster.instances.append(self)

    async def run(self) -> None:
        self.run_started.set()
        while not self.shutdown_called:
            await asyncio.sleep(0.01)

    def shutdown(self) -> None:
        self.shutdown_called = True


@pytest.mark.asyncio
async def test_dumpmaster_run_is_awaited_inside_runner_thread(monkeypatch):
    monkeypatch.setattr(mitmproxy_runner, "Options", FakeOptions)
    monkeypatch.setattr(mitmproxy_runner, "DumpMaster", FakeDumpMaster)

    runner = MitmproxyRunner("sub-1", 8081, lambda _flow: None)
    await runner.start()
    master = FakeDumpMaster.instances[-1]

    assert master.run_started.wait(timeout=1.0)
    assert runner.runner_thread is not None
    assert runner.runner_thread.is_alive()

    await runner.stop()

    assert master.shutdown_called is True
    assert runner.runner_thread is None
    assert runner.runner_error is None


@pytest.mark.asyncio
async def test_runner_error_surfaces_thread_failure(monkeypatch):
    class FailingDumpMaster(FakeDumpMaster):
        async def run(self) -> None:
            self.run_started.set()
            raise RuntimeError("proxy exploded")

    monkeypatch.setattr(mitmproxy_runner, "Options", FakeOptions)
    monkeypatch.setattr(mitmproxy_runner, "DumpMaster", FailingDumpMaster)

    runner = MitmproxyRunner("sub-1", 8081, lambda _flow: None)
    await runner.start()
    master = FailingDumpMaster.instances[-1]

    assert master.run_started.wait(timeout=1.0)
    runner.runner_thread.join(timeout=1.0)

    assert runner.runner_error == "RuntimeError: proxy exploded"
