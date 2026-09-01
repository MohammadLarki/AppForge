from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_debian_control_separates_build_and_runtime_dependencies() -> None:
    control = (ROOT / "debian" / "control").read_text(encoding="utf-8")

    assert "Build-Depends: debhelper-compat (= 13)" in control
    assert "Architecture: all" in control
    assert "python3 (>= 3.10), python3-tk" in control


def test_debian_release_version_matches_python_package() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    changelog = (ROOT / "debian" / "changelog").read_text(encoding="utf-8")

    assert 'version = "0.1.0"' in pyproject
    assert "appforge (0.1.0-1)" in changelog


def test_desktop_release_installs_launcher_icon_and_runtime_modules() -> None:
    install = (ROOT / "debian" / "appforge.install").read_text(encoding="utf-8")
    desktop = (ROOT / "packaging" / "appforge.desktop").read_text(encoding="utf-8")
    launcher = (ROOT / "packaging" / "appforge").read_text(encoding="utf-8")

    assert "appforge usr/lib/appforge" in install
    assert "appforge.desktop usr/share/applications" in install
    assert "appforge.svg usr/share/icons/hicolor/scalable/apps" in install
    assert "Exec=appforge" in desktop
    assert "Icon=appforge" in desktop
    assert "PYTHONPATH=\"/usr/lib/appforge" in launcher
