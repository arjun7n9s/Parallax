"""Preflight remaining phase blockers without running destructive live tests.

This script records whether the current workstation has the external inputs
needed for the remaining proof gates: corpus validation, Android/KVM dynamic
analysis, Kubernetes rollout, and observability validation. It does not print
secret values and it does not download malware.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def _ok(name: str, detail: str) -> Check:
    return Check(name=name, status="ok", detail=detail)


def _blocked(name: str, detail: str) -> Check:
    return Check(name=name, status="blocked", detail=detail)


def _warn(name: str, detail: str) -> Check:
    return Check(name=name, status="warn", detail=detail)


def tool_check(tool: str, *, search_roots: list[Path] | None = None) -> Check:
    path = shutil.which(tool)
    if path:
        return _ok(f"tool:{tool}", path)
    local = _find_local_tool(tool, search_roots or [])
    if local:
        return _ok(f"tool:{tool}", str(local))
    return _blocked(f"tool:{tool}", f"{tool} not found on PATH")


def _find_local_tool(tool: str, search_roots: list[Path]) -> Path | None:
    names = [tool]
    if not tool.endswith(".exe"):
        names.append(f"{tool}.exe")
    roots: list[Path] = []
    for root in search_roots:
        roots.extend([root / "tools", root.parent / "tools"])
    for base in roots:
        if not base.exists():
            continue
        for name in names:
            matches = sorted(path for path in base.rglob(name) if path.is_file())
            if matches:
                return matches[0]
    return None


def env_key_check(key: str, *, env_file: Path | None = None) -> Check:
    if os.getenv(key):
        return _ok(f"env:{key}", "present in environment")
    if env_file and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(f"{key}=") and line.split("=", 1)[1].strip():
                return _ok(f"env:{key}", f"present in {env_file}")
    return _blocked(f"env:{key}", "missing")


def benign_corpus_check(path: Path, *, min_benign: int) -> Check:
    count = len(list(path.rglob("*.apk"))) if path.exists() else 0
    if count >= min_benign:
        return _ok("corpus:benign_controls", f"{count} APKs found under {path}")
    return _blocked(
        "corpus:benign_controls",
        f"need at least {min_benign} benign APKs under {path}; found {count}",
    )


def kvm_check() -> Check:
    if platform.system().lower() != "linux":
        return _blocked(
            "dynamic:kvm", f"KVM requires Linux host; current OS is {platform.system()}"
        )
    if Path("/dev/kvm").exists():
        return _ok("dynamic:kvm", "/dev/kvm is present")
    return _blocked("dynamic:kvm", "/dev/kvm is missing")


def sample_check(path: Path) -> Check:
    samples = sorted(path.glob("*.apk")) if path.exists() else []
    if samples:
        return _ok("dynamic:sample_apk", f"{len(samples)} APK sample(s) found under {path}")
    return _blocked("dynamic:sample_apk", f"no APK sample found under {path}")


def helm_chart_check(path: Path) -> Check:
    if path.exists():
        return _ok("deploy:helm_chart", str(path))
    return _blocked("deploy:helm_chart", f"{path} missing")


def collect_checks(root: Path, *, min_benign: int) -> list[Check]:
    env_file = root / ".env"
    tool_roots = [root]
    return [
        env_key_check("MALWAREBAZAAR_API_KEY", env_file=env_file),
        benign_corpus_check(root / "samples" / "benign", min_benign=min_benign),
        sample_check(root / "samples"),
        kvm_check(),
        tool_check("docker", search_roots=tool_roots),
        tool_check("adb", search_roots=tool_roots),
        tool_check("helm", search_roots=tool_roots),
        tool_check("kubectl", search_roots=tool_roots),
        helm_chart_check(root / "deploy" / "helm" / "parallax" / "Chart.yaml"),
    ]


def render_markdown(checks: list[Check]) -> str:
    lines = [
        "# PARALLAX Phase Preflight",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        detail = check.detail.replace("|", "\\|")
        lines.append(f"| `{check.name}` | {check.status} | {detail} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--min-benign", type=int, default=20)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    parser.add_argument("--strict", action="store_true", help="Exit 2 if any check is blocked")
    args = parser.parse_args()

    checks = collect_checks(args.root.resolve(), min_benign=args.min_benign)
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        print(render_markdown(checks))

    if args.strict and any(check.status == "blocked" for check in checks):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
