"""Persistent registry and safe removal for user-scope AppForge installations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shutil

from .installer import InstallationPlan, InstallationResult, execute_install_plan


@dataclass(frozen=True, slots=True)
class RegisteredInstallation:
    application_id: str
    install_directory: str
    launcher_path: str
    executable: str | None
    icon: str | None = None


def install_and_record(plan: InstallationPlan) -> InstallationResult:
    """Install a user-scope application and persist its removal record."""

    result = execute_install_plan(plan)
    if not plan.requires_administrator and result.executable is not None:
        record = RegisteredInstallation(
            application_id=plan.application_id,
            install_directory=str(plan.install_directory),
            launcher_path=str(plan.launcher_path),
            executable=str(result.executable),
            icon=str(result.icon) if result.icon else None,
        )
        path = _record_path(plan.application_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(record), indent=2) + "\n", encoding="utf-8")
    return result


def uninstall(application_id: str) -> None:
    """Remove a previously recorded user-scope installation."""

    path = _record_path(application_id).resolve()
    _ensure_within(path, _record_root())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError("No AppForge installation record was found.") from error

    install_directory = Path(data["install_directory"]).resolve()
    launcher_path = Path(data["launcher_path"]).resolve()
    _ensure_within(install_directory, _install_root())
    _ensure_within(launcher_path, _launcher_root())

    if install_directory.exists():
        shutil.rmtree(install_directory)
    launcher_path.unlink(missing_ok=True)
    path.unlink(missing_ok=True)


def list_installations() -> list[RegisteredInstallation]:
    """Return the user-scope applications installed through the GUI."""

    records = []
    for path in sorted(_record_root().glob("*.json")):
        try:
            records.append(RegisteredInstallation(**json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return records


def _record_path(application_id: str) -> Path:
    return _record_root() / f"{application_id}.json"


def _record_root() -> Path:
    return Path.home() / ".local" / "share" / "appforge" / "installs"


def _install_root() -> Path:
    return Path.home() / ".local" / "opt" / "appforge"


def _launcher_root() -> Path:
    return Path.home() / ".local" / "share" / "applications"


def _ensure_within(path: Path, root: Path) -> None:
    if path != root and root not in path.parents:
        raise ValueError("Installation record points outside AppForge locations.")
