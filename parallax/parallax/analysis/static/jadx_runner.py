import logging
import subprocess
from typing import Dict

logger = logging.getLogger(__name__)


def run_jadx(apk_path: str, output_dir: str) -> Dict[str, str]:
    """
    Run jadx to decompile the APK into Java source code.

    Args:
        apk_path (str): Path to the local APK file.
        output_dir (str): Path to the directory where decompiled code should be saved.

    Returns:
        dict: A dictionary containing the status and output directory.
    """
    logger.info(f"Running Jadx on {apk_path} -> {output_dir}")

    # Using --no-res to speed up decompilation by skipping resource decoding
    # Using --show-bad-code to ensure we get as much code as possible even if flawed
    cmd = [
        "jadx",
        "-d",
        output_dir,
        "--no-res",
        "--show-bad-code",
        apk_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.debug(f"Jadx stdout: {result.stdout}")
        return {
            "status": "success",
            "output_dir": output_dir,
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Jadx failed for {apk_path}: {e.stderr}")
        return {
            "status": "error",
            "error": e.stderr or str(e),
            "output_dir": output_dir,
        }
    except FileNotFoundError:
        error_msg = "Jadx CLI not found in PATH. Please install Jadx."
        logger.error(error_msg)
        return {
            "status": "error",
            "error": error_msg,
            "output_dir": output_dir,
        }
