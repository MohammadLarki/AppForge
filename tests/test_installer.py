from pathlib import Path
import io
import json
import subprocess
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


def test_electron_archive_extracts_icon_and_writes_launchable_launcher(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    source = tmp_path / "Antigravity.tar.gz"
    icon = b"\x89PNG\r\n\x1a\napp-icon"
    asar = _make_asar_with_icon(icon)
    with tarfile.open(source, "w:gz") as archive:
        _add_archive_file(archive, "Antigravity-x64/antigravity", b"#!/bin/sh\ntest \"$1\" = --no-sandbox\n", 0o755)
        _add_archive_file(archive, "Antigravity-x64/chrome-sandbox", b"sandbox", 0o755)
        _add_archive_file(archive, "Antigravity-x64/resources/app.asar", asar, 0o644)

    result = execute_install_plan(create_install_plan(source))

    assert result.executable is not None
    assert result.icon is not None
    assert result.icon.read_bytes() == icon
    launcher = result.plan.launcher_path.read_text(encoding="utf-8")
    assert f'Exec="{result.executable}" --no-sandbox %U' in launcher
    assert f"Path={result.executable.parent}" in launcher
    assert f"Icon={result.icon}" in launcher
    subprocess.run([str(result.executable), "--no-sandbox"], cwd=result.executable.parent, check=True)


def _add_archive_file(archive: tarfile.TarFile, name: str, payload: bytes, mode: int) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mode = mode
    archive.addfile(info, fileobj=io.BytesIO(payload))


def _make_asar_with_icon(icon: bytes) -> bytes:
    header = json.dumps({"files": {"icon.png": {"size": len(icon), "offset": "0"}}}).encode("utf-8")
    header_size = len(header) + 8
    return b"\x04\x00\x00\x00" + header_size.to_bytes(4, "little") + b"\x00" * 8 + header + icon
