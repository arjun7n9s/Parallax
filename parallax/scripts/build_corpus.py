"""Build the labeled APK corpus manifest for PARALLAX validation.

The default plan targets the Phase 2 validation mix from ``Claude/VALIDATION.md``:
Cerberus, Hydra, Anatsa, SpyNote, mixed banking families, plus local benign
controls. Malware samples are pulled from MalwareBazaar; benign APKs are
ingested from a local directory because public app stores do not provide a
stable authenticated API.

Examples:
    python scripts/build_corpus.py --dry-run
    python scripts/build_corpus.py --families Cerberus=5,Hydra=5 --out-dir samples/corpus
    python scripts/build_corpus.py --benign-dir samples/benign --benign-limit 20

Requires ``MALWAREBAZAAR_API_KEY`` in .env for malware downloads.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import httpx
import pyzipper

from parallax.core.config import settings

MB_API = "https://mb-api.abuse.ch/api/v1/"
ZIP_PASSWORD = b"infected"

DEFAULT_FAMILIES: dict[str, int] = {
    "Cerberus": 50,
    "Hydra": 50,
    "Anatsa": 30,
    "SpyNote": 30,
    "SharkBot": 10,
    "FluBot": 10,
    "TeaBot": 10,
    "Octo": 10,
    "Coper": 10,
    "Ermac": 10,
    "Xenomorph": 10,
    "SOVA": 10,
    "Vultur": 10,
    "Alien": 10,
}


@dataclass(frozen=True)
class CorpusRecord:
    sha256: str
    family: str
    true_verdict: str
    source: str
    path: str
    signature: str = ""
    tags: list[str] | None = None
    first_seen: str = ""
    file_name: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {
                "sha256": self.sha256,
                "family": self.family,
                "true_verdict": self.true_verdict,
                "source": self.source,
                "path": self.path,
                "signature": self.signature,
                "tags": self.tags or [],
                "first_seen": self.first_seen,
                "file_name": self.file_name,
            },
            sort_keys=True,
        )


def _headers() -> dict[str, str]:
    if not settings.MALWAREBAZAAR_API_KEY:
        raise RuntimeError("MALWAREBAZAAR_API_KEY is not configured.")
    return {"Auth-Key": settings.MALWAREBAZAAR_API_KEY}


def parse_family_targets(raw: str | None) -> dict[str, int]:
    """Parse ``Family=Count`` pairs, falling back to the validation target mix."""
    if not raw:
        return dict(DEFAULT_FAMILIES)

    targets: dict[str, int] = {}
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"Invalid family target {item!r}; expected Family=Count")
        family, count_s = item.split("=", 1)
        count = int(count_s)
        if count <= 0:
            raise ValueError(f"Target count for {family!r} must be positive")
        targets[family.strip()] = count
    if not targets:
        raise ValueError("No valid family targets supplied.")
    return targets


def query_tag(tag: str, *, limit: int = 200, client: httpx.Client | None = None) -> list[dict]:
    """Return MalwareBazaar tag records for a family/tag."""
    own_client = client is None
    client = client or httpx.Client(timeout=30)
    try:
        resp = client.post(
            MB_API,
            headers=_headers(),
            data={"query": "get_taginfo", "tag": tag, "limit": str(limit)},
        )
        resp.raise_for_status()
        body = resp.json()
    finally:
        if own_client:
            client.close()

    if body.get("query_status") != "ok":
        raise RuntimeError(f"MalwareBazaar query for {tag!r} failed: {body.get('query_status')}")
    return list(body.get("data", []))


def select_apks(entries: Iterable[dict], *, family: str, count: int, seen: set[str]) -> list[dict]:
    """Pick APK records, deduping across the whole corpus by sha256."""
    selected: list[dict] = []
    for entry in entries:
        sha256 = entry.get("sha256_hash") or entry.get("sha256")
        if not sha256 or sha256 in seen:
            continue
        if entry.get("file_type") != "apk":
            continue
        tags = [str(t).lower() for t in entry.get("tags", [])]
        signature = str(entry.get("signature") or "").lower()
        family_l = family.lower()
        if family_l not in tags and family_l not in signature:
            continue
        selected.append(entry)
        seen.add(sha256)
        if len(selected) >= count:
            break
    return selected


def download_apk(sha256: str, *, client: httpx.Client | None = None) -> bytes:
    """Download and extract a MalwareBazaar APK zip by sha256."""
    own_client = client is None
    client = client or httpx.Client(timeout=120)
    try:
        resp = client.post(
            MB_API,
            headers=_headers(),
            data={"query": "get_file", "sha256_hash": sha256},
        )
        resp.raise_for_status()
        content = resp.content
    finally:
        if own_client:
            client.close()

    if not content.startswith(b"PK"):
        raise RuntimeError(f"MalwareBazaar download for {sha256} did not return a zip payload")
    with pyzipper.AESZipFile(io.BytesIO(content)) as zf:
        zf.setpassword(ZIP_PASSWORD)
        name = zf.namelist()[0]
        return zf.read(name)


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def build_malware_records(
    *,
    targets: dict[str, int],
    out_dir: Path,
    dry_run: bool = False,
    query_limit: int = 200,
    client: httpx.Client | None = None,
) -> list[CorpusRecord]:
    seen: set[str] = set()
    records: list[CorpusRecord] = []

    for family, count in targets.items():
        entries = query_tag(family, limit=max(query_limit, count), client=client)
        selected = select_apks(entries, family=family, count=count, seen=seen)
        if len(selected) < count:
            print(f"warning: requested {count} {family} APKs, selected {len(selected)}")

        for entry in selected:
            sha256 = entry["sha256_hash"]
            apk_path = out_dir / "malware" / family / f"{sha256}.apk"
            if not dry_run and not apk_path.exists():
                _write_bytes(apk_path, download_apk(sha256, client=client))
            records.append(
                CorpusRecord(
                    sha256=sha256,
                    family=family,
                    true_verdict="MALICIOUS",
                    source="MalwareBazaar",
                    path=str(apk_path),
                    signature=entry.get("signature") or "",
                    tags=entry.get("tags") or [],
                    first_seen=entry.get("first_seen") or "",
                    file_name=entry.get("file_name") or "",
                )
            )
    return records


def build_benign_records(benign_dir: Path | None, *, limit: int) -> list[CorpusRecord]:
    if not benign_dir:
        return []
    apks = sorted(benign_dir.rglob("*.apk"))[:limit]
    records: list[CorpusRecord] = []
    for path in apks:
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append(
            CorpusRecord(
                sha256=sha256,
                family="benign",
                true_verdict="CLEAN",
                source="local_benign",
                path=str(path),
                file_name=path.name,
            )
        )
    if len(records) < limit:
        print(f"warning: requested {limit} benign APKs, found {len(records)} in {benign_dir}")
    return records


def write_manifest(records: list[CorpusRecord], manifest: Path) -> None:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("\n".join(r.to_json() for r in records) + "\n", encoding="utf-8")


def corpus_summary(records: list[CorpusRecord]) -> dict[str, int]:
    summary = {
        "total": len(records),
        "malicious": sum(1 for r in records if r.true_verdict == "MALICIOUS"),
        "benign": sum(1 for r in records if r.true_verdict == "CLEAN"),
    }
    for record in records:
        summary[f"family:{record.family}"] = summary.get(f"family:{record.family}", 0) + 1
    return summary


def readiness_issues(
    records: list[CorpusRecord], *, min_total: int = 0, min_benign: int = 0
) -> list[str]:
    summary = corpus_summary(records)
    issues: list[str] = []
    if min_total and summary["total"] < min_total:
        issues.append(f"need at least {min_total} total records; selected {summary['total']}")
    if min_benign and summary["benign"] < min_benign:
        issues.append(f"need at least {min_benign} benign APKs; selected {summary['benign']}")
    if summary["malicious"] == 0:
        issues.append("need at least one malicious APK; selected 0")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--families", help="Comma-separated Family=Count targets")
    parser.add_argument("--out-dir", default="samples/corpus", type=Path)
    parser.add_argument("--manifest", default="samples/corpus.jsonl", type=Path)
    parser.add_argument("--query-limit", default=200, type=int)
    parser.add_argument("--benign-dir", type=Path)
    parser.add_argument("--benign-limit", default=20, type=int)
    parser.add_argument("--dry-run", action="store_true", help="Write manifest without downloads")
    parser.add_argument(
        "--min-total",
        default=0,
        type=int,
        help="Fail if the selected corpus has fewer than this many records.",
    )
    parser.add_argument(
        "--require-benign",
        action="store_true",
        help="Fail unless at least --benign-limit benign APKs are selected.",
    )
    parser.add_argument(
        "--min-benign",
        default=0,
        type=int,
        help="Fail if fewer than this many benign APKs are selected.",
    )
    args = parser.parse_args()

    targets = parse_family_targets(args.families)
    records = build_malware_records(
        targets=targets,
        out_dir=args.out_dir,
        dry_run=args.dry_run,
        query_limit=args.query_limit,
    )
    records.extend(build_benign_records(args.benign_dir, limit=args.benign_limit))
    min_benign = args.benign_limit if args.require_benign else args.min_benign
    issues = readiness_issues(records, min_total=args.min_total, min_benign=min_benign)
    if issues:
        for issue in issues:
            print(f"readiness error: {issue}")
        return 2

    write_manifest(records, args.manifest)

    summary = corpus_summary(records)
    print(f"wrote {len(records)} records -> {args.manifest}")
    print(f"malicious={summary['malicious']} benign={summary['benign']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
