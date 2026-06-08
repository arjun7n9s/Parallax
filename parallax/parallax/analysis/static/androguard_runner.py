import logging
from typing import Any, Dict

from androguard.misc import AnalyzeAPK

logger = logging.getLogger(__name__)


def run_androguard(apk_path: str) -> Dict[str, Any]:
    """
    Run Androguard to extract static metadata, permissions, activities, and services.

    Args:
        apk_path (str): The local path to the APK.

    Returns:
        dict: A dictionary of extracted static features.
    """
    logger.info(f"Running Androguard on {apk_path}")

    try:
        a, d, dx = AnalyzeAPK(apk_path)

        permissions = a.get_permissions()
        activities = a.get_activities()
        services = a.get_services()
        receivers = a.get_receivers()
        providers = a.get_providers()

        main_activity = a.get_main_activity()

        return {
            "package_name": a.get_package(),
            "app_name": a.get_app_name(),
            "version_name": a.get_androidversion_name(),
            "version_code": a.get_androidversion_code(),
            "min_sdk": a.get_min_sdk_version(),
            "target_sdk": a.get_target_sdk_version(),
            "main_activity": main_activity,
            "permissions": list(permissions) if permissions else [],
            "activities": list(activities) if activities else [],
            "services": list(services) if services else [],
            "receivers": list(receivers) if receivers else [],
            "providers": list(providers) if providers else [],
            "is_valid": a.is_valid_APK(),
        }
    except Exception as e:
        logger.error(f"Androguard analysis failed for {apk_path}: {e}")
        return {
            "error": str(e),
            "package_name": "unknown",
            "permissions": [],
            "activities": [],
            "services": [],
            "receivers": [],
        }
