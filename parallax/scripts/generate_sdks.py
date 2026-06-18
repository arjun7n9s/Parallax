"""Generate SDKs from the committed OpenAPI schema.

The script is intentionally thin: CI can verify the spec exists without pulling
large generator toolchains, while release builds can install the CLIs and run:

  python scripts/generate_sdks.py --python --typescript
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

OPENAPI = Path(__file__).resolve().parents[1] / "parallax" / "api" / "openapi.json"
SDK_DIR = Path(__file__).resolve().parents[1] / "sdks"


def _require(binary: str) -> str:
    found = shutil.which(binary)
    if not found:
        raise SystemExit(
            f"Missing '{binary}'. Install the generator first, then rerun this script."
        )
    return found


def generate_python() -> None:
    generator = _require("openapi-python-client")
    out = SDK_DIR / "python"
    subprocess.run(  # noqa: S603 - trusted release-time generator invocation
        [generator, "generate", "--path", str(OPENAPI), "--output-path", str(out), "--overwrite"],
        check=True,
    )


def generate_typescript() -> None:
    generator = _require("openapi-typescript-codegen")
    out = SDK_DIR / "typescript"
    subprocess.run(  # noqa: S603 - trusted release-time generator invocation
        [generator, "--input", str(OPENAPI), "--output", str(out), "--client", "fetch"],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", action="store_true", help="Generate Python client")
    parser.add_argument("--typescript", action="store_true", help="Generate TypeScript client")
    args = parser.parse_args()
    if not OPENAPI.exists():
        raise SystemExit(f"Missing OpenAPI schema: {OPENAPI}. Run scripts/export_openapi.py first.")
    if not args.python and not args.typescript:
        raise SystemExit("Select at least one target: --python and/or --typescript")
    if args.python:
        generate_python()
    if args.typescript:
        generate_typescript()


if __name__ == "__main__":
    main()
