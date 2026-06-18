"""Tests for the F-Droid benign-control downloader."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "fetch_fdroid_benign.py"
spec = importlib.util.spec_from_file_location("fetch_fdroid_benign", SCRIPT)
fetch_fdroid = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules["fetch_fdroid_benign"] = fetch_fdroid
spec.loader.exec_module(fetch_fdroid)


def _index() -> dict:
    return {
        "packages": {
            "clean.small": {
                "metadata": {"name": {"en-US": "Small"}, "summary": {"en-US": "Tiny app"}},
                "versions": {
                    "old": {
                        "file": {"name": "/clean.small_1.apk", "sha256": "1" * 64, "size": 20},
                        "manifest": {"versionCode": 1, "versionName": "1.0"},
                    },
                    "new": {
                        "file": {"name": "/clean.small_2.apk", "sha256": "2" * 64, "size": 30},
                        "manifest": {"versionCode": 2, "versionName": "2.0"},
                    },
                },
            },
            "dirty": {
                "metadata": {"name": {"en-US": "Dirty"}},
                "versions": {
                    "dirty": {
                        "antiFeatures": {"Ads": {}},
                        "file": {"name": "/dirty.apk", "sha256": "3" * 64, "size": 10},
                        "manifest": {"versionCode": 1},
                    }
                },
            },
            "too.large": {
                "metadata": {"name": {"en-US": "Large"}},
                "versions": {
                    "large": {
                        "file": {"name": "/large.apk", "sha256": "4" * 64, "size": 9999},
                        "manifest": {"versionCode": 1},
                    }
                },
            },
        }
    }


def test_select_candidates_uses_latest_clean_small_versions():
    candidates = fetch_fdroid.select_candidates(
        _index(),
        count=5,
        max_size_mb=0.001,
        repo_base="https://example.test/repo/",
    )

    assert len(candidates) == 1
    assert candidates[0].package == "clean.small"
    assert candidates[0].version_code == 2
    assert candidates[0].source_url == "https://example.test/repo/clean.small_2.apk"


def test_candidate_output_name_and_manifest_row(tmp_path):
    candidate = fetch_fdroid.FdroidCandidate(
        package="org.example.app",
        name="Example",
        summary="Summary",
        version_code=7,
        version_name="7.0",
        apk_name="org.example.app.apk",
        sha256="abcdef" + "0" * 58,
        size=123,
        source_url="https://example.test/app.apk",
    )

    path = tmp_path / candidate.output_name()
    row = candidate.to_manifest_row(path)

    assert candidate.output_name() == "org.example.app_7_abcdef000000.apk"
    assert row["source"] == "F-Droid"
    assert row["path"] == str(path)


def test_write_manifest_jsonl(tmp_path):
    manifest = tmp_path / "manifest.jsonl"

    fetch_fdroid.write_manifest([{"package": "a"}, {"package": "b"}], manifest)

    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    assert rows == [{"package": "a"}, {"package": "b"}]


def test_download_candidate_reuses_existing_verified_apk(tmp_path):
    apk_bytes = b"apk"
    sha256 = fetch_fdroid._sha256_bytes(apk_bytes)
    candidate = fetch_fdroid.FdroidCandidate(
        package="org.example.app",
        name="Example",
        summary="Summary",
        version_code=1,
        version_name="1.0",
        apk_name="org.example.app.apk",
        sha256=sha256,
        size=len(apk_bytes),
        source_url="https://example.invalid/app.apk",
    )
    path = tmp_path / candidate.output_name()
    path.write_bytes(apk_bytes)

    assert fetch_fdroid.download_candidate(candidate, tmp_path) == path
