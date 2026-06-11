"""
Integration tests for AVDManager.

Validates that AVDManager can successfully connect to the running
android-emulator container, query its status, push files, and execute shell commands.
"""

import tempfile
from pathlib import Path

import pytest

from parallax.analysis.dynamic.avd_manager import AVDManager


@pytest.fixture(scope="module")
def avd_manager():
    """Returns an AVDManager instance configured for 127.0.0.1:5555."""
    manager = AVDManager(adb_host="127.0.0.1", adb_port=5555)
    manager.wait_for_ready(timeout=180)
    return manager


def test_avd_is_running(avd_manager):
    """Verify the running emulator is correctly detected as active."""
    assert avd_manager.is_running() is True


def test_avd_boot_idempotent(avd_manager):
    """Verify boot returns True immediately when AVD is already running."""
    assert avd_manager.boot() is True


def test_avd_shell_execution(avd_manager):
    """Verify shell command execution and stdout retrieval."""
    output = avd_manager.shell("getprop sys.boot_completed")
    assert output.strip() == "1"


def test_avd_push_and_shell(avd_manager):
    """Verify pushing files and executing commands on them in the emulator."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write(b"Hello from Parallax AVDManager Integration Test!")
        tmp_path = Path(tmp.name)

    remote_path = "/data/local/tmp/test_avd_manager.txt"
    try:
        # Push the temp file
        avd_manager.push_file(tmp_path, remote_path)

        # Check content using cat via shell
        content = avd_manager.shell(f"cat {remote_path}")
        assert content.strip() == "Hello from Parallax AVDManager Integration Test!"
    finally:
        # Clean up both locally and remotely
        if tmp_path.exists():
            tmp_path.unlink()
        avd_manager.shell(f"rm -f {remote_path}")
