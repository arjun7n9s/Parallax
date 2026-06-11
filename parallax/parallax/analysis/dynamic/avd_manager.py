"""
AVD Lifecycle Manager.

Wraps adb command executions for managing emulator boot, application
installation, file system transfer, shell execution, and port forwarding.
"""

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class AVDManagerError(Exception):
    """Raised when an AVD management operation fails."""

    pass


def _find_adb() -> str:
    """Helper to locate the adb executable across different systems and environments."""
    # 1. Check if adb is in the system PATH
    if shutil.which("adb"):
        return "adb"

    # 2. Check standard environment variables
    for env_var in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        val = os.getenv(env_var)
        if val:
            p = Path(val) / "platform-tools" / "adb"
            if os.name == "nt":
                p = p.with_suffix(".exe")
            if p.exists():
                return str(p)

    # 3. Check Windows default user SDK location
    if os.name == "nt":
        user_profile = os.getenv("USERPROFILE")
        if user_profile:
            p = Path(user_profile) / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe"
            if p.exists():
                return str(p)

    # Fallback to default command
    return "adb"


class AVDManager:
    """Manager for emulator lifecycle and ADB interactions."""

    def __init__(self, adb_host: str = "localhost", adb_port: int = 5555, device_id: str | None = None):
        self.adb_host = adb_host
        self.adb_port = adb_port
        self.adb_bin = _find_adb()
        # If no device_id is provided, default to host:port format
        self.device_id = device_id or f"{self.adb_host}:{self.adb_port}"
        self._connect()

    def _run_adb(self, args: list[str], timeout: int | None = None, check: bool = True) -> subprocess.CompletedProcess:
        """Helper to run adb command targeting the specific device."""
        cmd = [self.adb_bin, "-s", self.device_id] + args
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=check)
        except subprocess.CalledProcessError as e:
            raise AVDManagerError(
                f"ADB command failed: {' '.join(cmd)}\n"
                f"exit code: {e.returncode}\n"
                f"stdout: {e.stdout}\n"
                f"stderr: {e.stderr}"
            ) from e
        except subprocess.TimeoutExpired as e:
            raise AVDManagerError(f"ADB command timed out: {' '.join(cmd)}") from e

    def _connect(self) -> None:
        """Connect to the remote ADB daemon if not already connected."""
        # Only run connect if it's an IP:port target
        if ":" in self.device_id or self.adb_host not in ("localhost", "127.0.0.1"):
            target = f"{self.adb_host}:{self.adb_port}"
            try:
                subprocess.run([self.adb_bin, "connect", target], capture_output=True, text=True, check=False)
            except Exception as e:
                logger.warning(f"Failed to run adb connect {target}: {e}")

    def is_running(self) -> bool:
        """Check if the emulator device is connected and responsive."""
        try:
            # Reconnect just in case
            self._connect()
            # Run getprop sys.boot_completed
            res = self._run_adb(["shell", "getprop", "sys.boot_completed"], timeout=10, check=False)
            if res.returncode == 0 and res.stdout.strip() == "1":
                return True
            return False
        except Exception:
            return False

    def is_frida_running(self) -> bool:
        """Check if frida-server is running on the emulator."""
        try:
            output = self.shell("ps -A")
            return "frida-server" in output
        except Exception:
            return False

    def boot(self, timeout: int = 300, frida_server_path: str | Path | None = None) -> bool:
        """Ensure the emulator is booted and ready (idempotent) and frida-server is running."""
        if self.is_running():
            logger.info("Emulator is already running.")
            if not self.is_frida_running():
                logger.info("Frida-server is not running. Launching setup...")
                from parallax.analysis.dynamic.install import get_default_frida_server_path, install_frida_server
                if not frida_server_path:
                    frida_server_path = get_default_frida_server_path(self)
                install_frida_server(self, frida_server_path)
            return True
        logger.info("Waiting for emulator to be ready...")
        ready = self.wait_for_ready(timeout)
        if ready:
            if not self.is_frida_running():
                logger.info("Frida-server is not running. Launching setup...")
                from parallax.analysis.dynamic.install import get_default_frida_server_path, install_frida_server
                if not frida_server_path:
                    frida_server_path = get_default_frida_server_path(self)
                install_frida_server(self, frida_server_path)
        return ready

    def wait_for_ready(self, timeout: int = 300) -> bool:
        """Poll sys.boot_completed until the device is ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_running():
                return True
            time.sleep(5)
        raise AVDManagerError(f"Timeout waiting for emulator {self.device_id} to boot after {timeout}s")

    def install_apk(self, apk_path: str | Path) -> None:
        """Install an APK on the emulator."""
        apk_path = Path(apk_path)
        if not apk_path.exists():
            raise FileNotFoundError(f"APK file not found: {apk_path}")
        logger.info(f"Installing APK: {apk_path}")
        self._run_adb(["install", "-r", str(apk_path)])

    def push_file(self, local: str | Path, remote: str) -> None:
        """Push a file to the emulator filesystem."""
        local = Path(local)
        if not local.exists():
            raise FileNotFoundError(f"Local file not found: {local}")
        self._run_adb(["push", str(local), remote])

    def shell(self, command: str, timeout: int = 30) -> str:
        """Execute a shell command inside the emulator and return stdout."""
        res = self._run_adb(["shell", command], timeout=timeout)
        return res.stdout

    def forward(self, local_port: int, remote_port: int) -> None:
        """Set up port forwarding."""
        self._run_adb(["forward", f"tcp:{local_port}", f"tcp:{remote_port}"])

    def uninstall(self, package: str) -> None:
        """Uninstall a package from the emulator."""
        self._run_adb(["uninstall", package], check=False)
