# Validation and Calibration

PARALLAX treats corpus validation as an evidence gate, not a marketing number. Accuracy, Brier score, calibrated risk, case studies, and cost-per-sample claims should only be published from a reproducible corpus run with at least 200 usable samples.

## Build the corpus

Malware samples come from MalwareBazaar. Benign controls come from a local APK directory so the corpus remains explicit and auditable.

```bash
export MALWAREBAZAAR_API_KEY=...
python scripts/build_corpus.py \
  --benign-dir samples/benign \
  --benign-limit 20 \
  --out-dir samples/corpus \
  --manifest samples/corpus.jsonl
```

Use `--dry-run` to validate family selection and manifest writing without downloading APK payloads.

For a publishable validation run, use the readiness gate before downloads:

```bash
python scripts/build_corpus.py \
  --dry-run \
  --benign-dir samples/benign \
  --benign-limit 20 \
  --manifest samples/corpus_preflight.jsonl \
  --min-total 200 \
  --require-benign
```

`--require-benign` requires the full `--benign-limit` count. Use `--min-benign` if you intentionally want a different gate. If this fails, do not publish validation claims. Add benign controls, adjust family targets, or expand MalwareBazaar tags until the preflight passes.

The default malware mix intentionally over-targets the 200-sample gate because public tag availability changes over time. Keep the final report tied to the manifest that was actually selected, not to the requested target counts.

## Run validation

The harness is resumable. It writes rows after each sample, so interrupted long runs can continue safely.

```bash
python scripts/run_corpus.py \
  --manifest samples/corpus.jsonl \
  --results samples/results.csv \
  --report ../Claude/validation_report.md \
  --resume
```

The generated report marks the run as provisional until it has at least 200 usable pipeline results. Treat all smaller runs as smoke tests only.

## Train Layer-B calibration

Train the isotonic calibration model only after the validation CSV has enough usable, mixed-class rows.

```bash
python scripts/train_calibration.py \
  --results samples/results.csv \
  --model parallax/ai/calibration/model.json
```

The trainer refuses undersized or one-class data. The model JSON includes sample counts, class counts, Brier score, identity Brier score, and the monotonic lookup points loaded by the runtime calibrator.

## Publish criteria

Before updating the whitepaper or case studies with numbers, verify:

- `samples/results.csv` has at least 200 usable rows.
- Both malicious and clean labels are present.
- The validation report says `Evidence gate met (N>=200 usable): yes`.
- `scripts/train_calibration.py` writes a model with `has_both_classes: true`.
- The trained model Brier score is no worse than identity Brier.
- The exact manifest, results CSV, report, model metadata, and PARALLAX commit SHA are archived together.
