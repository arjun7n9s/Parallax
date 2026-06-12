"""Unit tests for the dynamic protocol decoders."""

import struct

from parallax.analysis.dynamic.protocol_decoders import (
    decode_dns,
    decode_dns_over_https,
    decode_grpc,
    decode_payload,
    decode_websocket,
)


def _build_dns_query(name: str) -> bytes:
    header = struct.pack(">HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0)
    q = b""
    for label in name.split("."):
        q += bytes([len(label)]) + label.encode()
    q += b"\x00" + struct.pack(">HH", 1, 1)
    return header + q


def test_decode_dns_extracts_query():
    pkt = _build_dns_query("exfil.evil-c2.com")
    out = decode_dns(pkt)
    assert out is not None
    assert "exfil.evil-c2.com" in out["queries"]


def test_decode_dns_rejects_garbage():
    assert decode_dns(b"\x00\x01") is None
    assert decode_dns(b"") is None


def test_decode_doh_requires_content_type():
    pkt = _build_dns_query("c2.example.com")
    assert decode_dns_over_https("text/html", pkt) is None
    out = decode_dns_over_https("application/dns-message", pkt)
    assert out is not None and out["protocol"] == "doh"


def test_decode_grpc():
    body = b"\x00" + struct.pack(">I", 42) + b"x" * 42
    out = decode_grpc("application/grpc+proto", body)
    assert out is not None
    assert out["message_length"] == 42
    assert decode_grpc("application/json", body) is None


def test_decode_websocket_text_frame():
    text = b"hello c2"
    frame = bytes([0x81, len(text)]) + text  # FIN+text, unmasked
    out = decode_websocket(frame)
    assert out is not None
    assert out["frame_type"] == "text"
    assert "hello c2" in out["payload"]


def test_decode_payload_dispatch():
    pkt = _build_dns_query("a.b.com")
    assert decode_payload("application/dns-message", pkt)["protocol"] == "doh"
