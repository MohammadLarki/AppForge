from pathlib import Path

import pytest

from appforge.installer import InstallScope, create_install_plan


def test_appimage_plan_uses_user_locations(tmp_path: Path) -> None:
    plan = create_install_plan(tmp_path / "My App.AppImage")

    assert plan.scope is InstallScope.USER
    assert plan.application_id == "my-app"
    assert [action.name for action in plan.actions] == [
        "copy-appimage",
        "make-executable",
        "create-launcher",
    ]
    assert plan.launcher_path.name == "appforge-my-app.desktop"


def test_deb_plan_does_not_create_launcher(tmp_path: Path) -> None:
    plan = create_install_plan(tmp_path / "tool.deb", scope=InstallScope.SYSTEM)

    assert plan.requires_administrator
    assert [action.name for action in plan.actions] == ["install-deb-package"]


def test_unknown_package_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a supported"):
        create_install_plan(tmp_path / "tool.zip")
