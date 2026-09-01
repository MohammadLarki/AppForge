"""Package and application detection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DetectionResult:
    """Information discovered about an extracted application."""

    package_type: str
    executable: Path | None = None
    electron: bool = False


def detect_executable(directory: Path) -> Path | None:
    """Find a likely top-level executable in an extracted application."""
    candidates: list[Path] = []
    for path in directory.iterdir():
        if path.is_file() and path.name != "chrome-sandbox":
            try:
                if path.stat().st_mode & 0o111:
                    candidates.append(path)
            except OSError:
                continue

    if not candidates:
        return None

    name = directory.name.lower().replace("-x64", "").replace("_x64", "")
    for candidate in candidates:
        if name and name in candidate.name.lower():
            return candidate
    return candidates[0]


def detect_extracted_app(directory: Path) -> DetectionResult:
    """Inspect an extracted directory and identify its likely app type."""
    asar_files = list((directory / "resources").glob("*.asar"))
    electron = bool(asar_files or (directory / "chrome-sandbox").exists())

    return DetectionResult(
        package_type="electron" if electron else "portable",
        executable=detect_executable(directory),
        electron=electron,
    )
