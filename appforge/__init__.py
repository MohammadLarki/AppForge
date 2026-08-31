"""AppForge: small, predictable helpers for installing Linux applications."""

from .detector import ApplicationPackage, PackageKind, detect_package

__all__ = ["ApplicationPackage", "PackageKind", "detect_package"]
__version__ = "0.1.0"
