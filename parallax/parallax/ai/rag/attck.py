"""MITRE ATT&CK Mobile retrieval for the Intel Correlator.

A curated catalog of ATT&CK Mobile techniques relevant to banking malware is
embedded with the local embedding model on first use and cached. Given a free-
text query (behavior + code summary) we return the top-k candidate techniques by
cosine similarity. This keeps the correlator grounded in real technique IDs
instead of letting the LLM invent them.

The catalog is intentionally a high-value subset (not the full ATT&CK corpus);
the full STIX bundle can be ingested into Qdrant in Phase 5 for breadth.
"""

from __future__ import annotations

import logging
import math

from parallax.ai.llm import llm

logger = logging.getLogger(__name__)

# (technique_id, name, description) — real ATT&CK Mobile techniques.
ATTCK_MOBILE: list[tuple[str, str, str]] = [
    (
        "T1417.001",
        "Input Capture: Keylogging",
        "Log keystrokes to capture credentials and sensitive input.",
    ),
    (
        "T1417.002",
        "Input Capture: GUI Input Capture",
        "Mimic or overlay UI to capture user-entered credentials.",
    ),
    ("T1516", "Input Injection", "Inject input events to interact with the UI without the user."),
    (
        "T1437.001",
        "Application Layer Protocol: Web Protocols",
        "Use HTTP/HTTPS for command and control or exfiltration.",
    ),
    (
        "T1521.001",
        "Encrypted Channel: Symmetric Cryptography",
        "Encrypt C2 traffic with symmetric keys.",
    ),
    ("T1582", "SMS Control", "Send, intercept, or delete SMS messages, e.g. to capture OTPs."),
    ("T1636.003", "Protected User Data: SMS Messages", "Collect SMS messages from the device."),
    ("T1636.004", "Protected User Data: Contacts", "Collect the device contact list."),
    (
        "T1626.001",
        "Abuse Elevation Control: Device Administrator",
        "Request device admin to gain elevated control and resist removal.",
    ),
    (
        "T1407",
        "Download New Code at Runtime",
        "Fetch and execute additional code (DexClassLoader) after install.",
    ),
    (
        "T1623.001",
        "Command and Scripting Interpreter: Unix Shell",
        "Execute shell commands via Runtime.exec/ProcessBuilder.",
    ),
    (
        "T1646",
        "Exfiltration Over C2 Channel",
        "Exfiltrate collected data over the existing C2 channel.",
    ),
    ("T1513", "Screen Capture", "Capture the device screen content."),
    ("T1430", "Location Tracking", "Track the device's geographic location."),
    (
        "T1426",
        "System Information Discovery",
        "Collect device identifiers (IMEI, IMSI, model, OS).",
    ),
    (
        "T1418",
        "Software Discovery",
        "Enumerate installed applications, e.g. to find target bank apps.",
    ),
    (
        "T1624.001",
        "Event Triggered Execution: Broadcast Receivers",
        "Register receivers (e.g. BOOT_COMPLETED, SMS_RECEIVED) to trigger code.",
    ),
    (
        "T1406",
        "Obfuscated Files or Information",
        "Obfuscate/pack code and encrypt strings to evade analysis.",
    ),
    ("T1541", "Foreground Persistence", "Run a persistent foreground service to stay alive."),
    (
        "T1655.001",
        "Masquerading: Match Legitimate Name or Location",
        "Impersonate a legitimate (bank) app's name, icon, or UI.",
    ),
    (
        "T1632.001",
        "Subvert Trust Controls: Code Signing Policy Modification",
        "Modify trust controls, e.g. install attacker CA certificates.",
    ),
    ("T1640", "Account Access Removal", "Lock the user out or remove account access."),
    ("T1429", "Audio Capture", "Record audio via the microphone."),
    ("T1512", "Video Capture", "Capture video/photos via the camera."),
    ("T1644", "Out of Band Data", "Use an out-of-band channel (SMS) for C2."),
    ("T1623", "Command and Scripting Interpreter", "Execute commands received from C2."),
    ("T1409", "Stored Application Data", "Access data stored by other applications."),
    (
        "T1422",
        "System Network Configuration Discovery",
        "Discover network configuration and connectivity.",
    ),
]

_catalog_vectors: list[list[float]] | None = None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


async def _ensure_catalog_embedded() -> list[list[float]]:
    global _catalog_vectors
    if _catalog_vectors is None:
        texts = [f"{name}. {desc}" for _, name, desc in ATTCK_MOBILE]
        _catalog_vectors = await llm.embed(texts)
    return _catalog_vectors


async def retrieve_techniques(query: str, top_k: int = 8) -> list[dict]:
    """Return the top-k candidate ATT&CK techniques for a free-text query."""
    if not query.strip():
        return []
    try:
        vectors = await _ensure_catalog_embedded()
        qvec = (await llm.embed([query]))[0]
    except Exception as exc:  # embedding backend unavailable
        logger.warning("ATT&CK retrieval embedding failed: %s", exc)
        return []
    scored = [
        (
            _cosine(qvec, vectors[i]),
            ATTCK_MOBILE[i][0],
            ATTCK_MOBILE[i][1],
            ATTCK_MOBILE[i][2],
        )
        for i in range(len(ATTCK_MOBILE))
    ]
    scored.sort(key=lambda t: t[0], reverse=True)
    return [
        {"technique_id": tid, "name": name, "description": desc, "score": round(score, 3)}
        for score, tid, name, desc in scored[:top_k]
    ]
