"""Train the Layer-B isotonic risk calibrator from corpus results.

The runtime calibrator loads a small JSON monotonic lookup table. This script
turns ``scripts/run_corpus.py`` CSV output into that table, while refusing to
train on tiny, one-class, or unusable datasets. It keeps the Phase 2 claim
honest: no model is written until there is enough labeled evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

MALICIOUS_VERDICTS = {"MALICIOUS"}
DEFAULT_MIN_SAMPLES = 200


@dataclass(frozen=True)
class CalibrationSample:
    score: float
    label: int


def load_samples(results_csv: Path) -> list[CalibrationSample]:
    samples: list[CalibrationSample] = []
    with results_csv.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            score_raw = (row.get("sys_score") or "").strip()
            verdict_raw = (row.get("true_verdict") or "").strip().upper()
            if not score_raw or verdict_raw not in {"MALICIOUS", "CLEAN"}:
                continue
            try:
                score = float(score_raw)
            except ValueError:
                continue
            samples.append(
                CalibrationSample(
                    score=max(0.0, min(100.0, score)),
                    label=1 if verdict_raw in MALICIOUS_VERDICTS else 0,
                )
            )
    return samples


def validate_samples(samples: list[CalibrationSample], *, min_samples: int) -> None:
    if len(samples) < min_samples:
        raise ValueError(
            f"need at least {min_samples} usable samples to train calibration; got {len(samples)}"
        )
    labels = {sample.label for sample in samples}
    if labels != {0, 1}:
        raise ValueError("calibration training requires both malicious and clean samples")


def fit_isotonic(samples: list[CalibrationSample]) -> list[tuple[float, float]]:
    """Fit an increasing isotonic probability curve with PAVA."""
    ordered = sorted(samples, key=lambda sample: sample.score)
    blocks = [
        {
            "min_x": sample.score,
            "max_x": sample.score,
            "sum_y": float(sample.label),
            "weight": 1.0,
        }
        for sample in ordered
    ]

    idx = 0
    while idx < len(blocks) - 1:
        left = blocks[idx]
        right = blocks[idx + 1]
        left_mean = left["sum_y"] / left["weight"]
        right_mean = right["sum_y"] / right["weight"]
        if left_mean <= right_mean:
            idx += 1
            continue

        merged = {
            "min_x": left["min_x"],
            "max_x": right["max_x"],
            "sum_y": left["sum_y"] + right["sum_y"],
            "weight": left["weight"] + right["weight"],
        }
        blocks[idx : idx + 2] = [merged]
        if idx:
            idx -= 1

    points: list[tuple[float, float]] = []
    for block in blocks:
        probability = block["sum_y"] / block["weight"]
        points.append((float(block["min_x"]), probability))
        if block["max_x"] != block["min_x"]:
            points.append((float(block["max_x"]), probability))
    return _dedupe_points(points)


def _dedupe_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    deduped: list[tuple[float, float]] = []
    for x, y in points:
        if deduped and deduped[-1][0] == x:
            deduped[-1] = (x, y)
        else:
            deduped.append((x, y))
    return deduped


def brier_score(samples: list[CalibrationSample], points: list[tuple[float, float]]) -> float:
    if not samples:
        return 0.0
    errors = []
    for sample in samples:
        probability = predict_probability(points, sample.score)
        errors.append((probability - sample.label) ** 2)
    return sum(errors) / len(errors)


def identity_brier_score(samples: list[CalibrationSample]) -> float:
    if not samples:
        return 0.0
    return sum(((sample.score / 100.0) - sample.label) ** 2 for sample in samples) / len(samples)


def predict_probability(points: list[tuple[float, float]], score: float) -> float:
    if score <= points[0][0]:
        return points[0][1]
    if score >= points[-1][0]:
        return points[-1][1]
    for (left_x, left_y), (right_x, right_y) in zip(points, points[1:], strict=False):
        if left_x <= score <= right_x:
            span = right_x - left_x
            if span <= 0:
                return right_y
            ratio = (score - left_x) / span
            return left_y + ratio * (right_y - left_y)
    return points[-1][1]


def write_model(
    model_path: Path,
    *,
    samples: list[CalibrationSample],
    points: list[tuple[float, float]],
) -> None:
    labels = {sample.label for sample in samples}
    payload = {
        "type": "isotonic_probability",
        "score_scale": "0-100",
        "prediction_scale": "0-1",
        "sample_count": len(samples),
        "malicious_count": sum(sample.label for sample in samples),
        "clean_count": sum(1 for sample in samples if sample.label == 0),
        "has_both_classes": labels == {0, 1},
        "brier": round(brier_score(samples, points), 6),
        "identity_brier": round(identity_brier_score(samples), 6),
        "points": [[round(x, 4), round(y, 6)] for x, y in points],
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("samples/results.csv"))
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("parallax/ai/calibration/model.json"),
        help="Output JSON model path used by PARALLAX_CALIBRATION_MODEL or the default loader.",
    )
    parser.add_argument("--min-samples", type=int, default=DEFAULT_MIN_SAMPLES)
    args = parser.parse_args()

    samples = load_samples(args.results)
    validate_samples(samples, min_samples=args.min_samples)
    points = fit_isotonic(samples)
    write_model(args.model, samples=samples, points=points)
    print(f"wrote calibration model -> {args.model}")
    print(f"samples={len(samples)} brier={brier_score(samples, points):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
