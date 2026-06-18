"""Smoke-check external API connectivity: aimlapi gateway tiers + MalwareBazaar.

Run after setting AIML_API / MALWAREBAZAAR_API_KEY in .env:

    python scripts/smoke_cloud.py

Makes one tiny real call per tier (economy, premium, vision) through the
PARALLAX provider — verifying routing, auth, and response parsing — and one
authenticated MalwareBazaar query. Never prints secrets.
"""

import asyncio
import base64
import io
import struct
import sys
import zlib

import httpx

from parallax.ai.llm import llm
from parallax.core.config import settings

MB_API = "https://mb-api.abuse.ch/api/v1/"


def _tiny_png() -> str:
    """A valid 8x8 red PNG, base64-encoded — no Pillow dependency."""
    width = height = 8
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    buf = io.BytesIO()
    buf.write(b"\x89PNG\r\n\x1a\n")
    buf.write(chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)))
    buf.write(chunk(b"IDAT", zlib.compress(raw)))
    buf.write(chunk(b"IEND", b""))
    return base64.b64encode(buf.getvalue()).decode()


async def check_gateway() -> bool:
    ok = True
    for label, role, kwargs in [
        ("economy  (triage -> gpt-4o-mini)", "triage", {}),
        ("premium  (synthesis -> sonnet)", "synthesis", {}),
        ("vision   (visual -> gemini-flash)", "visual", {"images": [_tiny_png()]}),
    ]:
        provider = llm.provider_for(role)
        model = llm.spec_for(role).cloud_model
        try:
            if "images" in kwargs:
                out = await llm.complete_text(
                    role, "What colour is this image? One word.", **kwargs
                )
                passed = bool(out.strip())
            else:
                out_json = await llm.complete_json(role, 'Reply with exactly {"status": "ok"}.')
                passed = out_json.get("status") == "ok"
        except Exception as exc:  # noqa: BLE001 — report any failure mode
            print(f"  FAIL {label}: via {provider}: {type(exc).__name__}: {exc}")
            ok = False
            continue
        verdict = "ok" if passed else "UNEXPECTED RESPONSE"
        print(f"  {verdict:4} {label}: via {provider} [{model}]")
        ok = ok and passed
    return ok


def check_malwarebazaar() -> bool:
    key = settings.MALWAREBAZAAR_API_KEY
    if not key:
        print("  SKIP MalwareBazaar: no key configured")
        return False
    resp = httpx.post(
        MB_API,
        headers={"Auth-Key": key},
        data={"query": "get_taginfo", "tag": "SharkBot", "limit": "3"},
        timeout=30,
    )
    body = resp.json()
    status = body.get("query_status", "?")
    n = len(body.get("data", []) or [])
    passed = resp.status_code == 200 and status == "ok" and n > 0
    print(f"  {'ok' if passed else 'FAIL'}   MalwareBazaar: query_status={status}, samples={n}")
    return passed


async def main() -> int:
    print(f"LLM_MODE={settings.LLM_MODE}  CLOUD_PROVIDER={settings.CLOUD_PROVIDER}")
    print("aimlapi gateway:")
    gw = await check_gateway()
    print("MalwareBazaar:")
    mb = check_malwarebazaar()
    await llm.close()
    return 0 if (gw and mb) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
