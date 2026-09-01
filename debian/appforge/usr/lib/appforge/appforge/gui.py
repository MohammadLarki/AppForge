"""Start AppForge and report missing desktop dependencies clearly."""

from __future__ import annotations

import sys
from collections.abc import Callable


DEVELOPER_LINKS = {
    "Telegram": "https://t.me/HermitLab",
    "GitHub": "https://github.com/MohammadLarki",
    "Email": "mailto:mammadlarki.it@gmail.com",
}


def tkinter_install_instructions() -> str:
    """Return a distribution-oriented fix for a missing Tkinter binding."""
    return (
        "AppForge needs the Tkinter system dependency to start its desktop interface.\n"
        "On Ubuntu or Debian, install it with:\n"
        "  sudo apt update && sudo apt install python3-tk\n"
        "If you use a separately packaged Python version, install its matching package "
        "(for example, python3.14-tk).\n"
        "Tkinter is provided by the operating system, not by pip."
    )


def _load_desktop_main() -> Callable[[], int]:
    """Delay importing the UI so missing Tkinter can be handled gracefully."""
    from .desktop import main

    return main


def main() -> int:
    """Launch the desktop UI, returning a shell-friendly status code."""
    try:
        desktop_main = _load_desktop_main()
    except ModuleNotFoundError as error:
        if error.name not in {"tkinter", "_tkinter"}:
            raise
        print(tkinter_install_instructions(), file=sys.stderr)
        return 1
    return desktop_main()
