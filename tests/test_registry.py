from pathlib import Path

from appforge.installer import create_install_plan
from appforge.registry import install_and_record, list_installations, uninstall


def test_user_install_can_be_uninstalled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    source = tmp_path / "Demo.AppImage"
    source.write_text("demo", encoding="utf-8")

    result = install_and_record(create_install_plan(source))

    assert result.executable is not None
    assert len(list_installations()) == 1
    uninstall("demo")
    assert not result.executable.exists()
    assert list_installations() == []
