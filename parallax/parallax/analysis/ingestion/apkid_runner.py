import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def run_apkid(apk_path: str | Path) -> dict:
    """
    Run APKiD on the given APK to identify packers, compilers, and obfuscators.
    Returns a structured dictionary of findings.
    """
    apk_path = str(apk_path)
    try:
        # Run apkid in JSON output mode
        result = subprocess.run(
            ["apkid", "-j", apk_path],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0 and not result.stdout:
            logger.error(f"APKiD failed with exit code {result.returncode}: {result.stderr}")
            return {"error": "APKiD execution failed"}

        # Parse JSON output
        output_json = json.loads(result.stdout)
        
        # APKiD output structure is usually {"files": [{"filename": "...", "matches": {...}}]}
        files = output_json.get("files", [])
        if not files:
            return {"matches": {}}

        file_data = files[0]
        return {"matches": file_data.get("matches", {})}

    except FileNotFoundError:
        logger.warning("apkid binary not found. Returning empty results.")
        return {"error": "apkid not installed"}
    except json.JSONDecodeError:
        logger.error(f"Failed to parse APKiD output: {result.stdout}")
        return {"error": "invalid JSON output from apkid"}
    except Exception as e:
        logger.exception("Unexpected error running APKiD")
        return {"error": str(e)}
