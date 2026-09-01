# AppForge

AppForge is a lightweight Linux application installer for Ubuntu and Debian.
Choose a supported package, press Install, and AppForge handles the
appropriate installation flow.

## Supported packages

- AppImage: copied into the current user's local AppForge folder, marked
  executable, and given a launcher in the application menu.
- tar.gz / tgz: safely extracted into the current user's local AppForge folder
  and given a launcher when an executable is detected.
- deb: installed system-wide with apt-get; the desktop asks for an
  administrator password through the operating system.

## Install and run

### Python dependencies

AppForge has no third-party Python dependencies. Install the project in a
virtual environment (or run it from a checkout) with your preferred Python
version:

    python -m pip install -e .

### System dependencies (Ubuntu and Debian)

The desktop interface uses Tkinter. Tkinter is a system package and **cannot be
installed with pip**. Install it before starting AppForge:

    sudo apt update
    sudo apt install python3-tk

If you use a separately packaged Python version, install the matching Tkinter
package instead; for example, Python 3.14 may require `python3.14-tk`.

Then launch the application:

    python -m appforge

or, after installation:

    appforge

If Tkinter is missing, AppForge exits with this installation guidance instead
of showing a Python traceback. AppForge also needs a graphical desktop session
with a display available; it cannot open a window in a headless terminal.

## Safety model

- Archive detection and extraction reject unsafe paths and special-file links.
- The UI shows a clear failure message instead of silently ignoring errors.
- AppImage and archive installation stays in the user's home folder by default.
- Only deb installation requires elevated privileges, delegated to pkexec
  apt-get.

Uninstall support, package verification, icons, and richer desktop metadata are
the remaining work before a production release.
