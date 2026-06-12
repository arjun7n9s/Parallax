"""Auto-generate a YARA rule from an analysis.

Builds a rule from the most distinctive strings observed for a sample (C2
domains/URLs, package name, suspicious class names), filtering out common
Android framework strings to keep false positives low. The generated rule is
compiled to validate it before it is returned, and namespaced ``PARALLAX_AUTO_``
so it never shadows curated rules.
"""

from __future__ import annotations

import logging
import re

from parallax.ai.schemas import CortexResult

logger = logging.getLogger(__name__)

# Strings too generic to anchor a rule on.
_COMMON = {
    "android",
    "com.google",
    "androidx",
    "kotlin",
    "java.lang",
    "http://schemas.android.com",
    "google.com",
    "gstatic.com",
    "googleapis.com",
    "play.google.com",
}

_CLEAN_RE = re.compile(r"^[\w./:\-]+$")


def _distinctive_strings(package: str, cortex: CortexResult) -> list[str]:
    candidates: list[str] = []
    if package and not any(c in package for c in _COMMON):
        candidates.append(package)
    for dom in cortex.iocs.get("domains", []):
        if not any(c in dom for c in _COMMON):
            candidates.append(dom)
    for url in cortex.iocs.get("urls", []):
        if not any(c in url for c in _COMMON):
            candidates.append(url)
    code = cortex.code_interpreter
    if code:
        for cr in code.class_roles:
            name = cr.class_name
            if name and not any(c in name for c in _COMMON) and "." in name:
                candidates.append(name)
    # De-dup, keep clean ascii-ish strings of useful length.
    seen: set[str] = set()
    out: list[str] = []
    for s in candidates:
        s = s.strip()
        if 6 <= len(s) <= 120 and _CLEAN_RE.match(s) and s not in seen:
            seen.add(s)
            out.append(s)
    return out[:12]


def generate_yara_rule(sha256: str, package: str, cortex: CortexResult, date: str) -> str | None:
    """Generate and validate a YARA rule. Returns the rule text, or None."""
    strings = _distinctive_strings(package, cortex)
    if len(strings) < 2:
        logger.info("Not enough distinctive strings for a YARA rule (%s).", sha256)
        return None

    rule_name = f"PARALLAX_AUTO_{sha256[:8]}"
    lines = [f"rule {rule_name} {{", "    meta:"]
    lines.append('        author = "parallax"')
    lines.append(f'        sha256 = "{sha256}"')
    lines.append(f'        verdict = "{cortex.verdict}"')
    lines.append(f'        date = "{date}"')
    if cortex.intel_correlator and cortex.intel_correlator.family_attribution:
        lines.append(f'        family = "{cortex.intel_correlator.family_attribution}"')
    lines.append("    strings:")
    for i, s in enumerate(strings):
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'        $s{i} = "{escaped}" ascii wide')
    # Require a meaningful subset to match to reduce false positives.
    threshold = max(2, len(strings) // 2)
    lines.append("    condition:")
    lines.append(f"        {threshold} of them")
    lines.append("}")
    rule_text = "\n".join(lines)

    # Validate it compiles.
    try:
        import yara

        yara.compile(source=rule_text)
    except Exception as exc:
        logger.warning("Generated YARA rule failed to compile (%s): %s", sha256, exc)
        return None
    return rule_text
