"""Tests for the Phase 2 corpus builder."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_corpus.py"
spec = importlib.util.spec_from_file_location("build_corpus", SCRIPT)
build_corpus = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules["build_corpus"] = build_corpus
spec.loader.exec_module(build_corpus)


def test_parse_family_targets_defaults_and_custom():
    defaults = build_corpus.parse_family_targets(None)
    assert defaults["Cerberus"] == 50
    assert defaults["Hydra"] == 50

    custom = build_corpus.parse_family_targets("Cerberus=2, Hydra=3")
    assert custom == {"Cerberus": 2, "Hydra": 3}


@pytest.mark.parametrize("raw", ["Cerberus", "Cerberus=0", " = "])
def test_parse_family_targets_rejects_invalid(raw):
    with pytest.raises((ValueError, TypeError)):
        build_corpus.parse_family_targets(raw)


def test_select_apks_filters_family_and_dedupes():
    seen = {"already"}
    entries = [
        {"sha256_hash": "already", "file_type": "apk", "tags": ["Cerberus"]},
        {"sha256_hash": "jar", "file_type": "jar", "tags": ["Cerberus"]},
        {"sha256_hash": "wrong", "file_type": "apk", "tags": ["Hydra"]},
        {"sha256_hash": "good1", "file_type": "apk", "tags": ["Cerberus"]},
        {"sha256_hash": "good2", "file_type": "apk", "signature": "Android/Cerberus"},
    ]

    selected = build_corpus.select_apks(entries, family="Cerberus", count=2, seen=seen)

    assert [e["sha256_hash"] for e in selected] == ["good1", "good2"]
    assert seen == {"already", "good1", "good2"}


def test_write_manifest_jsonl(tmp_path):
    manifest = tmp_path / "corpus.jsonl"
    records = [
        build_corpus.CorpusRecord(
            sha256="a" * 64,
            family="Cerberus",
            true_verdict="MALICIOUS",
            source="MalwareBazaar",
            path="samples/corpus/malware/Cerberus/a.apk",
            tags=["Cerberus"],
        )
    ]

    build_corpus.write_manifest(records, manifest)

    lines = manifest.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["family"] == "Cerberus"
    assert row["true_verdict"] == "MALICIOUS"
    assert row["tags"] == ["Cerberus"]


def test_readiness_issues_require_minimums_and_benign():
    records = [
        build_corpus.CorpusRecord(
            sha256="a" * 64,
            family="Cerberus",
            true_verdict="MALICIOUS",
            source="MalwareBazaar",
            path="samples/corpus/malware/Cerberus/a.apk",
        )
    ]

    issues = build_corpus.readiness_issues(records, min_total=200, min_benign=20)

    assert "need at least 200 total records; selected 1" in issues
    assert "need at least 20 benign APKs; selected 0" in issues


def test_corpus_summary_counts_families_and_verdicts():
    records = [
        build_corpus.CorpusRecord(
            sha256="a" * 64,
            family="Cerberus",
            true_verdict="MALICIOUS",
            source="MalwareBazaar",
            path="a.apk",
        ),
        build_corpus.CorpusRecord(
            sha256="b" * 64,
            family="benign",
            true_verdict="CLEAN",
            source="local_benign",
            path="b.apk",
        ),
    ]

    summary = build_corpus.corpus_summary(records)

    assert summary["total"] == 2
    assert summary["malicious"] == 1
    assert summary["benign"] == 1
    assert summary["family:Cerberus"] == 1
    assert summary["family:benign"] == 1


def test_build_benign_records_hashes_local_apks(tmp_path):
    benign_dir = tmp_path / "benign"
    nested_dir = benign_dir / "fdroid"
    nested_dir.mkdir(parents=True)
    (nested_dir / "clock.apk").write_bytes(b"benign-apk")

    records = build_corpus.build_benign_records(benign_dir, limit=20)

    assert len(records) == 1
    assert records[0].family == "benign"
    assert records[0].true_verdict == "CLEAN"
    assert records[0].source == "local_benign"
    assert records[0].file_name == "clock.apk"
