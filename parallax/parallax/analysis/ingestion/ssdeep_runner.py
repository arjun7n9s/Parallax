import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def run_ssdeep(apk_path: str | Path) -> dict:
    """
    Run ssdeep on the given APK to generate a fuzzy hash.
    Returns the computed ssdeep hash or an error.
    """
    apk_path = str(apk_path)
    try:
        # Run ssdeep and just get the hash without file path
        # Output format is usually:
        # ssdeep,1.1--blocksize:hash:hash,filename
        # 3145728:xxxxxxxxxxx:xxxxxxxxxx,"/path/to/file"
        result = subprocess.run(
            ["ssdeep", "-s", apk_path], capture_output=True, text=True, check=False
        )

        if result.returncode != 0:
            logger.error(f"ssdeep failed with exit code {result.returncode}: {result.stderr}")
            return {"error": "ssdeep execution failed"}

        lines = result.stdout.strip().split("\n")
        if len(lines) < 2:
            return {"error": "unexpected ssdeep output format"}

        # The second line contains the hash
        # Format: chunk_size:chunk_hash:double_chunk_hash,"filename"
        hash_line = lines[1]

        # Extract just the hash part, ignoring the filename
        hash_value = hash_line.split(",")[0]

        return {"hash": hash_value}

    except FileNotFoundError:
        logger.warning("ssdeep binary not found. Returning empty results.")
        return {"error": "ssdeep not installed"}
    except Exception as e:
        logger.exception("Unexpected error running ssdeep")
        return {"error": str(e)}
