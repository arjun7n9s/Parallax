"""Guards that emulator provisioning stays paired with the Python Frida client."""

from pathlib import Path

PARALLAX_ROOT = Path(__file__).resolve().parents[2]


def test_emulator_bakes_frida_server_matching_python_pin():
    requirements = (PARALLAX_ROOT / "requirements.txt").read_text(encoding="utf-8")
    dockerfile = (PARALLAX_ROOT / "sandbox" / "Dockerfile.emulator").read_text(encoding="utf-8")

    assert "frida==16.7.19" in requirements
    assert "ARG FRIDA_VERSION=16.7.19" in dockerfile
    assert "releases/download/${FRIDA_VERSION}" in dockerfile


def test_emulator_image_no_longer_bakes_frida_17_java_bridge_breaker():
    dockerfile = (PARALLAX_ROOT / "sandbox" / "Dockerfile.emulator").read_text(encoding="utf-8")

    assert "17.11.0" not in dockerfile
    assert "frida-server-17" not in dockerfile
