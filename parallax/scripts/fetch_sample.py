"""Fetch a labelled Android malware sample from MalwareBazaar.

Usage:
    python scripts/fetch_sample.py <family-tag> [out_dir]

Queries MalwareBazaar for samples carrying the given tag, picks the first
APK, downloads it (zip is AES-encrypted, password "infected"), extracts it
to ``out_dir`` (default ``samples/``) and prints the ground-truth metadata
(family signature, tags) so the pipeline output can be checked against it.

Requires MALWAREBAZAAR_API_KEY in the environment / .env.
"""

import io
import sys

import httpx
import pyzipper

from parallax.core.config import settings

MB_API = "https://mb-api.abuse.ch/api/v1/"
ZIP_PASSWORD = b"infected"


def _headers() -> dict:
    if not settings.MALWAREBAZAAR_API_KEY:
        sys.exit("MALWAREBAZAAR_API_KEY not configured.")
    return {"Auth-Key": settings.MALWAREBAZAAR_API_KEY}


def pick_apk(tag: str) -> dict:
    resp = httpx.post(
        MB_API,
        headers=_headers(),
        data={"query": "get_taginfo", "tag": tag, "limit": "50"},
        timeout=30,
    )
    body = resp.json()
    if body.get("query_status") != "ok":
        sys.exit(f"MalwareBazaar query failed: {body.get('query_status')}")
    for entry in body.get("data", []):
        if entry.get("file_type") == "apk":
            return entry
    sys.exit(f"No APK found among samples tagged '{tag}'.")


def download(sha256: str) -> bytes:
    resp = httpx.post(
        MB_API,
        headers=_headers(),
        data={"query": "get_file", "sha256_hash": sha256},
        timeout=120,
    )
    # MalwareBazaar mislabels the zip's content-type as JSON, so detect the
    # actual payload by the zip magic bytes rather than the header.
    if not resp.content.startswith(b"PK"):
        sys.exit(f"Download failed: {resp.text[:200]}")
    with pyzipper.AESZipFile(io.BytesIO(resp.content)) as zf:
        zf.setpassword(ZIP_PASSWORD)
        name = zf.namelist()[0]
        return zf.read(name)


def main() -> int:
    if len(sys.argv) < 2:
        return print(__doc__) or 1
    tag = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "samples"

    import os

    os.makedirs(out_dir, exist_ok=True)

    entry = pick_apk(tag)
    sha256 = entry["sha256_hash"]
    print("Ground truth (MalwareBazaar):")
    print(f"  sha256:    {sha256}")
    print(f"  signature: {entry.get('signature')}")
    print(f"  file_name: {entry.get('file_name')}")
    print(f"  file_type: {entry.get('file_type')}")
    print(f"  tags:      {entry.get('tags')}")
    print(f"  first_seen:{entry.get('first_seen')}")

    apk_bytes = download(sha256)
    out_path = os.path.join(out_dir, f"{sha256}.apk")
    with open(out_path, "wb") as fh:
        fh.write(apk_bytes)
    print(f"\nSaved {len(apk_bytes):,} bytes -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
