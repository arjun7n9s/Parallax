"""Tests for Layer-B risk calibration plumbing."""

import json

from parallax.ai import calibration, risk
from parallax.ai.schemas import (
    BehaviorAnalystOutput,
    CodeInterpreterOutput,
    IntelCorrelatorOutput,
    VisualIntelOutput,
)


class _ProbabilityModel:
    def predict(self, values):
        assert values == [60.0]
        return [0.73]


class _BadModel:
    def predict(self, values):
        raise RuntimeError("bad model")


def test_calibration_identity_when_model_missing(tmp_path):
    calibration.clear_calibration_cache()
    assert calibration.calibrate_score(42.5, tmp_path / "missing.pkl") == 42.5


def test_calibration_scales_probability_predictions(monkeypatch):
    monkeypatch.setattr(calibration, "_load_calibrator", lambda path: _ProbabilityModel())
    assert calibration.calibrate_score(60.0) == 73.0


def test_calibration_loads_json_points(tmp_path):
    model_path = tmp_path / "model.json"
    model_path.write_text(
        json.dumps({"points": [[0, 0], [50, 0.5], [100, 0.9]]}),
        encoding="utf-8",
    )
    calibration.clear_calibration_cache()
    assert calibration.calibrate_score(75.0, model_path) == 70.0


def test_calibration_accepts_callable_model(monkeypatch):
    monkeypatch.setattr(calibration, "_load_calibrator", lambda path: lambda score: score + 7.0)
    assert calibration.calibrate_score(50.0) == 57.0


def test_calibration_failure_falls_back_to_identity(monkeypatch):
    monkeypatch.setattr(calibration, "_load_calibrator", lambda path: _BadModel())
    assert calibration.calibrate_score(64.0) == 64.0


def test_compute_risk_uses_calibrated_score_for_verdict(monkeypatch):
    monkeypatch.setattr(risk, "calibrate_score", lambda score: 82.0)

    result = risk.compute_risk(
        permissions=[],
        code=CodeInterpreterOutput(risk_level="LOW"),
        behavior=BehaviorAnalystOutput(risk_level="LOW"),
        intel=IntelCorrelatorOutput(),
        visual=VisualIntelOutput(),
        debate=None,
    )

    assert result.calibrated_score == 82.0
    assert result.verdict == "CRITICAL"
