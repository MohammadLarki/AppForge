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

## Run

AppForge currently uses only Python's standard library:

    python -m appforge

## Safety model

- Archive detection and extraction reject unsafe paths and special-file links.
- The UI shows a clear failure message instead of silently ignoring errors.
- AppImage and archive installation stays in the user's home folder by default.
- Only deb installation requires elevated privileges, delegated to pkexec
  apt-get.

Uninstall support, package verification, icons, and richer desktop metadata are
the remaining work before a production release.
