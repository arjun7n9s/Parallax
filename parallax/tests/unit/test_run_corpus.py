"""Tests for the Phase 2 corpus validation harness."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_corpus.py"
spec = importlib.util.spec_from_file_location("run_corpus", SCRIPT)
run_corpus = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules["run_corpus"] = run_corpus
spec.loader.exec_module(run_corpus)


def test_load_manifest_requires_core_fields(tmp_path):
    manifest = tmp_path / "corpus.jsonl"
    manifest.write_text(
        json.dumps(
            {
                "sha256": "a" * 64,
                "family": "Cerberus",
                "true_verdict": "MALICIOUS",
                "path": "samples/a.apk",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    items = run_corpus.load_manifest(manifest)

    assert len(items) == 1
    assert items[0].true_family == "Cerberus"


def test_parse_pipeline_output_extracts_literal_result_fields():
    text = """
status             : complete
verdict            : HIGH
final_score        : 65.0
family_attribution : 'Cerberus' (confidence 0.9)
"""

    parsed = run_corpus.parse_pipeline_output(text)

    assert parsed["status"] == "complete"
    assert parsed["sys_verdict"] == "HIGH"
    assert parsed["sys_score"] == "65.0"
    assert parsed["sys_family"] == "Cerberus"
    assert parsed["sys_family_confidence"] == "0.9"


def test_make_result_row_marks_family_match():
    item = run_corpus.CorpusItem(
        sha256="a" * 64,
        true_family="Cerberus",
        true_verdict="MALICIOUS",
        path="samples/a.apk",
    )

    row = run_corpus.make_result_row(
        item,
        {"sys_verdict": "HIGH", "sys_family": "Cerberus", "sys_score": "65.0"},
        latency_s=12.34,
    )

    assert row["match"] == "true"
    assert row["latency_s"] == "12.3"


def test_compute_metrics_precision_recall_f1_and_latency():
    rows = [
        {
            "true_family": "Cerberus",
            "true_verdict": "MALICIOUS",
            "sys_verdict": "HIGH",
            "sys_score": "80.0",
            "match": "true",
            "latency_s": "10.0",
        },
        {
            "true_family": "Hydra",
            "true_verdict": "MALICIOUS",
            "sys_verdict": "CLEAN",
            "sys_score": "20.0",
            "match": "false",
            "latency_s": "20.0",
        },
        {
            "true_family": "benign",
            "true_verdict": "CLEAN",
            "sys_verdict": "LOW",
            "sys_score": "30.0",
            "match": "true",
            "latency_s": "30.0",
        },
        {
            "true_family": "benign",
            "true_verdict": "CLEAN",
            "sys_verdict": "CLEAN",
            "sys_score": "40.0",
            "match": "true",
            "latency_s": "40.0",
        },
    ]

    metrics = run_corpus.compute_metrics(rows)

    assert metrics["family_top1"] == 0.5
    assert metrics["verdict_precision"] == 0.5
    assert metrics["verdict_recall"] == 0.5
    assert metrics["verdict_f1"] == 0.5
    assert metrics["validation_ready"] is False
    assert metrics["brier"] == pytest.approx(0.2325)
    assert metrics["tp"] == 1
    assert metrics["fp"] == 1
    assert metrics["tn"] == 1
    assert metrics["fn"] == 1
    assert metrics["latency_p50_s"] == 25.0


def test_render_report_includes_summary_and_accuracy_table():
    row = {
        "sha256": "a" * 64,
        "true_family": "Cerberus",
        "true_verdict": "MALICIOUS",
        "sys_verdict": "HIGH",
        "sys_family": "Cerberus",
        "sys_score": "65.0",
        "match": "true",
    }

    report = run_corpus.render_report([row], run_corpus.compute_metrics([row]))

    assert "# PARALLAX Validation Report" in report
    assert "PROVISIONAL ONLY" in report
    assert "Evidence gate met (N>=200 usable): no" in report
    assert "Brier score" in report
    assert "Family top-1 accuracy" in report
    assert "| True malicious | 1 | 0 |" in report
    assert "Cerberus" in report
