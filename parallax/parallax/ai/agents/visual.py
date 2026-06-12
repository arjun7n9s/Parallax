"""Visual Intelligence agent — phishing/overlay detection over screenshots."""

from __future__ import annotations

import base64
import logging

from parallax.ai.llm import llm
from parallax.ai.prompts.cortex import VISUAL_SYSTEM
from parallax.ai.schemas import ScreenshotFinding, VisualIntelOutput
from parallax.core.storage import SCREENSHOTS_BUCKET, get_minio_client

logger = logging.getLogger(__name__)

_MAX_SCREENSHOTS = 12


def _fetch_png_b64(key: str) -> str | None:
    """Fetch a screenshot from MinIO and return base64-encoded PNG bytes."""
    client = get_minio_client()
    resp = None
    try:
        resp = client.get_object(SCREENSHOTS_BUCKET, key)
        data = resp.read()
        return base64.b64encode(data).decode("ascii")
    except Exception as exc:
        logger.warning("Could not fetch screenshot %s: %s", key, exc)
        return None
    finally:
        if resp is not None:
            resp.close()
            resp.release_conn()


async def _analyze_one(key: str, b64: str) -> ScreenshotFinding:
    raw = await llm.complete_json(
        "visual",
        "Analyze this Android screenshot for phishing or brand-impersonation overlay.",
        VISUAL_SYSTEM,
        images=[b64],
    )
    finding = ScreenshotFinding.model_validate(raw)
    finding.screenshot_key = key
    return finding


async def run_visual_intelligence(screenshot_keys: list[str]) -> VisualIntelOutput:
    """Analyze captured screenshots and aggregate a brand-impersonation verdict.

    ``screenshot_keys`` are MinIO object keys in the screenshots bucket.
    """
    out = VisualIntelOutput()
    if not screenshot_keys:
        return out

    findings: list[ScreenshotFinding] = []
    for key in screenshot_keys[:_MAX_SCREENSHOTS]:
        b64 = _fetch_png_b64(key)
        if not b64:
            continue
        try:
            findings.append(await _analyze_one(key, b64))
        except Exception as exc:
            logger.warning("Visual analysis failed for %s: %s", key, exc)

    out.findings = findings
    if findings:
        best = max(findings, key=lambda f: f.brand_similarity_score)
        out.brand_impersonation = best.brand_detected
        out.brand_impersonation_score = best.brand_similarity_score
        out.phishing_detected = any(f.is_phishing for f in findings)
        out.overlay_attack_detected = any(f.overlay_detected for f in findings)
        out.confidence = max((f.brand_similarity_score for f in findings), default=0.0)
    return out
