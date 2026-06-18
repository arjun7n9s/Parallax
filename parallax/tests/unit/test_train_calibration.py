"""Tests for the Phase 2 calibration trainer."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "train_calibration.py"
spec = importlib.util.spec_from_file_location("train_calibration", SCRIPT)
train_calibration = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules["train_calibration"] = train_calibration
spec.loader.exec_module(train_calibration)


def _write_results(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["sha256", "true_verdict", "sys_score"])
        writer.writeheader()
        writer.writerows(rows)


def test_load_samples_skips_unusable_rows(tmp_path):
    results = tmp_path / "results.csv"
    _write_results(
        results,
        [
            {"sha256": "a", "true_verdict": "MALICIOUS", "sys_score": "82"},
            {"sha256": "b", "true_verdict": "CLEAN", "sys_score": "not-a-score"},
            {"sha256": "c", "true_verdict": "UNKNOWN", "sys_score": "12"},
        ],
    )

    samples = train_calibration.load_samples(results)

    assert samples == [train_calibration.CalibrationSample(score=82.0, label=1)]


def test_validate_samples_rejects_small_or_one_class_sets():
    with pytest.raises(ValueError, match="at least 3"):
        train_calibration.validate_samples(
            [train_calibration.CalibrationSample(score=10.0, label=0)],
            min_samples=3,
        )

    with pytest.raises(ValueError, match="both malicious and clean"):
        train_calibration.validate_samples(
            [
                train_calibration.CalibrationSample(score=80.0, label=1),
                train_calibration.CalibrationSample(score=90.0, label=1),
            ],
            min_samples=2,
        )


def test_fit_isotonic_returns_monotonic_probabilities():
    samples = [
        train_calibration.CalibrationSample(score=10.0, label=0),
        train_calibration.CalibrationSample(score=20.0, label=1),
        train_calibration.CalibrationSample(score=30.0, label=0),
        train_calibration.CalibrationSample(score=90.0, label=1),
    ]

    points = train_calibration.fit_isotonic(samples)
    probabilities = [y for _, y in points]

    assert probabilities == sorted(probabilities)
    assert train_calibration.predict_probability(points, 90.0) == 1.0


def test_write_model_contains_quality_metadata(tmp_path):
    model = tmp_path / "model.json"
    samples = [
        train_calibration.CalibrationSample(score=10.0, label=0),
        train_calibration.CalibrationSample(score=90.0, label=1),
    ]
    points = train_calibration.fit_isotonic(samples)

    train_calibration.write_model(model, samples=samples, points=points)

    payload = json.loads(model.read_text(encoding="utf-8"))
    assert payload["type"] == "isotonic_probability"
    assert payload["sample_count"] == 2
    assert payload["malicious_count"] == 1
    assert payload["clean_count"] == 1
    assert payload["has_both_classes"] is True
    assert payload["brier"] <= payload["identity_brier"]
    assert payload["points"]
