# PARALLAX — Deferred Fixes & Future Issues

> Living document. Add items here as they're identified during the build.
> Review periodically before each phase gate.

---

## Deferred from Foundation Audit (2026-06-08)

| # | Issue | Priority | Phase Needed By | Notes |
|---|---|---|---|---|
| 1 | **Add rate limiting** to API endpoints (e.g. `slowapi`) | Low | V2-3 (before dynamic pipeline goes live) | A security product should protect itself. Not blocking Phase 1 since it's internal-only during dev. |
| 2 | **Populate docs with real content** — `docs/api/`, `docs/architecture/`, `docs/runbooks/` are stubs | Low | V2-9 (integration/hardening) | Incremental — flesh out as modules are built. Copy PSBs to `docs/architecture/` as a quick win. |

---

## Identified During Build

_Add new items below as they come up._

| # | Issue | Priority | Phase Needed By | Notes |
|---|---|---|---|---|
| | | | | |

---

## Resolved

| # | Issue | Resolved In | Commit |
|---|---|---|---|
| — | ForeignKey constraints missing | Batch 1 | `406d21c` |
| — | Temp file leak in analyze.py | Batch 1 | `406d21c` |
| — | No upload size limit / magic byte check | Batch 1 | `406d21c` |
| — | `.gitignore` null byte corruption | Batch 1 | `406d21c` |
| — | CORS wildcard `*` | Batch 1 | `406d21c` |
| — | No OpenTelemetry instrumentation | Batch 2 | `b828bfd` |
| — | No Qdrant init script | Batch 2 | `b828bfd` |
| — | No X-Request-ID correlation | Batch 2 | `b828bfd` |
| — | storage.py eager init crashes on import | Batch 2 | `b828bfd` |
| — | Scattered `import os` in analyze.py | Batch 2 | `b828bfd` |
| — | Duplicate test fixture in test_analyze.py | Batch 2 | `b828bfd` |
| — | No mypy in CI / pre-commit | Batch 3 | `b828bfd` |
| — | No bandit security scan in CI | Batch 3 | `b828bfd` |
| — | No Docker analysis_net isolation | Batch 3 | `b828bfd` |
| — | Missing history/pagination endpoint | Batch 3 | `b828bfd` |
