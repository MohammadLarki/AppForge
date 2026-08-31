"""Plan and execute safe installations for supported Linux application packages."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import os
import re
import shutil
import stat
import subprocess
import tarfile

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


@dataclass(frozen=True, slots=True)
class InstallationResult:
    """The durable locations created by a successful installation."""

    plan: InstallationPlan
    executable: Path | None


def create_install_plan(
    package_path: str | Path,
    *,
    application_name: str | None = None,
    scope: InstallScope = InstallScope.USER,
) -> InstallationPlan:
    """Build an installation plan without changing the system."""

    package = detect_package(package_path)
    if not package.supported:
        raise ValueError("The selected file is not a supported AppForge package.")
    if package.kind is PackageKind.DEB and scope is not InstallScope.SYSTEM:
        raise ValueError("Deb packages require system scope.")

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


def execute_install_plan(
    plan: InstallationPlan,
    *,
    command_runner: object = subprocess.run,
) -> InstallationResult:
    """Execute a previously reviewed plan.

    AppImage and tar.gz installations write only the locations named by the
    plan. Deb installation delegates dependency resolution to apt through
    pkexec, so only the package manager receives administrator privileges.
    """

    source = plan.package.path
    if not source.is_file():
        raise FileNotFoundError(f"Package file does not exist: {source}")

    if plan.package.kind is PackageKind.DEB:
        _run_deb_install(source, command_runner)
        return InstallationResult(plan, None)

    if plan.package.kind is PackageKind.APPIMAGE:
        executable = _install_appimage(source, plan.install_directory)
    else:
        executable = _install_tar_archive(source, plan.install_directory, plan.package.executable)

    _write_launcher(plan.launcher_path, plan.application_id, executable)
    return InstallationResult(plan, executable)


def _actions_for(
    package: ApplicationPackage,
    install_directory: Path,
    launcher_path: Path,
) -> tuple[InstallAction, ...]:
    if package.kind is PackageKind.DEB:
        return (InstallAction("install-deb-package", package.path, None),)
    if package.kind is PackageKind.APPIMAGE:
        target = install_directory / package.path.name
        return (
            InstallAction("copy-appimage", package.path, target),
            InstallAction("make-executable", None, target),
            InstallAction("create-launcher", None, launcher_path),
        )
    return (
        InstallAction("extract-tar-archive", package.path, install_directory),
        InstallAction("create-launcher", None, launcher_path),
    )


def _run_deb_install(source: Path, command_runner: object) -> None:
    command = ["pkexec", "apt-get", "install", "--yes", str(source.resolve())]
    result = command_runner(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "apt-get failed").strip()
        raise RuntimeError(f"Deb installation failed: {detail}")


def _install_appimage(source: Path, install_directory: Path) -> Path:
    install_directory.mkdir(parents=True, exist_ok=True)
    target = install_directory / source.name
    shutil.copy2(source, target)
    target.chmod(target.stat().st_mode | stat.S_IXUSR)
    return target


def _install_tar_archive(
    source: Path, install_directory: Path, executable_member: Path | None
) -> Path:
    if executable_member is None:
        raise ValueError("Archive does not contain an executable file.")

    install_directory.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(source, mode="r:gz") as archive:
            for member in archive:
                _extract_member_safely(archive, member, install_directory)
    except tarfile.TarError as error:
        raise ValueError(f"Invalid tar archive: {source}") from error

    executable = install_directory / executable_member
    if not executable.is_file():
        raise ValueError("The detected archive executable was not extracted.")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def _extract_member_safely(
    archive: tarfile.TarFile, member: tarfile.TarInfo, destination: Path
) -> None:
    member_path = Path(member.name)
    if member_path.is_absolute() or ".." in member_path.parts:
        raise ValueError("Archive contains an unsafe path.")
    target = destination / member_path

    if member.isdir():
        target.mkdir(parents=True, exist_ok=True)
        return
    if not member.isfile():
        raise ValueError("Archive contains unsupported links or special files.")

    target.parent.mkdir(parents=True, exist_ok=True)
    source_file = archive.extractfile(member)
    if source_file is None:
        raise ValueError("Archive member could not be read.")
    with source_file, target.open("wb") as output:
        shutil.copyfileobj(source_file, output)
    os.chmod(target, member.mode & 0o777)


def _write_launcher(launcher_path: Path, application_id: str, executable: Path) -> None:
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    escaped_executable = str(executable).replace("\\", "\\\\").replace(" ", "\\s")
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={application_id}\n"
        f"Exec={escaped_executable}\n"
        "Terminal=false\n"
        "Categories=Utility;\n"
    )
    launcher_path.write_text(content, encoding="utf-8")
    launcher_path.chmod(0o644)


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
