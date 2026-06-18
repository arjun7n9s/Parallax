"""Tests for the remaining-phase preflight helper."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "phase_preflight.py"
spec = importlib.util.spec_from_file_location("phase_preflight", SCRIPT)
phase_preflight = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules["phase_preflight"] = phase_preflight
spec.loader.exec_module(phase_preflight)


def test_env_key_check_reads_env_file_without_printing_value(tmp_path, monkeypatch):
    monkeypatch.delenv("MALWAREBAZAAR_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("MALWAREBAZAAR_API_KEY=secret-value\n", encoding="utf-8")

    check = phase_preflight.env_key_check("MALWAREBAZAAR_API_KEY", env_file=env_file)

    assert check.status == "ok"
    assert "secret-value" not in check.detail


def test_benign_corpus_check_requires_minimum_and_recurses(tmp_path):
    benign = tmp_path / "samples" / "benign" / "fdroid"
    benign.mkdir(parents=True)
    (benign / "clock.apk").write_bytes(b"apk")

    check = phase_preflight.benign_corpus_check(tmp_path / "samples" / "benign", min_benign=2)

    assert check.status == "blocked"
    assert "found 1" in check.detail


def test_render_markdown_escapes_pipe():
    report = phase_preflight.render_markdown(
        [phase_preflight.Check(name="x", status="ok", detail="a|b")]
    )

    assert "a\\|b" in report


def test_tool_check_finds_project_local_tools(tmp_path, monkeypatch):
    monkeypatch.setattr(phase_preflight.shutil, "which", lambda _tool: None)
    tool = tmp_path / "tools" / "helm" / "helm.exe"
    tool.parent.mkdir(parents=True)
    tool.write_bytes(b"exe")

    check = phase_preflight.tool_check("helm", search_roots=[tmp_path])

    assert check.status == "ok"
    assert check.detail == str(tool)


def test_docker_desktop_kvm_check_loads_and_verifies_modules(monkeypatch):
    monkeypatch.setattr(
        phase_preflight.shutil, "which", lambda tool: "wsl.exe" if tool == "wsl" else None
    )

    def fake_run(args, **kwargs):
        assert args[:3] == ["wsl.exe", "-d", "docker-desktop"]
        assert "modprobe kvm && modprobe kvm_intel && ls -la /dev/kvm" in args
        assert kwargs["timeout"] == 30
        return SimpleNamespace(
            returncode=0, stdout="crw------- 1 root root 10, 232 /dev/kvm\n", stderr=""
        )

    monkeypatch.setattr(phase_preflight.subprocess, "run", fake_run)

    check = phase_preflight.docker_desktop_kvm_check()

    assert check.status == "ok"
    assert "10, 232" in check.detail


def test_docker_desktop_kvm_check_blocks_when_device_is_missing(monkeypatch):
    monkeypatch.setattr(
        phase_preflight.shutil, "which", lambda tool: "wsl.exe" if tool == "wsl" else None
    )
    monkeypatch.setattr(
        phase_preflight.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="ls: /dev/kvm: No such file or directory",
        ),
    )

    check = phase_preflight.docker_desktop_kvm_check()

    assert check.status == "blocked"
    assert "No such file" in check.detail


def test_collect_checks_includes_core_blockers(tmp_path, monkeypatch):
    monkeypatch.setattr(
        phase_preflight,
        "tool_check",
        lambda tool, search_roots=None: phase_preflight._ok(tool, "ok"),
    )
    monkeypatch.setattr(phase_preflight, "kvm_check", lambda: phase_preflight._blocked("kvm", "no"))
    monkeypatch.setenv("MALWAREBAZAAR_API_KEY", "secret")
    (tmp_path / "deploy" / "helm" / "parallax").mkdir(parents=True)
    (tmp_path / "deploy" / "helm" / "parallax" / "Chart.yaml").write_text("apiVersion: v2\n")

    checks = phase_preflight.collect_checks(tmp_path, min_benign=20)
    names = {check.name for check in checks}

    assert "env:MALWAREBAZAAR_API_KEY" in names
    assert "corpus:benign_controls" in names
    assert "deploy:helm_chart" in names
    assert any(check.status == "blocked" for check in checks)
