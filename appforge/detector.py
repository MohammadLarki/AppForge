"""Detect supported Linux application packages.

The detector is deliberately read-only: archives are inspected in place and are
never extracted. Installation is handled by a later AppForge component.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import stat
import tarfile


class PackageKind(str, Enum):
    """Package formats understood by the first AppForge MVP."""

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


def detect_package(path: str | Path) -> ApplicationPackage:
    """Identify an application package at path.

    For tar.gz and tgz archives, the returned executable is the first regular
    file with an executable permission bit. Invalid or unreadable archives are
    classified as unsupported instead of raising an extraction error.
    """

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
                if member.isfile() and member.mode & (
                    stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                ):
                    return Path(member.name)
    except (FileNotFoundError, OSError, tarfile.TarError):
        return None
    return None
