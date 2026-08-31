"""AppForge: small, predictable helpers for installing Linux applications."""

from .detector import ApplicationPackage, PackageKind, detect_package
from .installer import InstallScope, InstallationPlan, create_install_plan

__all__ = [
    "ApplicationPackage",
    "InstallScope",
    "InstallationPlan",
    "PackageKind",
    "create_install_plan",
    "detect_package",
]
__version__ = "0.1.0"
