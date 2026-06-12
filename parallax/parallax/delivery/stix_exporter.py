"""STIX 2.1 bundle export for MISP / OpenCTI / SIEM interoperability."""

from __future__ import annotations

import logging

from parallax.ai.schemas import CortexResult

logger = logging.getLogger(__name__)


def build_stix_bundle(sha256: str, package: str, cortex: CortexResult) -> dict:
    """Build a STIX 2.1 bundle for one analysis. Returns the bundle as a dict."""
    try:
        import stix2
    except ImportError:
        logger.warning("stix2 not installed; returning minimal bundle.")
        return {"type": "bundle", "objects": []}

    objects: list = []

    malware = stix2.Malware(
        name=f"{package or sha256[:12]}",
        is_family=False,
        malware_types=["trojan"],
        description=cortex.executive_summary or f"PARALLAX verdict: {cortex.verdict}",
    )
    objects.append(malware)

    file_obj = stix2.File(
        name=f"{package or sha256}.apk",
        hashes={"SHA-256": sha256},
    )
    objects.append(file_obj)

    # Indicators for network IOCs.
    patterns: list[tuple[str, str]] = []
    for dom in cortex.iocs.get("domains", []):
        patterns.append((f"[domain-name:value = '{dom}']", f"C2 domain {dom}"))
    for ip in cortex.iocs.get("ips", []):
        patterns.append((f"[ipv4-addr:value = '{ip}']", f"C2 IP {ip}"))
    for url in cortex.iocs.get("urls", []):
        safe = url.replace("'", "")
        patterns.append((f"[url:value = '{safe}']", f"C2 URL {url}"))

    for pattern, desc in patterns:
        try:
            ind = stix2.Indicator(
                name=desc,
                pattern=pattern,
                pattern_type="stix",
                valid_from="2020-01-01T00:00:00Z",
            )
            objects.append(ind)
            objects.append(
                stix2.Relationship(
                    relationship_type="indicates", source_ref=ind.id, target_ref=malware.id
                )
            )
        except Exception as exc:
            logger.debug("Skipping malformed indicator %s: %s", pattern, exc)

    # Attack patterns from ATT&CK techniques.
    for tid in cortex.attck_techniques:
        ap = stix2.AttackPattern(
            name=tid,
            external_references=[
                {"source_name": "mitre-attack", "external_id": tid}
            ],
        )
        objects.append(ap)
        objects.append(
            stix2.Relationship(
                relationship_type="uses", source_ref=malware.id, target_ref=ap.id
            )
        )

    bundle = stix2.Bundle(objects=objects, allow_custom=True)
    return bundle.serialize() if hasattr(bundle, "serialize") else dict(bundle)


def build_stix_json(sha256: str, package: str, cortex: CortexResult) -> str:
    """Return the bundle as a JSON string."""
    import json

    result = build_stix_bundle(sha256, package, cortex)
    if isinstance(result, str):
        return result
    return json.dumps(result, indent=2)
