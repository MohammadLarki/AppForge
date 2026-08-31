"""AppForge: small, predictable helpers for installing Linux applications."""

from .detector import ApplicationPackage, PackageKind, detect_package
from .installer import (
    InstallScope,
    InstallationPlan,
    InstallationResult,
    create_install_plan,
    execute_install_plan,
)

__all__ = [
    "ApplicationPackage",
    "InstallScope",
    "InstallationPlan",
    "InstallationResult",
    "PackageKind",
    "create_install_plan",
    "detect_package",
    "execute_install_plan",
]
__version__ = "0.1.0"
