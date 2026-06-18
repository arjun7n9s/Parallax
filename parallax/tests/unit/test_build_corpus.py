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


def test_build_malware_records_skips_failed_downloads(tmp_path, monkeypatch, capsys):
    good = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    bad = "b" * 64

    monkeypatch.setattr(
        build_corpus,
        "query_tag",
        lambda *_args, **_kwargs: [
            {"sha256_hash": bad, "file_type": "apk", "tags": ["Cerberus"]},
            {"sha256_hash": good, "file_type": "apk", "tags": ["Cerberus"]},
        ],
    )

    def fake_download(sha256, **_kwargs):
        if sha256 == bad:
            raise RuntimeError("temporary 502")
        return b"hello"

    monkeypatch.setattr(build_corpus, "download_apk", fake_download)

    records = build_corpus.build_malware_records(
        targets={"Cerberus": 2},
        out_dir=tmp_path,
    )

    assert [record.sha256 for record in records] == [good]
    assert "temporary 502" in capsys.readouterr().out


def test_build_malware_records_skips_unreadable_existing_files(tmp_path, monkeypatch, capsys):
    sha256 = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    apk_path = tmp_path / "malware" / "Cerberus" / f"{sha256}.apk"
    apk_path.parent.mkdir(parents=True)
    apk_path.write_bytes(b"hello")

    monkeypatch.setattr(
        build_corpus,
        "query_tag",
        lambda *_args, **_kwargs: [
            {"sha256_hash": sha256, "file_type": "apk", "tags": ["Cerberus"]},
        ],
    )

    original_read_bytes = Path.read_bytes

    def fake_read_bytes(path):
        if path == apk_path:
            raise OSError("blocked by local scanner")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)

    records = build_corpus.build_malware_records(
        targets={"Cerberus": 1},
        out_dir=tmp_path,
    )

    assert records == []
    assert "blocked by local scanner" in capsys.readouterr().out
