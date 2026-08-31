"""Create safe, reviewable installation plans for supported packages.

This module does not use a shell. A future UI can display the returned plan,
ask for consent, and execute its actions with the appropriate privilege helper.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re

from .detector import ApplicationPackage, PackageKind, detect_package


class InstallScope(str, Enum):
    """Where the application will be installed."""

    USER = "user"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class InstallAction:
    """One human-readable, non-shell installation operation."""

    name: str
    source: Path | None
    destination: Path | None


@dataclass(frozen=True, slots=True)
class InstallationPlan:
    """The complete plan a UI should show before installation begins."""

    package: ApplicationPackage
    application_id: str
    scope: InstallScope
    install_directory: Path
    launcher_path: Path
    actions: tuple[InstallAction, ...]

    @property
    def requires_administrator(self) -> bool:
        """Whether the plan writes outside the current user's home directory."""

        return self.scope is InstallScope.SYSTEM


def create_install_plan(
    package_path: str | Path,
    *,
    application_name: str | None = None,
    scope: InstallScope = InstallScope.USER,
) -> InstallationPlan:
    """Build an installation plan without changing the system.

    The caller can present this plan for confirmation before executing it. The
    default user scope intentionally avoids an administrator-password prompt.
    """

    package = detect_package(package_path)
    if not package.supported:
        raise ValueError("The selected file is not a supported AppForge package.")

    application_id = _application_id(application_name or package.path.stem)
    install_directory = _install_directory(application_id, scope)
    launcher_path = _launcher_path(application_id, scope)
    actions = _actions_for(package, install_directory, launcher_path)

    return InstallationPlan(
        package=package,
        application_id=application_id,
        scope=scope,
        install_directory=install_directory,
        launcher_path=launcher_path,
        actions=actions,
    )


def _actions_for(
    package: ApplicationPackage,
    install_directory: Path,
    launcher_path: Path,
) -> tuple[InstallAction, ...]:
    if package.kind is PackageKind.DEB:
        return (
            InstallAction("install-deb-package", package.path, None),
        )
    if package.kind is PackageKind.APPIMAGE:
        return (
            InstallAction("copy-appimage", package.path, install_directory / package.path.name),
            InstallAction("make-executable", None, install_directory / package.path.name),
            InstallAction("create-launcher", None, launcher_path),
        )
    return (
        InstallAction("extract-tar-archive", package.path, install_directory),
        InstallAction("create-launcher", None, launcher_path),
    )


def _application_id(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not normalized:
        raise ValueError("Application name must include at least one letter or number.")
    return normalized


def _install_directory(application_id: str, scope: InstallScope) -> Path:
    if scope is InstallScope.SYSTEM:
        return Path("/opt/appforge") / application_id
    return Path.home() / ".local" / "opt" / "appforge" / application_id


def _launcher_path(application_id: str, scope: InstallScope) -> Path:
    if scope is InstallScope.SYSTEM:
        return Path("/usr/share/applications") / f"appforge-{application_id}.desktop"
    return Path.home() / ".local" / "share" / "applications" / f"appforge-{application_id}.desktop"
