"""Layer-B risk calibration.

The production calibrator is trained from corpus results and saved as a pickle.
Until that file exists, calibration remains identity. The loader accepts common
sklearn-style models with ``predict`` as well as simple callables, which keeps
unit fixtures tiny and lets the real isotonic model drop in later.
"""

from __future__ import annotations

import logging
import os
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = Path(__file__).with_name("model.pkl")
ENV_MODEL_PATH = "PARALLAX_CALIBRATION_MODEL"


def calibrate_score(evidence_score: float, model_path: str | Path | None = None) -> float:
    """Map Layer-A evidence score (0-100) to calibrated score (0-100)."""
    score = _clamp(evidence_score)
    model = _load_calibrator(str(_resolve_model_path(model_path)))
    if model is None:
        return score
    try:
        calibrated = _predict(model, score)
    except Exception as exc:
        logger.warning("Calibration model failed; using identity score: %s", exc)
        return score
    # Isotonic classifiers commonly return probability in 0-1. Store and return
    # the project-wide 0-100 risk scale.
    if 0.0 <= calibrated <= 1.0:
        calibrated *= 100.0
    return _clamp(calibrated)


def clear_calibration_cache() -> None:
    _load_calibrator.cache_clear()


def _resolve_model_path(model_path: str | Path | None = None) -> Path:
    if model_path is not None:
        return Path(model_path)
    env_path = os.getenv(ENV_MODEL_PATH)
    if env_path:
        return Path(env_path)
    return DEFAULT_MODEL_PATH


@lru_cache(maxsize=4)
def _load_calibrator(path: str) -> Any | None:
    model_path = Path(path)
    if not model_path.exists():
        return None
    with model_path.open("rb") as fh:
        return pickle.load(fh)


def _predict(model: Any, score: float) -> float:
    if hasattr(model, "predict"):
        prediction = model.predict([score])
    elif callable(model):
        prediction = model(score)
    else:
        raise TypeError("calibration model must be callable or expose predict()")

    if isinstance(prediction, (list, tuple)):
        return float(prediction[0])
    try:
        return float(prediction.item())  # numpy scalar / single-element array
    except AttributeError:
        return float(prediction)


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, float(value)))
