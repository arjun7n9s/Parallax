"""
One-time setup scripts for the Android emulator environment.

Handles installing the mitmproxy CA certificate and setting up frida-server.
"""

import hashlib
import logging
import lzma
import time
import urllib.request
from pathlib import Path

from cryptography import x509

from parallax.analysis.dynamic.avd_manager import AVDManager, AVDManagerError

logger = logging.getLogger(__name__)


def get_android_ca_hash(cert_pem: bytes) -> str:
    """Calculate the Android-compatible MD5-based subject name hash for a CA cert."""
    cert = x509.load_pem_x509_certificate(cert_pem)
    der_subject = cert.subject.public_bytes()
    md5_hash = hashlib.md5(der_subject, usedforsecurity=False).digest()
    hash_val = int.from_bytes(md5_hash[:4], byteorder="little")
    return f"{hash_val:08x}.0"


def install_mitmproxy_ca(avd_manager: AVDManager, ca_path: str | Path) -> str:
    """
    Install a mitmproxy CA certificate into Android's system trust store.

    Uses adb disable-verity + reboot + remount to make /system writable,
    then pushes the certificate into /system/etc/security/cacerts/.
    The cert persists across reboots.
    """
    ca_path = Path(ca_path)
    if not ca_path.exists():
        raise FileNotFoundError(f"CA certificate file not found: {ca_path}")

    # Calculate Android subject hash filename (e.g. c8750f0d.0)
    cert_bytes = ca_path.read_bytes()
    cert_filename = get_android_ca_hash(cert_bytes)
    logger.info(f"Calculated CA cert filename: {cert_filename}")

    # 1. Switch adbd to root
    avd_manager.root()

    # 2. Disable dm-verity so /system can be mounted writable
    logger.info("Disabling dm-verity...")
    try:
        output = avd_manager.shell("avbctl disable-verification", timeout=10)
        logger.debug(f"avbctl output: {output}")
    except Exception:
        # Fallback: older emulators use disable-verity via adb directly
        try:
            avd_manager._run_adb(["disable-verity"])
        except Exception as e:
            logger.warning(f"disable-verity failed (may already be disabled): {e}")

    # 3. Reboot to apply verity changes, then wait for boot
    logger.info("Rebooting emulator to apply verity changes...")
    try:
        avd_manager._run_adb(["reboot"], check=False)
    except Exception:
        pass  # reboot often kills the connection before returning

    time.sleep(5)  # Give the emulator a moment to begin rebooting
    avd_manager.wait_for_ready(timeout=180)

    # 4. Re-root after reboot
    avd_manager.root()

    # 5. Remount /system as writable
    logger.info("Remounting /system as writable...")
    remount_out = avd_manager._run_adb(["remount"])
    logger.debug(f"Remount output: {remount_out.stdout}")

    # 6. Push the CA certificate
    dest_path = f"/system/etc/security/cacerts/{cert_filename}"
    logger.info(f"Pushing CA cert to {dest_path}...")
    avd_manager.push_file(ca_path, dest_path)

    # 7. Set correct ownership and permissions
    avd_manager.shell(f"chown root:root {dest_path}")
    avd_manager.shell(f"chmod 644 {dest_path}")

    # 8. Restore SELinux context (best-effort)
    try:
        avd_manager.shell(f"restorecon {dest_path}")
    except Exception as e:
        logger.warning(f"restorecon failed (non-fatal): {e}")

    # 9. Verify the cert is readable on the device
    verify = avd_manager.shell(f"cat {dest_path} | head -1")
    if "BEGIN CERTIFICATE" not in verify and "BEGIN" not in verify:
        raise AVDManagerError(
            f"CA cert verification failed: {dest_path} does not contain a valid certificate"
        )

    logger.info(f"CA certificate {cert_filename} installed and verified at {dest_path}")
    return cert_filename


def get_default_frida_server_path(avd_manager: AVDManager) -> Path:
    """Download and cache the matching Frida-server binary based on the host version and device ABI."""
    abi = avd_manager.shell("getprop ro.product.cpu.abi").strip()
    if not abi:
        abi = "x86_64"  # Default fallback

    import frida
    from importlib import metadata as importlib_metadata

    # Prefer the package metadata (always present); fall back to module attribute
    # for older installs and stubbed imports (e.g. .venv-fast conftest mocks).
    try:
        version = importlib_metadata.version("frida")
    except (importlib_metadata.PackageNotFoundError, Exception):
        version = getattr(frida, "__version__", "17.11.0")

    cache_dir = Path(__file__).parent / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    binary_name = f"frida-server-{version}-android-{abi}"
    binary_path = cache_dir / binary_name

    if binary_path.exists():
        return binary_path

    # Download URL
    url = f"https://github.com/frida/frida/releases/download/{version}/frida-server-{version}-android-{abi}.xz"
    xz_path = cache_dir / f"{binary_name}.xz"

    logger.info(f"Downloading frida-server {version} for {abi} from {url}...")
    try:
        urllib.request.urlretrieve(url, xz_path)  # nosec B310
    except Exception as e:
        raise AVDManagerError(f"Failed to download frida-server from {url}: {e}") from e

    logger.info(f"Decompressing {xz_path}...")
    try:
        with lzma.open(xz_path, "rb") as f_in:
            with open(binary_path, "wb") as f_out:
                f_out.write(f_in.read())
        # Make executable locally
        binary_path.chmod(0o755)
    except Exception as e:
        if binary_path.exists():
            binary_path.unlink()
        raise AVDManagerError(f"Failed to decompress frida-server: {e}") from e
    finally:
        if xz_path.exists():
            xz_path.unlink()

    return binary_path


def install_frida_server(avd_manager: AVDManager, binary_path: str | Path) -> None:
    """Push frida-server binary to /data/local/tmp, chmod 755, start it and verify."""
    binary_path = Path(binary_path)
    if not binary_path.exists():
        raise FileNotFoundError(f"Frida server binary not found: {binary_path}")

    # Ensure ADB root
    avd_manager.root()

    remote_path = "/data/local/tmp/frida-server"
    logger.info(f"Pushing frida-server from {binary_path} to {remote_path}...")
    avd_manager.push_file(binary_path, remote_path)
    avd_manager.shell(f"chmod 755 {remote_path}")

    # Kill existing frida-server
    try:
        avd_manager.shell("pkill -f frida-server")
    except Exception:
        pass

    # Start frida-server in background
    logger.info("Starting frida-server in background...")
    # Bound to all interfaces (or 0.0.0.0:27042) to support socat forwarding inside container
    avd_manager.shell(f"nohup {remote_path} -l 0.0.0.0:27042 >/dev/null 2>&1 &")

    # Verify if it is running
    import time

    start_time = time.time()
    while time.time() - start_time < 15:
        if avd_manager.is_frida_running():
            logger.info("frida-server verified running successfully!")
            return
        time.sleep(1)

    raise AVDManagerError("frida-server failed to start and verify after 15s")
