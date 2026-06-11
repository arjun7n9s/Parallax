"""
Integration tests for the installation script (install.py).
"""

import datetime
import os
import tempfile
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from parallax.analysis.dynamic.avd_manager import AVDManager
from parallax.analysis.dynamic.install import (
    get_android_ca_hash,
    get_default_frida_server_path,
    install_frida_server,
    install_mitmproxy_ca,
)


@pytest.fixture(scope="module")
def avd_manager():
    manager = AVDManager(adb_host="127.0.0.1", adb_port=5555)
    manager.wait_for_ready(timeout=180)
    return manager


def generate_self_signed_cert() -> bytes:
    """Helper to generate a self-signed cert for testing."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "Parallax Test CA")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM)


def test_get_android_ca_hash():
    cert_pem = generate_self_signed_cert()
    ca_hash = get_android_ca_hash(cert_pem)
    assert len(ca_hash) == 10
    assert ca_hash.endswith(".0")


def test_install_mitmproxy_ca(avd_manager):
    cert_pem = generate_self_signed_cert()
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as tmp:
        tmp.write(cert_pem)
        tmp_path = Path(tmp.name)

    try:
        cert_filename = install_mitmproxy_ca(avd_manager, tmp_path)
        dest_path = f"/system/etc/security/cacerts/{cert_filename}"

        # Verify it exists in the cacerts path
        ls_out = avd_manager.shell(f"ls -la {dest_path}")
        assert cert_filename in ls_out

        # Clean up
        avd_manager.shell(f"rm -f {dest_path}")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def test_get_default_frida_server_path(avd_manager):
    # Verify download/cache works
    binary_path = get_default_frida_server_path(avd_manager)
    assert binary_path.exists()
    assert binary_path.is_file()
    # Check execution permission
    assert os.access(binary_path, os.X_OK)


def test_install_frida_server(avd_manager):
    binary_path = get_default_frida_server_path(avd_manager)
    # Reinstall and verify
    install_frida_server(avd_manager, binary_path)
    assert avd_manager.is_frida_running() is True
