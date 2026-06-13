import functools
import glob
import logging
import os
from typing import Any, Dict, List

import yara

from parallax.core.config import settings

logger = logging.getLogger(__name__)


def _resolve_rules_dir() -> str:
    """Find the rules/yara directory.

    Honors ``YARA_RULES_DIR`` when set, otherwise searches the known layouts:
    the rules live at the repository root (``rules/yara``) but a deployment may
    also ship them inside the package (``parallax/rules/yara``).
    """
    if settings.YARA_RULES_DIR and os.path.isdir(settings.YARA_RULES_DIR):
        return settings.YARA_RULES_DIR
    # static -> analysis -> parallax(pkg) -> parallax(repo subdir) -> repo root
    pkg_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    repo_root = os.path.dirname(pkg_root)
    for base in (pkg_root, repo_root):
        candidate = os.path.join(base, "rules", "yara")
        if os.path.isdir(candidate):
            return candidate
    return os.path.join(pkg_root, "rules", "yara")  # default for the warning path


@functools.lru_cache(maxsize=1)
def load_yara_rules() -> yara.Rules | None:
    """
    Load and compile all YARA rules from the rules/yara/baseline and rules/yara/custom directories.
    """
    rules_dir = _resolve_rules_dir()

    # We compile all .yar files we can find in baseline and custom
    filepaths = {}

    for category in ["baseline", "custom"]:
        category_dir = os.path.join(rules_dir, category)
        if not os.path.exists(category_dir):
            continue

        for yar_file in glob.glob(os.path.join(category_dir, "*.yar")):
            namespace = os.path.basename(yar_file).replace(".yar", "")
            filepaths[f"{category}_{namespace}"] = yar_file

    if not filepaths:
        logger.warning(f"No YARA rules found in {rules_dir}")
        return None

    try:
        return yara.compile(filepaths=filepaths)
    except yara.SyntaxError as e:
        logger.error(f"Failed to compile YARA rules: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error compiling YARA rules: {e}")
        return None


def run_yara(apk_path: str) -> List[Dict[str, Any]]:
    """
    Run compiled YARA rules against the given file.

    Args:
        apk_path (str): Path to the local APK file or DEX file.

    Returns:
        list: A list of dictionaries representing the YARA matches.
    """
    logger.info(f"Running YARA scan on {apk_path}")

    rules = load_yara_rules()
    if not rules:
        return []

    try:
        matches = rules.match(apk_path)

        results = []
        for match in matches:
            results.append(
                {
                    "rule": match.rule,
                    "namespace": match.namespace,
                    "tags": match.tags,
                    "meta": match.meta,
                    "strings": [
                        {
                            "offset": string_match.instances[0].offset,
                            "identifier": string_match.identifier,
                            "data": repr(string_match.instances[0].matched_data),
                        }
                        for string_match in match.strings
                    ]
                    if match.strings
                    else [],
                }
            )

        return results
    except Exception as e:
        logger.error(f"YARA scan failed for {apk_path}: {e}")
        return []
