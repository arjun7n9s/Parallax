"""Export the FastAPI OpenAPI schema to parallax/api/openapi.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_OUTPUT = ROOT / "parallax" / "api" / "openapi.json"


def export_openapi(output: Path = DEFAULT_OUTPUT) -> Path:
    from parallax.api.main import app

    schema = app.openapi()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path = export_openapi(args.output)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
