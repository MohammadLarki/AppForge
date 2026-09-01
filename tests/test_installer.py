from pathlib import Path
import tarfile

import pytest

from appforge.installer import (
    InstallScope,
    create_install_plan,
    execute_install_plan,
)


def test_appimage_install_copies_file_and_writes_launcher(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    source = tmp_path / "My App.AppImage"
    source.write_text("appimage", encoding="utf-8")
    plan = create_install_plan(source)

    result = execute_install_plan(plan)

    assert result.executable is not None
    assert result.executable.read_text(encoding="utf-8") == "appimage"
    assert plan.launcher_path.is_file()
    assert "Exec=" in plan.launcher_path.read_text(encoding="utf-8")


def test_deb_plan_requires_system_scope(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="system scope"):
        create_install_plan(tmp_path / "tool.deb")


def test_deb_install_uses_pkexec(tmp_path: Path) -> None:
    source = tmp_path / "tool.deb"
    source.write_bytes(b"deb")
    plan = create_install_plan(source, scope=InstallScope.SYSTEM)
    calls = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return Result()

    execute_install_plan(plan, command_runner=runner)

    assert calls[0][0][:4] == ["pkexec", "apt-get", "install", "--yes"]


def test_tar_with_unsafe_member_is_rejected_during_detection(tmp_path: Path) -> None:
    source = tmp_path / "unsafe.tar.gz"
    payload = tmp_path / "payload"
    payload.write_text("x", encoding="utf-8")
    with tarfile.open(source, "w:gz") as archive:
        archive.add(payload, arcname="../escape")

    with pytest.raises(ValueError, match="not a supported"):
        create_install_plan(source)
