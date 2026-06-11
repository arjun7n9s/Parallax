"""
One-time setup scripts for the Android emulator environment.

Handles installing the mitmproxy CA certificate and setting up frida-server.
"""

import hashlib
import logging
import lzma
import os
import urllib.request
from pathlib import Path
from cryptography import x509
from parallax.analysis.dynamic.avd_manager import AVDManager, AVDManagerError

logger = logging.getLogger(__name__)


def get_android_ca_hash(cert_pem: bytes) -> str:
    """Calculate the Android-compatible MD5-based subject name hash for a CA cert."""
    cert = x509.load_pem_x509_certificate(cert_pem)
    der_subject = cert.subject.public_bytes()
    md5_hash = hashlib.md5(der_subject).digest()
    hash_val = int.from_bytes(md5_hash[:4], byteorder="little")
    return f"{hash_val:08x}.0"


def install_mitmproxy_ca(avd_manager: AVDManager, ca_path: str | Path) -> str:
    """
    Install a mitmproxy CA certificate into Android's system trust store.
    Attempts system remount, and falls back to a tmpfs overlay workaround if read-only.
    """
    ca_path = Path(ca_path)
    if not ca_path.exists():
        raise FileNotFoundError(f"CA certificate file not found: {ca_path}")

    # Calculate Android subject hash
    cert_bytes = ca_path.read_bytes()
    cert_filename = get_android_ca_hash(cert_bytes)
    logger.info(f"Calculated CA cert filename: {cert_filename}")

    # Ensure ADB is root
    avd_manager._run_adb(["root"])

    # Push file to temporary location
    temp_device_path = f"/data/local/tmp/{cert_filename}"
    avd_manager.push_file(ca_path, temp_device_path)

    dest_path = f"/system/etc/security/cacerts/{cert_filename}"
    installed = False

    # Attempt 1: Standard mount remount and write
    try:
        # Try remounting root or system
        for mount_cmd in ["mount -o rw,remount /system", "mount -o rw,remount /"]:
            try:
                avd_manager.shell(mount_cmd)
            except Exception:
                pass

        # Try to copy and set permissions
        avd_manager.shell(f"cp {temp_device_path} {dest_path}")
        avd_manager.shell(f"chmod 644 {dest_path}")
        avd_manager.shell(f"chown root:root {dest_path}")

        # Check if file exists and has size > 0
        ls_out = avd_manager.shell(f"ls -la {dest_path}")
        if cert_filename in ls_out:
            logger.info("Successfully installed CA certificate via standard write.")
            installed = True
    except Exception as e:
        logger.warning(f"Standard CA install failed: {e}. Falling back to tmpfs workaround.")

    # Attempt 2: Tmpfs overlay fallback
    if not installed:
        try:
            mounts = avd_manager.shell("mount")
            if "tmpfs on /system/etc/security/cacerts" not in mounts:
                logger.info("Setting up tmpfs overlay on /system/etc/security/cacerts")
                avd_manager.shell("mkdir -p /data/local/tmp/cacerts")
                avd_manager.shell("cp -d /system/etc/security/cacerts/* /data/local/tmp/cacerts/")
                avd_manager.shell("mount -t tmpfs tmpfs /system/etc/security/cacerts/")
                avd_manager.shell("cp -d /data/local/tmp/cacerts/* /system/etc/security/cacerts/")
                avd_manager.shell("rm -rf /data/local/tmp/cacerts")

            # Push to the now writeable tmpfs-backed directory
            avd_manager.shell(f"cp {temp_device_path} {dest_path}")
            avd_manager.shell(f"chmod 644 {dest_path}")
            avd_manager.shell(f"chown root:root {dest_path}")
            logger.info("Successfully installed CA certificate via tmpfs overlay.")
            installed = True
        except Exception as e:
            logger.error(f"Failed to install CA cert via tmpfs overlay: {e}")
            raise AVDManagerError(f"Failed to install CA certificate on device: {e}") from e

    # Clean up temp file
    try:
        avd_manager.shell(f"rm -f {temp_device_path}")
    except Exception:
        pass

    return cert_filename


def get_default_frida_server_path(avd_manager: AVDManager) -> Path:
    """Download and cache the matching Frida-server binary based on the host version and device ABI."""
    abi = avd_manager.shell("getprop ro.product.cpu.abi").strip()
    if not abi:
        abi = "x86_64"  # Default fallback

    import frida

    version = frida.__version__

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
    avd_manager._run_adb(["root"])

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
