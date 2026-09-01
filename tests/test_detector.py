from pathlib import Path

from appforge.detector import PackageKind, detect_executable, detect_extracted_app, detect_package


def test_detect_package_recognizes_appimage(tmp_path: Path) -> None:
    package = detect_package(tmp_path / "Example.AppImage")

    assert package.kind is PackageKind.APPIMAGE
    assert package.supported


def test_detect_extracted_app_preserves_electron_detection(tmp_path: Path) -> None:
    app_directory = tmp_path / "Example-x64"
    resources = app_directory / "resources"
    resources.mkdir(parents=True)
    (resources / "app.asar").write_bytes(b"")
    executable = app_directory / "Example"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)

    result = detect_extracted_app(app_directory)

    assert detect_executable(app_directory) == executable
    assert result.package_type == "electron"
    assert result.electron
    assert result.executable == executable
