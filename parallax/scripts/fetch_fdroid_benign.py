"""Fetch benign APK controls from the official F-Droid repository.

The validation corpus needs clean controls that are explicit and auditable.
This helper downloads small, latest F-Droid APKs, verifies their SHA-256 from
the signed repository index metadata, and writes a JSONL manifest beside the
ignored sample files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx

DEFAULT_INDEX_URL = "https://f-droid.org/repo/index-v2.json"
DEFAULT_REPO_BASE = "https://f-droid.org/repo/"


@dataclass(frozen=True)
class FdroidCandidate:
    package: str
    name: str
    summary: str
    version_code: int
    version_name: str
    apk_name: str
    sha256: str
    size: int
    source_url: str

    def output_name(self) -> str:
        safe_package = "".join(ch if ch.isalnum() or ch in ".-" else "_" for ch in self.package)
        return f"{safe_package}_{self.version_code}_{self.sha256[:12]}.apk"

    def to_manifest_row(self, path: Path) -> dict[str, str | int]:
        return {
            "package": self.package,
            "name": self.name,
            "summary": self.summary,
            "version_code": self.version_code,
            "version_name": self.version_name,
            "sha256": self.sha256,
            "size": self.size,
            "source": "F-Droid",
            "source_url": self.source_url,
            "path": str(path),
        }


def _localized(value: object) -> str:
    if isinstance(value, dict):
        for key in ("en-US", "en-GB", "en"):
            if value.get(key):
                return str(value[key])
        for item in value.values():
            if item:
                return str(item)
    return str(value or "")


def load_index(index_url: str, *, timeout_s: int = 120) -> dict:
    with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
        response = client.get(index_url)
        response.raise_for_status()
        return response.json()


def select_candidates(
    index: dict,
    *,
    count: int,
    max_size_mb: float,
    repo_base: str = DEFAULT_REPO_BASE,
) -> list[FdroidCandidate]:
    max_size = int(max_size_mb * 1024 * 1024)
    candidates: list[FdroidCandidate] = []
    for package, payload in sorted((index.get("packages") or {}).items()):
        metadata = payload.get("metadata") or {}
        latest = _latest_clean_version(payload.get("versions") or {}, max_size=max_size)
        if latest is None:
            continue
        file_info = latest["file"]
        apk_name = str(file_info["name"]).lstrip("/")
        candidates.append(
            FdroidCandidate(
                package=str(package),
                name=_localized(metadata.get("name")) or str(package),
                summary=_localized(metadata.get("summary")),
                version_code=int(latest.get("manifest", {}).get("versionCode") or 0),
                version_name=str(latest.get("manifest", {}).get("versionName") or ""),
                apk_name=apk_name,
                sha256=str(file_info["sha256"]),
                size=int(file_info["size"]),
                source_url=urljoin(repo_base, apk_name),
            )
        )

    candidates.sort(key=lambda c: (c.size, c.package))
    return candidates[:count]


def _latest_clean_version(versions: dict, *, max_size: int) -> dict | None:
    clean: list[dict] = []
    for version in versions.values():
        if version.get("antiFeatures"):
            continue
        file_info = version.get("file") or {}
        if not str(file_info.get("name", "")).endswith(".apk"):
            continue
        size = int(file_info.get("size") or 0)
        if size <= 0 or size > max_size:
            continue
        if not file_info.get("sha256"):
            continue
        clean.append(version)
    if not clean:
        return None
    return max(
        clean,
        key=lambda v: (
            int(v.get("manifest", {}).get("versionCode") or 0),
            int(v.get("added") or 0),
        ),
    )


def download_candidate(
    candidate: FdroidCandidate, out_dir: Path, *, timeout_s: int = 180, retries: int = 3
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / candidate.output_name()
    if path.exists() and _sha256(path) == candidate.sha256:
        return path

    last_error: Exception | None = None
    for _attempt in range(1, retries + 1):
        try:
            with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
                response = client.get(candidate.source_url)
                response.raise_for_status()
                path.write_bytes(response.content)
            break
        except httpx.HTTPError as exc:
            last_error = exc
    else:
        raise RuntimeError(f"failed to download {candidate.package}: {last_error}") from last_error

    actual = _sha256(path)
    if actual != candidate.sha256:
        path.unlink(missing_ok=True)
        raise RuntimeError(
            f"SHA-256 mismatch for {candidate.package}: expected {candidate.sha256}, got {actual}"
        )
    return path


def write_manifest(rows: list[dict[str, str | int]], manifest: Path) -> None:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-url", default=DEFAULT_INDEX_URL)
    parser.add_argument("--repo-base", default=DEFAULT_REPO_BASE)
    parser.add_argument("--out-dir", type=Path, default=Path("samples/benign/fdroid"))
    parser.add_argument(
        "--manifest", type=Path, default=Path("samples/benign/fdroid_manifest.jsonl")
    )
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--max-size-mb", type=float, default=15.0)
    parser.add_argument("--download-timeout-s", type=int, default=180)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    index = load_index(args.index_url)
    candidates = select_candidates(
        index,
        count=args.count,
        max_size_mb=args.max_size_mb,
        repo_base=args.repo_base,
    )
    if len(candidates) < args.count:
        print(f"warning: requested {args.count} benign APKs, selected {len(candidates)}")

    rows: list[dict[str, str | int]] = []
    for candidate in candidates:
        path = args.out_dir / candidate.output_name()
        if not args.dry_run:
            path = download_candidate(
                candidate,
                args.out_dir,
                timeout_s=args.download_timeout_s,
                retries=args.retries,
            )
        rows.append(candidate.to_manifest_row(path))
        print(f"selected {candidate.package} {candidate.version_name} {candidate.size} bytes")

    write_manifest(rows, args.manifest)
    print(f"wrote {len(rows)} F-Droid rows -> {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
