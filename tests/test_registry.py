from pathlib import Path

import pytest

from appforge.installer import create_install_plan
from appforge.registry import install_and_record, list_installations, uninstall


def test_user_install_can_be_uninstalled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    source = tmp_path / "Demo.AppImage"
    source.write_text("demo", encoding="utf-8")

    result = install_and_record(create_install_plan(source))

    assert result.executable is not None
    assert result.icon is None
    assert len(list_installations()) == 1
    uninstall("demo")
    assert not result.executable.exists()
    assert not result.plan.launcher_path.exists()
    assert not (tmp_path / "home" / ".local" / "share" / "appforge" / "installs" / "demo.json").exists()
    assert list_installations() == []


def test_uninstall_rejects_a_record_path_outside_appforge(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    with pytest.raises(ValueError, match="outside AppForge"):
        uninstall("../../not-an-appforge-install")
