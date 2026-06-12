"""Protocol decoders for non-trivial C2 traffic.

mitmproxy gives us HTTP(S) for free. Banking malware increasingly hides C2 in
DNS, DNS-over-HTTPS, WebSockets and gRPC. These decoders extract structured
signal from raw payloads so the Behavior Analyst and IoC extractor can reason
over more than plain web requests.

Each decoder is defensive: it returns ``None`` when the payload is not the
expected protocol, and never raises on malformed input.
"""

from __future__ import annotations

import base64
import logging
import struct

logger = logging.getLogger(__name__)


def decode_dns(payload: bytes) -> dict | None:
    """Parse a DNS query packet and extract queried names (DNS exfil pattern)."""
    if not payload or len(payload) < 12:
        return None
    try:
        qdcount = struct.unpack(">H", payload[4:6])[0]
        if qdcount == 0 or qdcount > 20:
            return None
        names: list[str] = []
        offset = 12
        for _ in range(qdcount):
            labels = []
            guard = 0
            while offset < len(payload) and guard < 64:
                length = payload[offset]
                if length == 0:
                    offset += 1
                    break
                if length & 0xC0:  # compression pointer
                    offset += 2
                    break
                offset += 1
                labels.append(payload[offset : offset + length].decode("ascii", "ignore"))
                offset += length
                guard += 1
            if labels:
                names.append(".".join(labels))
            offset += 4  # QTYPE + QCLASS
        if not names:
            return None
        return {"protocol": "dns", "queries": names}
    except Exception:
        return None


def decode_dns_over_https(content_type: str, payload: bytes) -> dict | None:
    """Detect DNS-over-HTTPS (RFC 8484) by content type, then parse as DNS."""
    if "application/dns-message" not in (content_type or "").lower():
        return None
    parsed = decode_dns(payload)
    if parsed:
        parsed["protocol"] = "doh"
    return parsed


def decode_websocket(payload: bytes) -> dict | None:
    """Extract a text/binary WebSocket frame's unmasked payload."""
    if not payload or len(payload) < 2:
        return None
    try:
        b0, b1 = payload[0], payload[1]
        opcode = b0 & 0x0F
        if opcode not in (0x1, 0x2):  # text, binary
            return None
        masked = bool(b1 & 0x80)
        length = b1 & 0x7F
        idx = 2
        if length == 126:
            length = struct.unpack(">H", payload[idx : idx + 2])[0]
            idx += 2
        elif length == 127:
            length = struct.unpack(">Q", payload[idx : idx + 8])[0]
            idx += 8
        if length <= 0 or length > 1_000_000:
            return None
        if masked:
            mask = payload[idx : idx + 4]
            idx += 4
            data = bytes(payload[idx + i] ^ mask[i % 4] for i in range(min(length, len(payload) - idx)))
        else:
            data = payload[idx : idx + length]
        kind = "text" if opcode == 0x1 else "binary"
        decoded = data.decode("utf-8", "ignore") if kind == "text" else base64.b64encode(data).decode()
        return {"protocol": "websocket", "frame_type": kind, "payload": decoded[:2000]}
    except Exception:
        return None


def decode_grpc(content_type: str, payload: bytes) -> dict | None:
    """Detect gRPC by content type and extract the length-prefixed message size."""
    if "application/grpc" not in (content_type or "").lower():
        return None
    if not payload or len(payload) < 5:
        return {"protocol": "grpc", "messages": 0}
    try:
        compressed = payload[0]
        msg_len = struct.unpack(">I", payload[1:5])[0]
        return {
            "protocol": "grpc",
            "compressed": bool(compressed),
            "message_length": msg_len,
        }
    except Exception:
        return None


def decode_payload(content_type: str, payload: bytes) -> dict | None:
    """Try all decoders against a payload; return the first structured match."""
    for decoder in (
        lambda: decode_dns_over_https(content_type, payload),
        lambda: decode_grpc(content_type, payload),
        lambda: decode_websocket(payload),
        lambda: decode_dns(payload),
    ):
        result = decoder()
        if result:
            return result
    return None
