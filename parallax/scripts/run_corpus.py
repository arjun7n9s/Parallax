"""Run a labeled corpus through PARALLAX and summarize validation metrics.

Reads ``samples/corpus.jsonl`` produced by ``scripts/build_corpus.py``, runs each
APK through ``scripts/run_pipeline.py``, writes ``samples/results.csv``, and
renders a markdown report suitable for ``Claude/validation_report.md``.

The harness is intentionally file-based and resumable: if a SHA256 already has
a row in the results CSV, ``--resume`` skips it.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

RESULT_FIELDS = [
    "sha256",
    "true_family",
    "true_verdict",
    "sys_verdict",
    "sys_family",
    "sys_family_confidence",
    "sys_score",
    "latency_s",
    "cost_usd",
    "match",
    "status",
    "error",
]

MALICIOUS_VERDICTS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


@dataclass(frozen=True)
class CorpusItem:
    sha256: str
    true_family: str
    true_verdict: str
    path: str


def load_manifest(path: Path) -> list[CorpusItem]:
    items: list[CorpusItem] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        try:
            items.append(
                CorpusItem(
                    sha256=row["sha256"],
                    true_family=row["family"],
                    true_verdict=row["true_verdict"],
                    path=row["path"],
                )
            )
        except KeyError as exc:
            raise ValueError(f"{path}:{lineno} missing required field {exc.args[0]!r}") from exc
    return items


def read_existing_results(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        return {row["sha256"]: row for row in csv.DictReader(fh)}


def write_results(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in RESULT_FIELDS})


def parse_pipeline_output(text: str) -> dict[str, str]:
    """Extract the stable literal fields printed by scripts/run_pipeline.py."""

    def field(name: str) -> str:
        match = re.search(rf"^{re.escape(name)}\s*:\s*(.+)$", text, re.MULTILINE)
        return match.group(1).strip() if match else ""

    family_line = field("family_attribution")
    family = ""
    family_conf = ""
    if family_line:
        family_match = re.match(r"'?([^'()]+)'?\s*\(confidence\s+([^)]*)\)", family_line)
        if family_match:
            family = family_match.group(1).strip()
            family_conf = family_match.group(2).strip()
        else:
            family = family_line.strip("' ")

    return {
        "status": field("status"),
        "sys_verdict": field("verdict"),
        "sys_score": field("final_score"),
        "sys_family": "" if family in {"None", "null"} else family,
        "sys_family_confidence": family_conf,
    }


def run_one(item: CorpusItem, *, timeout_s: int, python: str) -> dict:
    start = time.monotonic()
    env = dict(os.environ)
    env["PYTHONPATH"] = env.get("PYTHONPATH") or "."
    try:
        proc = subprocess.run(
            [python, "scripts/run_pipeline.py", item.path],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        latency = time.monotonic() - start
        parsed = parse_pipeline_output(proc.stdout)
        error = "" if proc.returncode == 0 else (proc.stderr or proc.stdout)[-1000:]
        return make_result_row(item, parsed, latency_s=latency, error=error)
    except Exception as exc:  # noqa: BLE001 - one bad sample must not kill corpus run
        latency = time.monotonic() - start
        return make_result_row(item, {}, latency_s=latency, error=f"{type(exc).__name__}: {exc}")


def _malicious(verdict: str) -> bool:
    return verdict.upper() in MALICIOUS_VERDICTS


def make_result_row(
    item: CorpusItem, parsed: dict[str, str], *, latency_s: float, error: str = ""
) -> dict:
    sys_family = parsed.get("sys_family", "")
    true_family = item.true_family
    family_match = (
        true_family.lower() == sys_family.lower()
        if true_family.lower() != "benign"
        else not sys_family
    )
    return {
        "sha256": item.sha256,
        "true_family": true_family,
        "true_verdict": item.true_verdict,
        "sys_verdict": parsed.get("sys_verdict", ""),
        "sys_family": sys_family,
        "sys_family_confidence": parsed.get("sys_family_confidence", ""),
        "sys_score": parsed.get("sys_score", ""),
        "latency_s": f"{latency_s:.1f}",
        "cost_usd": "",  # Phase 4.5 wires token/model pricing into this field.
        "match": "true" if family_match else "false",
        "status": parsed.get("status", ""),
        "error": error,
    }


def compute_metrics(rows: list[dict]) -> dict[str, float | int]:
    usable = [r for r in rows if r.get("sys_verdict")]
    if not usable:
        return {"samples": len(rows), "usable": 0}

    fam_rows = [r for r in usable if r.get("true_family", "").lower() != "benign"]
    family_top1 = (
        sum(1 for r in fam_rows if r.get("match") == "true") / len(fam_rows) if fam_rows else 0.0
    )

    tp = fp = tn = fn = 0
    for row in usable:
        truth = row.get("true_verdict") == "MALICIOUS"
        pred = _malicious(row.get("sys_verdict", ""))
        if truth and pred:
            tp += 1
        elif truth and not pred:
            fn += 1
        elif not truth and pred:
            fp += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    latencies = sorted(float(r["latency_s"]) for r in usable if r.get("latency_s"))
    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)
    brier_scores = _brier_score(rows)
    return {
        "samples": len(rows),
        "usable": len(usable),
        "validation_ready": len(usable) >= 200,
        "family_top1": family_top1,
        "verdict_precision": precision,
        "verdict_recall": recall,
        "verdict_f1": f1,
        "brier": brier_scores,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "latency_p50_s": p50,
        "latency_p95_s": p95,
        "latency_p99_s": p99,
    }


def _brier_score(rows: list[dict]) -> float:
    errors: list[float] = []
    for row in rows:
        if row.get("true_verdict") not in {"MALICIOUS", "CLEAN"}:
            continue
        try:
            probability = max(0.0, min(100.0, float(row.get("sys_score", "")))) / 100.0
        except ValueError:
            continue
        label = 1.0 if row["true_verdict"] == "MALICIOUS" else 0.0
        errors.append((probability - label) ** 2)
    return sum(errors) / len(errors) if errors else 0.0


def percentile(values: list[float], pct: int) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    rank = (pct / 100) * (len(values) - 1)
    low = int(rank)
    high = min(low + 1, len(values) - 1)
    frac = rank - low
    return round(values[low] * (1 - frac) + values[high] * frac, 2)


def render_report(rows: list[dict], metrics: dict[str, float | int]) -> str:
    ready = bool(metrics.get("validation_ready", 0))
    evidence_status = (
        "REPRODUCIBLE VALIDATION RUN"
        if ready
        else "PROVISIONAL ONLY - fewer than 200 usable samples"
    )
    lines = [
        "# PARALLAX Validation Report",
        "",
        f"> Evidence status: **{evidence_status}**.",
        "",
        "## Summary",
        "",
        f"- Samples in CSV: {metrics.get('samples', 0)}",
        f"- Usable pipeline results: {metrics.get('usable', 0)}",
        f"- Evidence gate met (N>=200 usable): {'yes' if ready else 'no'}",
        f"- Family top-1 accuracy: {metrics.get('family_top1', 0.0):.3f}",
        f"- Verdict precision: {metrics.get('verdict_precision', 0.0):.3f}",
        f"- Verdict recall: {metrics.get('verdict_recall', 0.0):.3f}",
        f"- Verdict F1: {metrics.get('verdict_f1', 0.0):.3f}",
        f"- Brier score: {metrics.get('brier', 0.0):.3f}",
        f"- Latency p50/p95/p99: {metrics.get('latency_p50_s', 0.0)}s / "
        f"{metrics.get('latency_p95_s', 0.0)}s / {metrics.get('latency_p99_s', 0.0)}s",
        "",
        "## Confusion Matrix",
        "",
        "| | Pred malicious | Pred clean |",
        "|---|---:|---:|",
        f"| True malicious | {metrics.get('tp', 0)} | {metrics.get('fn', 0)} |",
        f"| True clean | {metrics.get('fp', 0)} | {metrics.get('tn', 0)} |",
        "",
        "## Accuracy Table",
        "",
        "| sha256 | true_family | true_verdict | sys_verdict | sys_family | score | match |",
        "|---|---|---|---|---|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {sha256} | {true_family} | {true_verdict} | {sys_verdict} | "
            "{sys_family} | {sys_score} | {match} |".format(**row)
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("samples/corpus.jsonl"))
    parser.add_argument("--results", type=Path, default=Path("samples/results.csv"))
    parser.add_argument("--report", type=Path, default=Path("../Claude/validation_report.md"))
    parser.add_argument("--timeout-s", type=int, default=1800)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    items = load_manifest(args.manifest)
    if args.limit:
        items = items[: args.limit]

    existing = read_existing_results(args.results) if args.resume else {}
    rows: list[dict] = list(existing.values())
    seen = set(existing)
    for item in items:
        if item.sha256 in seen:
            print(f"skip existing {item.sha256}")
            continue
        print(f"run {item.sha256} {item.true_family} -> {item.path}")
        row = run_one(item, timeout_s=args.timeout_s, python=args.python)
        rows.append(row)
        seen.add(item.sha256)
        write_results(args.results, rows)

    metrics = compute_metrics(rows)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(rows, metrics), encoding="utf-8")
    print(f"wrote {args.results}")
    print(f"wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
