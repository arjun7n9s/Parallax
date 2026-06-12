"""Select the most security-relevant decompiled code for the Code Interpreter.

A real APK decompiles to thousands of Java files — far more than any model
context can hold. Rather than truncating arbitrarily, we rank files by how many
sensitive-API signals they contain and feed only the top files (each truncated)
to the LLM. This keeps the agent grounded in the code that actually matters.
"""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

# Sensitive API / keyword signals, weighted by how indicative each is of
# banking-malware behavior. Matched case-sensitively against decompiled Java.
SIGNAL_WEIGHTS: dict[str, int] = {
    "AccessibilityService": 5,
    "AccessibilityEvent": 3,
    "SYSTEM_ALERT_WINDOW": 5,
    "TYPE_APPLICATION_OVERLAY": 5,
    "addView": 2,
    "SmsManager": 5,
    "SmsMessage": 4,
    "getMessageBody": 4,
    "createFromPdu": 4,
    "RECEIVE_SMS": 3,
    "sendTextMessage": 4,
    "DexClassLoader": 5,
    "DexFile": 3,
    "loadDex": 3,
    "HttpURLConnection": 2,
    "OkHttpClient": 2,
    "okhttp3": 2,
    "Cipher.getInstance": 3,
    "SecretKeySpec": 3,
    "Base64": 1,
    "WebView": 2,
    "addJavascriptInterface": 4,
    "loadUrl": 2,
    "getDeviceId": 3,
    "getSubscriberId": 3,
    "DevicePolicyManager": 4,
    "Runtime.getRuntime().exec": 4,
    "ProcessBuilder": 3,
    "getInstalledApplications": 3,
    "KeyguardManager": 2,
    "NotificationListenerService": 4,
}

_HOST_RE = re.compile(r"https?://[A-Za-z0-9.\-:/_%?=&]+")

# Decompiled framework/library packages carry no app-specific intent and bloat
# the scan (a real APK decompiles to thousands of these). Skipping them makes
# selection both faster and more focused on the app's own code.
_SKIP_DIR_PARTS = (
    "/android/", "/androidx/", "/kotlin/", "/kotlinx/", "/java/", "/javax/",
    "/com/google/android/gms/", "/com/google/android/material/",
    "/com/google/common/", "/com/google/protobuf/", "/com/google/firebase/",
    "/org/apache/", "/org/json/", "/okhttp3/internal/", "/okio/", "/retrofit2/",
    "/dagger/", "/io/reactivex/", "/com/squareup/", "/com/bumptech/glide/",
)
_MAX_FILES_SCANNED = 4000


def score_text(text: str) -> tuple[int, list[str]]:
    """Return (score, matched-signal names) for a chunk of source text."""
    score = 0
    matched: list[str] = []
    for signal, weight in SIGNAL_WEIGHTS.items():
        if signal in text:
            score += weight
            matched.append(signal)
    return score, matched


def select_relevant_code(
    sources_dir: str,
    max_files: int = 8,
    max_chars_per_file: int = 3500,
    total_char_budget: int = 22000,
) -> tuple[str, list[str], list[str]]:
    """Walk decompiled sources and select the most relevant files.

    Returns ``(concatenated_code, selected_relative_paths, hardcoded_urls)``.
    ``sources_dir`` may be the jadx output dir or its ``sources`` subdir.
    """
    if not sources_dir or not os.path.isdir(sources_dir):
        # jadx writes to <out>/sources; accept either.
        candidate = os.path.join(sources_dir or "", "sources")
        if os.path.isdir(candidate):
            sources_dir = candidate
        else:
            return "", [], []

    scored: list[tuple[int, str, str, list[str]]] = []
    urls: set[str] = set()
    scanned = 0

    for root, _, files in os.walk(sources_dir):
        norm = root.replace("\\", "/")
        if any(part in norm + "/" for part in _SKIP_DIR_PARTS):
            continue
        for fname in files:
            if not fname.endswith(".java"):
                continue
            if scanned >= _MAX_FILES_SCANNED:
                break
            scanned += 1
            path = os.path.join(root, fname)
            try:
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            score, matched = score_text(text)
            for m in _HOST_RE.findall(text):
                urls.add(m)
            if score > 0:
                rel = os.path.relpath(path, sources_dir)
                scored.append((score, rel, text, matched))

    scored.sort(key=lambda t: t[0], reverse=True)

    chosen: list[str] = []
    blocks: list[str] = []
    used = 0
    for score, rel, text, matched in scored[:max_files]:
        snippet = text[:max_chars_per_file]
        if used + len(snippet) > total_char_budget:
            break
        used += len(snippet)
        chosen.append(rel)
        header = f"// FILE: {rel}  (signals: {', '.join(matched)})\n"
        blocks.append(header + snippet)

    return "\n\n".join(blocks), chosen, sorted(urls)
