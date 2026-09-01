"""AppForge: small, predictable helpers for installing Linux applications."""

from .detector import (
    ApplicationPackage,
    DetectionResult,
    PackageKind,
    detect_executable,
    detect_extracted_app,
    detect_package,
)
from .installer import InstallScope, InstallationPlan, InstallationResult, create_install_plan, execute_install_plan
from .registry import install_and_record, list_installations, uninstall

__all__ = [
    "ApplicationPackage", "DetectionResult", "InstallScope", "InstallationPlan",
    "InstallationResult", "PackageKind", "create_install_plan", "detect_executable",
    "detect_extracted_app", "detect_package", "execute_install_plan", "install_and_record",
    "list_installations", "uninstall",
]
__version__ = "0.1.0"
