"""
Pytest configuration and shared fixtures for PARALLAX.
"""

import sys
import types
from unittest.mock import MagicMock

# Monkey-patch passlib to prevent ValueError from bcrypt>=4.0.0 at import time
sys.modules["passlib"] = MagicMock()
sys.modules["passlib.utils"] = MagicMock()
sys.modules["passlib.utils.compat"] = MagicMock()
sys.modules["passlib.registry"] = MagicMock()
sys.modules["passlib.apache"] = MagicMock()

# Monkey-patch heavy optional packages and their submodules.
# Production runs (with full .venv) have these installed and never hit this path.
# Tests that actually need these packages should be marked @pytest.mark.integration
# and skipped in the fast unit-test pipeline.
#
# We must create *real* module entries (not just MagicMock) for the parent module
# so that `from X.submodule import Y` resolves. Submodules are then mocked.
_OPTIONAL_PACKAGES = {
    "frida": [
        "frida.core",
        "frida.core.Device",
        "frida.TimedOutError",
        "frida.ServerNotRunningError",
        "frida.ExecutableNotFoundError",
    ],
    "androguard": [
        "androguard.core",
        "androguard.core.apk",
        "androguard.core.dex",
        "androguard.core.analysis",
        "androguard.misc",
        "androguard.misc.AnalyzeAPK",
    ],
    "mitmproxy": [
        "mitmproxy.options",
        "mitmproxy.tools.dump",
        "mitmproxy.http",
        "mitmproxy.http.HTTPFlow",
    ],
    "celery": ["celery", "celery.Celery", "celery.Task", "celery.shared_task"],
    "yara": ["yara"],
}

for _pkg_name, _submodules in _OPTIONAL_PACKAGES.items():
    try:
        __import__(_pkg_name)
    except ImportError:
        if _pkg_name not in sys.modules:
            _pkg = types.ModuleType(_pkg_name)
            _pkg.__path__ = []  # Mark as a package so submodule imports work
            sys.modules[_pkg_name] = _pkg
        for _submod in _submodules:
            if _submod not in sys.modules:
                sys.modules[_submod] = MagicMock()

# Patch the top-level mock modules to expose attributes used in type annotations
# (e.g. `yara.Rules | None`, `celery.Celery`). MagicMock returns a child MagicMock
# on attribute access, so the union syntax evaluates successfully.
for _attr_module in ("yara", "celery", "frida", "androguard", "mitmproxy"):
    _mod = sys.modules.get(_attr_module)
    if _mod is not None and not hasattr(_mod, "__path__"):
        continue
    # Real package — leave alone. The submodule mocks above handle attribute lookup
    # via from-import. For type-annotation-only references on the top-level
    # module (rare), explicitly expose them:
    if _attr_module == "yara" and hasattr(_mod, "__path__"):
        _mod.Rules = MagicMock
        _mod.SyntaxError = type("SyntaxError", (Exception,), {})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from parallax.api.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    """Returns a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def _disable_heartbeat(monkeypatch):
    """Unit tests must never start the Redis heartbeat thread, regardless of the
    ambient .env. Tests that exercise the heartbeat re-enable it explicitly."""
    from parallax.core.config import settings

    monkeypatch.setattr(settings, "HEARTBEAT_ENABLED", False, raising=False)
