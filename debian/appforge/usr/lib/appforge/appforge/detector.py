"""Detect supported Linux application packages and extracted applications."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import stat
import tarfile


class PackageKind(str, Enum):
    """Package formats understood by AppForge."""

    APPIMAGE = "appimage"
    DEB = "deb"
    TAR_GZ = "tar.gz"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ApplicationPackage:
    """A detected package and the executable discovered inside it, if any."""

    path: Path
    kind: PackageKind
    executable: Path | None = None

    @property
    def supported(self) -> bool:
        """Whether AppForge can install this package format."""
        return self.kind is not PackageKind.UNKNOWN


@dataclass(frozen=True)
class DetectionResult:
    """Information discovered about an extracted application directory."""

    package_type: str
    executable: Path | None = None
    electron: bool = False


def detect_package(path: str | Path) -> ApplicationPackage:
    """Identify an application package without extracting it."""
    package_path = Path(path).expanduser()
    name = package_path.name.lower()
    if name.endswith(".appimage"):
        return ApplicationPackage(package_path, PackageKind.APPIMAGE, package_path)
    if name.endswith(".deb"):
        return ApplicationPackage(package_path, PackageKind.DEB)
    if name.endswith((".tar.gz", ".tgz")):
        executable = _find_archive_executable(package_path)
        if executable is not None:
            return ApplicationPackage(package_path, PackageKind.TAR_GZ, executable)
    return ApplicationPackage(package_path, PackageKind.UNKNOWN)


def _find_archive_executable(archive_path: Path) -> Path | None:
    """Return the first executable regular member in a gzip-compressed tar."""
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            for member in archive:
                if member.isfile() and member.mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                    return Path(member.name)
    except (FileNotFoundError, OSError, tarfile.TarError):
        return None
    return None


def detect_executable(directory: Path) -> Path | None:
    """Find a likely top-level executable in an extracted application."""
    try:
        candidates = [
            path for path in directory.iterdir()
            if path.is_file() and path.name != "chrome-sandbox" and path.stat().st_mode & 0o111
        ]
    except OSError:
        return None
    if not candidates:
        return None
    normalized_name = directory.name.lower().replace("-x64", "").replace("_x64", "")
    return next((item for item in candidates if normalized_name in item.name.lower()), candidates[0])


def detect_extracted_app(directory: Path) -> DetectionResult:
    """Inspect an extracted directory and identify a portable or Electron app."""
    electron = bool(list((directory / "resources").glob("*.asar")) or (directory / "chrome-sandbox").exists())
    return DetectionResult(
        package_type="electron" if electron else "portable",
        executable=detect_executable(directory),
        electron=electron,
    )
