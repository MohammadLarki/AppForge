"""Plan and execute safe installations for supported Linux application packages."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
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
    icon: Path | None = None


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

    icon = _discover_icon(plan.install_directory, plan.application_id)
    _write_launcher(plan.launcher_path, plan.application_id, executable, icon)
    return InstallationResult(plan, executable, icon)


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


def _write_launcher(
    launcher_path: Path,
    application_id: str,
    executable: Path,
    icon: Path | None,
) -> None:
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    electron = _electron_runtime_directory(executable) is not None
    arguments = " --no-sandbox %U" if electron else " %U"
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={application_id}\n"
        f"Exec={_desktop_quote(executable)}{arguments}\n"
        f"Path={executable.parent}\n"
        "Terminal=false\n"
        "Categories=Utility;\n"
    )
    if icon is not None:
        content += f"Icon={icon}\n"
    launcher_path.write_text(content, encoding="utf-8")
    launcher_path.chmod(0o644)


def _desktop_quote(path: Path) -> str:
    """Quote a desktop-entry argument without invoking a shell."""
    value = str(path).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{value}"'


def _electron_runtime_directory(executable: Path) -> Path | None:
    """Return Electron's runtime directory when the executable is Electron-based."""
    directory = executable.parent
    if (directory / "chrome-sandbox").is_file() and (directory / "resources" / "app.asar").is_file():
        return directory
    return None


def _discover_icon(install_directory: Path, application_id: str) -> Path | None:
    """Find an installed icon, extracting an Electron ASAR icon when necessary."""
    candidates = [
        path for path in install_directory.rglob("*")
        if path.is_file() and path.suffix.lower() in {".png", ".svg", ".xpm"}
    ]
    if candidates:
        return max(candidates, key=lambda path: _icon_score(path, application_id))

    for archive in install_directory.rglob("app.asar"):
        extracted = _extract_asar_icon(archive, install_directory)
        if extracted is not None:
            return extracted
    return None


def _icon_score(path: Path, application_id: str) -> tuple[int, int]:
    name = path.stem.lower()
    score = 0
    if name == "icon":
        score += 100
    if application_id.replace("-", "") in name.replace("-", ""):
        score += 50
    if "tray" in name:
        score -= 100
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    return score, size


def _extract_asar_icon(archive_path: Path, destination_directory: Path) -> Path | None:
    """Extract the best PNG/SVG icon from an Electron ASAR archive safely."""
    try:
        with archive_path.open("rb") as archive:
            prefix = archive.read(8)
            header_size = int.from_bytes(prefix[4:8], "little")
            if header_size < 8:
                return None
            header = json.loads(archive.read(header_size)[8:].decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return None

    icons: list[tuple[str, dict[str, object]]] = []

    def visit(node: dict[str, object], prefix: str = "") -> None:
        children = node.get("files")
        if not isinstance(children, dict):
            return
        for name, value in children.items():
            if not isinstance(name, str) or not isinstance(value, dict):
                continue
            relative = f"{prefix}/{name}" if prefix else name
            if name.lower().endswith((".png", ".svg")) and "tray" not in name.lower():
                icons.append((relative, value))
            visit(value, relative)

    visit(header)
    if not icons:
        return None
    icons.sort(key=lambda item: ("icon" in item[0].lower(), item[0].lower().endswith(".png")), reverse=True)
    relative, metadata = icons[0]
    try:
        offset = int(metadata["offset"])
        size = int(metadata["size"])
        header_end = 8 + header_size
    except (KeyError, TypeError, ValueError):
        return None
    try:
        with archive_path.open("rb") as archive:
            archive.seek(header_end + offset)
            payload = archive.read(size)
    except OSError:
        return None
    if len(payload) != size or not payload:
        return None
    destination = destination_directory / f".appforge-icon{Path(relative).suffix.lower()}"
    destination.write_bytes(payload)
    return destination


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
